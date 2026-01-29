"use client";

interface FilterBarProps {
  platforms: string[];
  selectedPlatform: string | null;
  onPlatformChange: (platform: string | null) => void;
  dateRange?: number;
  onDateRangeChange?: (days: number) => void;
}

export function FilterBar({
  platforms,
  selectedPlatform,
  onPlatformChange,
  dateRange = 30,
  onDateRangeChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 bg-white rounded-lg shadow px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Platform:</span>
        <div className="flex gap-1">
          <button
            onClick={() => onPlatformChange(null)}
            className={`px-3 py-1 text-sm rounded-full transition-colors ${
              selectedPlatform === null
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            All
          </button>
          {platforms.map((platform) => (
            <button
              key={platform}
              onClick={() => onPlatformChange(platform)}
              className={`px-3 py-1 text-sm rounded-full capitalize transition-colors ${
                selectedPlatform === platform
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {platform}
            </button>
          ))}
        </div>
      </div>

      {onDateRangeChange && (
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-sm text-gray-500">Period:</span>
          <select
            value={dateRange}
            onChange={(e) => onDateRangeChange(Number(e.target.value))}
            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      )}
    </div>
  );
}
