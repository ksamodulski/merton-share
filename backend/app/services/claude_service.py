"""Claude API service for AI-powered features."""

import anthropic
import json
import re
from pathlib import Path
from typing import List, Optional, Union

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
            model=self.model,
            max_tokens=8192,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 7}],
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
