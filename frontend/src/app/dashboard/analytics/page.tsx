"use client";

import { useState, useEffect } from "react";
import {
  analyticsApi,
  type AnalyticsSummary,
  type PostMetrics,
  type ShootMetrics,
  type PlatformStats,
  type TimelineEntry,
  type TrendEntry,
} from "@/lib/api";
import {
  StatCard,
  PlatformChart,
  TimelineChart,
  TrendsChart,
  PostsTable,
  ShootsGrid,
  FilterBar,
} from "@/components/analytics";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [topPosts, setTopPosts] = useState<PostMetrics[]>([]);
  const [shoots, setShoots] = useState<ShootMetrics[]>([]);
  const [platforms, setPlatforms] = useState<PlatformStats[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [followerTrends, setFollowerTrends] = useState<{ label: string; data: TrendEntry[]; color: string }[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState(30);
  const [sourceFilter, setSourceFilter] = useState<"official" | "branded" | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const sourceParam = sourceFilter || undefined;
        // Fetch all data in parallel
        const [summaryData, postsData, shootsData, platformsData, timelineData] =
          await Promise.all([
            analyticsApi.getSummary({ source: sourceParam }),
            analyticsApi.getTopPosts({ limit: 10, platform: selectedPlatform || undefined, source: sourceParam }),
            analyticsApi.getShoots({ sort_by: "views" }),
            analyticsApi.getPlatforms({ source: sourceParam }),
            analyticsApi.getTimeline({ days: dateRange, platform: selectedPlatform || undefined, source: sourceParam }),
          ]);

        setSummary(summaryData);
        setTopPosts(postsData);
        setShoots(shootsData);
        setPlatforms(platformsData);
        setTimeline(timelineData);

        // Fetch follower/subscriber growth trends (fire-and-forget style)
        const trendConfigs = [
          { platform: "youtube", metric: "subscriber_count", label: "YouTube Subscribers", color: "#FF0000" },
          { platform: "x", metric: "follower_count", label: "X Followers", color: "#000000" },
          { platform: "linkedin", metric: "follower_count", label: "LinkedIn Followers", color: "#0077B5" },
          { platform: "facebook", metric: "follower_count", label: "Facebook Followers", color: "#1877F2" },
          { platform: "instagram", metric: "follower_count", label: "Instagram Followers", color: "#E4405F" },
        ];
        const trendResults = await Promise.all(
          trendConfigs.map((cfg) =>
            analyticsApi.getTrends({ platform: cfg.platform, metric_name: cfg.metric, days: dateRange })
              .then((data) => ({ ...cfg, data }))
              .catch(() => ({ ...cfg, data: [] as TrendEntry[] }))
          )
        );
        setFollowerTrends(trendResults.filter((t) => t.data.length > 0));

        setError(null);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
        setError("Failed to load analytics data. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [selectedPlatform, dateRange, sourceFilter]);

  const formatLastUpdated = (dateStr: string | null) => {
    if (!dateStr) return "Never synced";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const availablePlatforms = platforms.map((p) => p.platform);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        {summary?.last_updated && (
          <span className="text-sm text-gray-500">
            Last synced: {formatLastUpdated(summary.last_updated)}
          </span>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Source Toggle */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        {([
          { value: null, label: "All Content" },
          { value: "official" as const, label: "Official Channels" },
          { value: "branded" as const, label: "Branded Accounts" },
        ]).map((opt) => (
          <button
            key={opt.label}
            onClick={() => setSourceFilter(opt.value)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              sourceFilter === opt.value
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Filter Bar */}
      <FilterBar
        platforms={availablePlatforms}
        selectedPlatform={selectedPlatform}
        onPlatformChange={setSelectedPlatform}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
      />

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Total Posts"
            value={summary.total_posts}
            subtitle={`${summary.total_clips} clips`}
          />
          <StatCard
            title="Total Views"
            value={summary.total_views}
          />
          <StatCard
            title="Total Likes"
            value={summary.total_likes}
          />
          <StatCard
            title="Total Comments"
            value={summary.total_comments}
          />
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {timeline.length > 0 && <TimelineChart data={timeline} metric="views" />}
        {platforms.length > 0 && <PlatformChart data={platforms} />}
      </div>

      {/* Growth Trends */}
      {followerTrends.length > 0 && (
        <TrendsChart series={followerTrends} title="Follower Growth" />
      )}

      {/* Top Posts Table */}
      {topPosts.length > 0 && (
        <PostsTable posts={topPosts} title="Top Performing Posts" />
      )}

      {/* Shoots Grid */}
      {shoots.length > 0 && <ShootsGrid shoots={shoots} />}

      {/* Empty State */}
      {!summary?.total_posts && !isLoading && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Analytics Data Yet
          </h3>
          <p className="text-gray-500">
            Posts will appear here once synced from your ops-console.
            Engagement metrics (views, likes, comments) will be tracked automatically.
          </p>
        </div>
      )}
    </div>
  );
}
