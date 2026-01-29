"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { PlatformStats } from "@/lib/api";

interface PlatformChartProps {
  data: PlatformStats[];
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: "#FF0000",
  linkedin: "#0077B5",
  x: "#000000",
  unknown: "#9CA3AF",
};

export function PlatformChart({ data }: PlatformChartProps) {
  const chartData = data.map((item) => ({
    name: item.platform.charAt(0).toUpperCase() + item.platform.slice(1),
    posts: item.post_count,
    views: item.total_views,
    likes: item.total_likes,
    platform: item.platform.toLowerCase(),
  }));

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Platform Performance
      </h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
            <XAxis type="number" tickFormatter={formatNumber} />
            <YAxis type="category" dataKey="name" width={80} />
            <Tooltip
              formatter={(value: number) => formatNumber(value)}
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Bar dataKey="views" name="Views" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PLATFORM_COLORS[entry.platform] || PLATFORM_COLORS.unknown}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend with additional stats */}
      <div className="mt-4 grid grid-cols-3 gap-4">
        {data.map((platform) => (
          <div
            key={platform.platform}
            className="flex items-center gap-2 p-2 rounded-lg bg-gray-50"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{
                backgroundColor:
                  PLATFORM_COLORS[platform.platform.toLowerCase()] ||
                  PLATFORM_COLORS.unknown,
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 capitalize truncate">
                {platform.platform}
              </p>
              <p className="text-xs text-gray-500">
                {platform.post_count} posts
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
