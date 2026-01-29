"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TimelineEntry } from "@/lib/api";

interface TimelineChartProps {
  data: TimelineEntry[];
  metric?: "views" | "posts" | "likes";
}

export function TimelineChart({ data, metric = "views" }: TimelineChartProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  const chartData = data.map((entry) => ({
    date: formatDate(entry.date),
    fullDate: entry.date,
    views: entry.views,
    posts: entry.post_count,
    likes: entry.likes,
  }));

  const getMetricConfig = () => {
    switch (metric) {
      case "posts":
        return { dataKey: "posts", color: "#3B82F6", label: "Posts" };
      case "likes":
        return { dataKey: "likes", color: "#EF4444", label: "Likes" };
      default:
        return { dataKey: "views", color: "#10B981", label: "Views" };
    }
  };

  const config = getMetricConfig();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        {config.label} Over Time
      </h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id={`color${config.dataKey}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={config.color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={config.color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={formatNumber}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value: number) => [formatNumber(value), config.label]}
              labelFormatter={(label) => `Date: ${label}`}
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Area
              type="monotone"
              dataKey={config.dataKey}
              stroke={config.color}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#color${config.dataKey})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
