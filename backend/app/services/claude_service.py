"""Claude API service for AI-powered features."""

import anthropic
import asyncio
import json
import re
from pathlib import Path
from typing import AsyncIterator, List, Optional, Union

from app.config import get_settings

settings = get_settings()

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text()


class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        # Async client for streaming — lets a client disconnect (UI cancel)
        # propagate cancellation and abort the in-flight Claude request.
        self.async_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def _extract_json(self, text: str) -> Union[dict, list]:
        """Extract JSON from Claude's response (object or array)."""
        # Try to find JSON in code blocks first
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            return json.loads(json_match.group(1).strip())

        # Try to find raw JSON object
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            return json.loads(json_match.group(0))

        # Try to find raw JSON array
        json_match = re.search(r"\[[\s\S]*\]", text)
        if json_match:
            return json.loads(json_match.group(0))

        raise ValueError("No valid JSON found in response")

    async def gather_market_data(self) -> dict:
        """
        Gather current market data: live numbers from yfinance, qualitative from Claude.

        Returns:
            Dictionary with valuations, volatility, institutional_views, rates
        """
        import asyncio
        from datetime import date
        from app.services.yfinance_service import fetch_market_snapshot, format_snapshot_for_prompt

        today = date.today().isoformat()

        # Fetch live market data in a thread (yfinance is synchronous)
        snapshot = await asyncio.to_thread(fetch_market_snapshot)
        live_data_block = format_snapshot_for_prompt(snapshot)

        # Build prompt
        prompt_template = load_prompt("market_data")
        prompt = prompt_template.format(today=today, live_data_block=live_data_block)

        message = self.client.messages.create(
            model=settings.market_data_model,
            max_tokens=16000,  # headroom for thinking + the JSON payload
            thinking={"type": "enabled", "budget_tokens": settings.market_data_thinking_budget},
            tools=[{"type": "web_search_20260209", "name": "web_search",
                    "max_uses": settings.market_data_max_searches}],
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # With web search the response contains server_tool_use / web_search_tool_result
        # blocks before the final text block — find the last text block.
        text = next(
            (block.text for block in reversed(message.content) if block.type == "text"),
            None,
        )
        if text is None:
            raise ValueError("No text block found in Claude response")
        return self._extract_json(text)

    async def gather_market_data_streaming(self) -> AsyncIterator[dict]:
        """
        Streaming variant of gather_market_data for live UI progress.

        Async-generates progress events while Claude works, then a final event:
          {"type": "status", "stage": ..., "detail": ...}  — progress
          {"type": "result", "data": <parsed JSON dict>}   — final payload
          {"type": "error",  "detail": ...}                — on failure

        Uses the async Anthropic client so a client disconnect cancels this
        generator, which exits the stream context and aborts the in-flight
        request server-side (no leaked worker thread).
        """
        from datetime import date
        from app.services.yfinance_service import fetch_market_snapshot, format_snapshot_for_prompt

        today = date.today().isoformat()

        snapshot = await asyncio.to_thread(fetch_market_snapshot)
        live_data_block = format_snapshot_for_prompt(snapshot)
        yield {"type": "status", "stage": "yfinance", "detail": "Live market snapshot loaded"}

        prompt_template = load_prompt("market_data")
        prompt = prompt_template.format(today=today, live_data_block=live_data_block)

        # Accumulate each web_search block's streamed JSON input by index so we
        # can surface the actual query once the block completes.
        search_json: dict[int, str] = {}
        final_text = None
        try:
            async with self.async_client.messages.stream(
                model=settings.market_data_model,
                max_tokens=16000,
                thinking={"type": "enabled", "budget_tokens": settings.market_data_thinking_budget},
                tools=[{"type": "web_search_20260209", "name": "web_search",
                        "max_uses": settings.market_data_max_searches}],
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for event in stream:
                    et = event.type
                    if et == "content_block_start":
                        blk = event.content_block
                        if blk.type == "thinking":
                            yield {"type": "status", "stage": "thinking",
                                   "detail": "Reasoning over the data"}
                        elif blk.type == "text":
                            yield {"type": "status", "stage": "compiling",
                                   "detail": "Compiling results"}
                        elif blk.type == "server_tool_use" and getattr(blk, "name", None) == "web_search":
                            search_json[event.index] = ""
                    elif et == "content_block_delta":
                        delta = event.delta
                        if getattr(delta, "type", None) == "input_json_delta" and event.index in search_json:
                            search_json[event.index] += delta.partial_json or ""
                    elif et == "content_block_stop" and event.index in search_json:
                        query = None
                        try:
                            query = json.loads(search_json[event.index] or "{}").get("query")
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        yield {"type": "status", "stage": "search",
                               "detail": f"Searching: {query}" if query else "Searching the web"}
                final = await stream.get_final_message()
            final_text = next(
                (b.text for b in reversed(final.content) if b.type == "text"),
                None,
            )
        except asyncio.CancelledError:
            raise  # client disconnected — let cancellation abort the request
        except Exception as e:  # noqa: BLE001 — surfaced to the client as an error event
            yield {"type": "error", "detail": str(e)}
            return

        if not final_text:
            yield {"type": "error", "detail": "No text block found in Claude response"}
            return
        try:
            data = self._extract_json(final_text)
        except Exception as e:  # noqa: BLE001
            yield {"type": "error", "detail": f"Failed to parse Claude response: {e}"}
            return
        yield {"type": "result", "data": data}

    async def lookup_etf_metadata(self, tickers: List[str]) -> List[dict]:
        """
        Look up ETF metadata using Claude's knowledge.

        Args:
            tickers: List of ETF ticker symbols

        Returns:
            List of ETF metadata dictionaries with region, name, isin, ter, etc.
        """
        # Load prompt from configurable file
        prompt_template = load_prompt("etf_lookup")
        prompt = prompt_template.format(tickers=", ".join(tickers))

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        result = self._extract_json(message.content[0].text)

        # Handle {"results": [...]} format from prompt
        if isinstance(result, dict) and "results" in result:
            return result["results"]

        return result if isinstance(result, list) else [result]


# Singleton instance
_claude_service: Optional[ClaudeService] = None


def get_claude_service() -> ClaudeService:
    """Get or create Claude service singleton."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
