import { useState, useRef } from 'react';

interface ParsedHolding {
  ticker: string;
  valueEur: number;
  percentage: number;
  currencyDenomination: string;
}

interface Props {
  onPortfolioParsed: (holdings: ParsedHolding[], totalValue: number) => void;
  onError: (error: string) => void;
}

export default function CSVUploader({ onPortfolioParsed, onError }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      onError('Please upload a CSV file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      onError('File too large. Maximum 5MB.');
      return;
    }

    setFileName(file.name);
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/v1/portfolio/parse-csv', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to parse CSV');
      }

      const result = await response.json();
      const holdings: ParsedHolding[] = result.holdings.map((h: Record<string, unknown>) => ({
        ticker: h.ticker as string,
        valueEur: h.value_eur as number,
        percentage: h.percentage as number,
        currencyDenomination: h.currency_denomination as string,
      }));

      onPortfolioParsed(holdings, result.total_value_eur);
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Failed to parse CSV');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`
        border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
        ${isDragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-gray-400'}
        ${isProcessing ? 'opacity-50 cursor-wait' : ''}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileSelect}
        className="hidden"
      />

      {isProcessing ? (
        <div className="space-y-3">
          <div className="animate-spin w-10 h-10 border-4 border-primary-600 border-t-transparent rounded-full mx-auto"></div>
          <p className="text-gray-600">Parsing CSV...</p>
          {fileName && <p className="text-sm text-gray-500">{fileName}</p>}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <p className="text-gray-700 font-medium">Upload IBKR CSV Export</p>
            <p className="text-sm text-gray-500 mt-1">
              Drag & drop or click to select your Activity Statement CSV
            </p>
          </div>
          <p className="text-xs text-gray-400">
            Export from IBKR: Reports → Activity → CSV format
          </p>
        </div>
      )}
    </div>
  );
}
