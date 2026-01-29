"use client";

interface StatValueProps {
  value: number | string;
  label: string;
  size?: "sm" | "md" | "lg";
  format?: "number" | "compact" | "none";
}

function formatNumber(value: number, format: "number" | "compact" | "none"): string {
  if (format === "none") return String(value);
  if (format === "compact") {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

const sizeStyles = {
  sm: { value: "text-lg font-semibold", label: "text-xs" },
  md: { value: "text-2xl font-bold", label: "text-sm" },
  lg: { value: "text-4xl font-bold", label: "text-base" },
};

export function StatValue({ value, label, size = "md", format = "number" }: StatValueProps) {
  const styles = sizeStyles[size];
  const displayValue = typeof value === "number" ? formatNumber(value, format) : value;

  return (
    <div className="flex flex-col">
      <span className={`${styles.value} text-gray-900`}>{displayValue}</span>
      <span className={`${styles.label} text-gray-500`}>{label}</span>
    </div>
  );
}
