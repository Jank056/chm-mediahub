"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { clientsApi, type KOLGroupDetail, type ShootSummary, type ClipSummary } from "@/lib/api";
import { Avatar, Badge, KOLChip, PlatformIcon, StatValue } from "@/components/clients";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

function ClipCard({ clip }: { clip: ClipSummary }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
      <div className="flex items-start gap-4">
        {/* Thumbnail placeholder */}
        <div className="w-24 h-16 bg-gray-200 rounded flex-shrink-0 flex items-center justify-center">
          {clip.video_preview_url ? (
            <img
              src={clip.video_preview_url}
              alt={clip.title || "Clip"}
              className="w-full h-full object-cover rounded"
            />
          ) : (
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="font-medium text-gray-900 text-sm line-clamp-2">
              {clip.title || "Untitled Clip"}
            </h4>
            <div className="flex items-center gap-2 flex-shrink-0">
              {clip.platform && <PlatformIcon platform={clip.platform} size="sm" />}
              {clip.is_short && (
                <Badge variant="info" size="sm">Short</Badge>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              {formatNumber(clip.total_views)}
            </span>
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
              {formatNumber(clip.total_likes)}
            </span>
            {clip.post_count > 0 && (
              <span>{clip.post_count} platform{clip.post_count > 1 ? "s" : ""}</span>
            )}
            {clip.earliest_posted_at && (
              <span>Posted {formatDate(clip.earliest_posted_at)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ShootSection({ shoot }: { shoot: ShootSummary }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="bg-white rounded-xl shadow">
      {/* Shoot Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <svg
              className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <h3 className="font-semibold text-gray-900">{shoot.name}</h3>
          </div>
          {shoot.shoot_date && (
            <span className="text-sm text-gray-500">{formatDate(shoot.shoot_date)}</span>
          )}
        </div>

        <div className="flex items-center gap-6 text-sm">
          <span className="text-gray-600">
            <strong>{shoot.clip_count}</strong> clips
          </span>
          <span className="text-gray-600">
            <strong>{formatNumber(shoot.total_views)}</strong> views
          </span>
        </div>
      </button>

      {/* Clips List */}
      {expanded && shoot.clips.length > 0 && (
        <div className="border-t border-gray-100 p-4 space-y-3">
          {shoot.clips.map((clip) => (
            <ClipCard key={clip.id} clip={clip} />
          ))}
        </div>
      )}

      {expanded && shoot.clips.length === 0 && (
        <div className="border-t border-gray-100 p-6 text-center text-gray-500 text-sm">
          No clips linked to this shoot yet
        </div>
      )}
    </div>
  );
}

export default function KOLGroupDetailPage() {
  const params = useParams();
  const slug = params.slug as string;
  const projectCode = params.projectId as string;
  const groupId = params.groupId as string;

  const [group, setGroup] = useState<KOLGroupDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await clientsApi.getKOLGroup(slug, projectCode, groupId);
        setGroup(data);
      } catch (err) {
        setError("Failed to load KOL group");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [slug, projectCode, groupId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !group) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error || "KOL group not found"}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        <Link href="/dashboard/clients" className="hover:text-blue-600">
          Clients
        </Link>
        <span className="mx-2">/</span>
        <Link href={`/dashboard/clients/${group.client_slug}`} className="hover:text-blue-600">
          {group.client_slug}
        </Link>
        <span className="mx-2">/</span>
        <Link
          href={`/dashboard/clients/${group.client_slug}/projects/${group.project_code}`}
          className="hover:text-blue-600"
        >
          {group.project_name}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{group.name}</span>
      </nav>

      {/* Group Header */}
      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{group.name}</h1>
              {group.publish_day && (
                <Badge variant="info" size="md">{group.publish_day}</Badge>
              )}
            </div>
            <p className="text-gray-500">
              {group.project_name} &bull; {group.kol_count} KOL{group.kol_count !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {/* KOLs */}
        {group.kols.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {group.kols.map((kol) => (
              <KOLChip key={kol.id} kol={kol} size="md" />
            ))}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-gray-100">
          <StatValue value={group.shoots?.length || 0} label="Podcasts" />
          <StatValue value={group.clip_count} label="Clips" />
          <StatValue value={group.total_views} label="Total Views" format="compact" />
          <StatValue value={group.video_count || 0} label="Videos Planned" />
        </div>
      </div>

      {/* Shoots Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Podcasts & Clips ({group.shoots?.length || 0})
          </h2>
        </div>

        {(!group.shoots || group.shoots.length === 0) ? (
          <div className="bg-white rounded-xl shadow p-8 text-center">
            <p className="text-gray-500">No podcasts linked to this KOL group yet</p>
            <p className="text-sm text-gray-400 mt-2">
              Sync shoots from ops-console to see them here
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {group.shoots.map((shoot) => (
              <ShootSection key={shoot.id} shoot={shoot} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
