"use client";

import type { ClientAnalytics } from "@/lib/api";

interface StatsGridProps {
  analytics: ClientAnalytics;
}

function StatBox({
  value,
  label,
  icon,
}: {
  value: number | string;
  label: string;
  icon?: React.ReactNode;
}) {
  const formattedValue =
    typeof value === "number"
      ? value >= 1_000_000
        ? `${(value / 1_000_000).toFixed(1)}M`
        : value >= 1_000
        ? `${(value / 1_000).toFixed(1)}K`
        : value.toLocaleString()
      : value;

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <span className="text-3xl font-bold text-gray-900">{formattedValue}</span>
    </div>
  );
}

export function StatsGrid({ analytics }: StatsGridProps) {
  return (
    <div className="space-y-6">
      {/* Primary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox value={analytics.kol_group_count} label="KOL Groups" />
        <StatBox value={analytics.kol_count} label="KOLs" />
        <StatBox value={analytics.total_clips} label="Clips" />
        <StatBox value={analytics.total_posts} label="Posts" />
      </div>

      {/* Engagement Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox value={analytics.total_views} label="Total Views" />
        <StatBox value={analytics.total_likes} label="Total Likes" />
        <StatBox value={analytics.total_comments} label="Total Comments" />
        <StatBox value={analytics.total_shares} label="Total Shares" />
      </div>
    </div>
  );
}
