"use client";

import Link from "next/link";
import { Badge } from "./Badge";
import { StatValue } from "./StatValue";
import type { KOLGroupSummary } from "@/lib/api";

interface KOLGroupCardProps {
  group: KOLGroupSummary;
  clientSlug: string;
  projectCode: string;
}

export function KOLGroupCard({ group, clientSlug, projectCode }: KOLGroupCardProps) {
  return (
    <Link
      href={`/dashboard/clients/${clientSlug}/projects/${projectCode}/groups/${group.id}`}
      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-5"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{group.name}</h3>
        </div>
        <div className="flex gap-2">
          {group.publish_day && (
            <Badge variant="info">{group.publish_day}</Badge>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4 pt-3 border-t border-gray-100">
        <StatValue value={group.video_count || 0} label="Videos" size="sm" />
        <StatValue value={group.kol_count} label="KOLs" size="sm" />
        <StatValue value={group.total_views} label="Views" size="sm" format="compact" />
      </div>
    </Link>
  );
}
