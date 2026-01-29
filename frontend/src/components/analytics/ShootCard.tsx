"use client";

import type { ShootMetrics } from "@/lib/api";

interface ShootCardProps {
  shoot: ShootMetrics;
}

export function ShootCard({ shoot }: ShootCardProps) {
  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
      <h3 className="font-semibold text-gray-900 truncate">{shoot.name}</h3>

      {shoot.doctors.length > 0 && (
        <p className="text-xs text-gray-500 mt-1 truncate">
          {shoot.doctors.join(", ")}
        </p>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div>
          <p className="text-lg font-bold text-gray-900">
            {formatNumber(shoot.total_views)}
          </p>
          <p className="text-xs text-gray-500">Views</p>
        </div>
        <div>
          <p className="text-lg font-bold text-gray-900">
            {shoot.post_count}
          </p>
          <p className="text-xs text-gray-500">Posts</p>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
        <span>{formatNumber(shoot.total_likes)} likes</span>
        <span>{formatNumber(shoot.total_comments)} comments</span>
      </div>
    </div>
  );
}

interface ShootsGridProps {
  shoots: ShootMetrics[];
}

export function ShootsGrid({ shoots }: ShootsGridProps) {
  if (shoots.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
        No podcast/shoot data available.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Performance by Podcast
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {shoots.map((shoot) => (
          <ShootCard key={shoot.id} shoot={shoot} />
        ))}
      </div>
    </div>
  );
}
