"use client";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

export function StatCard({ title, value, subtitle, icon, trend }: StatCardProps) {
  const formatNumber = (num: number | string) => {
    if (typeof num === "string") return num;
    return num.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <p className="text-3xl font-bold text-gray-900 mt-2">
        {formatNumber(value)}
      </p>
      {subtitle && (
        <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
      )}
      {trend && (
        <div className={`text-sm mt-1 ${trend.isPositive ? "text-green-600" : "text-red-600"}`}>
          {trend.isPositive ? "+" : ""}{trend.value}%
        </div>
      )}
    </div>
  );
}
