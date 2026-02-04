"use client";

import { useState } from "react";
import type { PostMetrics } from "@/lib/api";

interface PostsTableProps {
  posts: PostMetrics[];
  title?: string;
  showSource?: boolean;
  pageSize?: number;
  contentTypeFilter?: string | null;
  onContentTypeFilterChange?: (value: string | null) => void;
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: "bg-red-500",
  linkedin: "bg-blue-700",
  x: "bg-gray-900",
  facebook: "bg-[#1877F2]",
  instagram: "bg-[#E4405F]",
  unknown: "bg-gray-400",
};

const PLATFORM_ICONS: Record<string, string> = {
  youtube: "YT",
  linkedin: "LI",
  x: "X",
  facebook: "FB",
  instagram: "IG",
};

const CONTENT_TYPE_BADGES: Record<string, { label: string; color: string }> = {
  video: { label: "Video", color: "bg-purple-100 text-purple-700" },
  image: { label: "Image", color: "bg-blue-100 text-blue-700" },
  article: { label: "Article", color: "bg-amber-100 text-amber-700" },
  text: { label: "Text", color: "bg-gray-100 text-gray-600" },
  carousel: { label: "Carousel", color: "bg-teal-100 text-teal-700" },
  poll: { label: "Poll", color: "bg-orange-100 text-orange-700" },
  gif: { label: "GIF", color: "bg-pink-100 text-pink-700" },
  media: { label: "Media", color: "bg-indigo-100 text-indigo-700" },
};

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function PostsTable({
  posts,
  title = "Top Performing Posts",
  showSource = false,
  pageSize = 10,
  contentTypeFilter = null,
  onContentTypeFilterChange,
}: PostsTableProps) {
  const [sortBy, setSortBy] = useState<"views" | "likes" | "comments" | "engagement" | "posted_at">("views");
  const [page, setPage] = useState(0);

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "\u2014";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Filter by content type
  const filteredPosts = contentTypeFilter
    ? posts.filter((p) => p.content_type === contentTypeFilter)
    : posts;

  const sortedPosts = [...filteredPosts].sort((a, b) => {
    if (sortBy === "views") return b.view_count - a.view_count;
    if (sortBy === "likes") return b.like_count - a.like_count;
    if (sortBy === "comments") return b.comment_count - a.comment_count;
    if (sortBy === "engagement") return engagementRate(b) - engagementRate(a);
    if (sortBy === "posted_at") {
      const dateA = a.posted_at ? new Date(a.posted_at).getTime() : 0;
      const dateB = b.posted_at ? new Date(b.posted_at).getTime() : 0;
      return dateB - dateA;
    }
    return 0;
  });

  const totalPages = Math.ceil(sortedPosts.length / pageSize);
  const paginatedPosts = sortedPosts.slice(page * pageSize, (page + 1) * pageSize);

  function engagementRate(post: PostMetrics) {
    if (post.view_count === 0) return 0;
    return ((post.like_count + post.comment_count + post.share_count) / post.view_count) * 100;
  }

  // Compute content type counts for filter chips
  const contentTypeCounts: Record<string, number> = {};
  posts.forEach((p) => {
    const ct = p.content_type || "unknown";
    contentTypeCounts[ct] = (contentTypeCounts[ct] || 0) + 1;
  });

  // Compute aggregate stats
  const shortsCount = posts.filter((p) => p.is_short).length;
  const avgDuration = (() => {
    const withDuration = posts.filter((p) => p.duration_seconds && p.duration_seconds > 0);
    if (withDuration.length === 0) return null;
    const total = withDuration.reduce((sum, p) => sum + (p.duration_seconds || 0), 0);
    return Math.round(total / withDuration.length);
  })();

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-sm text-gray-500">{filteredPosts.length} posts</span>
              {shortsCount > 0 && (
                <span className="text-xs text-gray-400">
                  {shortsCount} short{shortsCount !== 1 ? "s" : ""}
                </span>
              )}
              {avgDuration !== null && (
                <span className="text-xs text-gray-400">
                  Avg duration: {formatDuration(avgDuration)}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as typeof sortBy);
                setPage(0);
              }}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="views">Views</option>
              <option value="likes">Likes</option>
              <option value="comments">Comments</option>
              <option value="engagement">Engagement</option>
              <option value="posted_at">Date</option>
            </select>
          </div>
        </div>

        {/* Content Type Filter Chips */}
        {onContentTypeFilterChange && Object.keys(contentTypeCounts).length > 1 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-3">
            <button
              onClick={() => { onContentTypeFilterChange(null); setPage(0); }}
              className={`px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                !contentTypeFilter
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              All
            </button>
            {Object.entries(contentTypeCounts)
              .filter(([ct]) => ct !== "unknown")
              .sort(([, a], [, b]) => b - a)
              .map(([ct, count]) => {
                const badge = CONTENT_TYPE_BADGES[ct];
                return (
                  <button
                    key={ct}
                    onClick={() => { onContentTypeFilterChange(contentTypeFilter === ct ? null : ct); setPage(0); }}
                    className={`px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                      contentTypeFilter === ct
                        ? "bg-gray-900 text-white"
                        : badge?.color || "bg-gray-100 text-gray-600"
                    } hover:opacity-80`}
                  >
                    {badge?.label || ct} ({count})
                  </button>
                );
              })}
          </div>
        )}
      </div>

      {filteredPosts.length === 0 ? (
        <div className="px-6 py-8 text-center text-gray-500">
          <p>No posts available.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Post
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Platform
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  {showSource && (
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Source
                    </th>
                  )}
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Views
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Likes
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Comments
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Eng. Rate
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Posted
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {paginatedPosts.map((post, idx) => {
                  const badge = CONTENT_TYPE_BADGES[post.content_type || ""] || null;
                  return (
                    <tr key={post.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {/* Thumbnail */}
                          {post.thumbnail_url ? (
                            <div className="flex-shrink-0 w-16 h-10 relative rounded overflow-hidden bg-gray-100">
                              <img
                                src={post.thumbnail_url}
                                alt=""
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                              {post.duration_seconds != null && post.duration_seconds > 0 && (
                                <span className="absolute bottom-0.5 right-0.5 bg-black/80 text-white text-[10px] px-1 rounded">
                                  {formatDuration(post.duration_seconds)}
                                </span>
                              )}
                              {post.is_short && (
                                <span className="absolute top-0.5 left-0.5 bg-red-500 text-white text-[9px] px-1 rounded font-bold">
                                  SHORT
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="flex-shrink-0 text-sm font-medium text-gray-400 w-5 text-right">
                              {page * pageSize + idx + 1}
                            </span>
                          )}
                          <div className="min-w-0">
                            {post.content_url ? (
                              <a
                                href={post.content_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm font-medium text-gray-900 truncate max-w-xs block hover:text-blue-600 hover:underline"
                              >
                                {post.title || (post.platform === "x" ? "Tweet" : "Post")}
                              </a>
                            ) : (
                              <p className="text-sm font-medium text-gray-900 truncate max-w-xs">
                                {post.title || (post.platform === "x" ? "Tweet" : "Post")}
                              </p>
                            )}
                            {/* Hashtags */}
                            {post.hashtags && post.hashtags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-0.5">
                                {post.hashtags.slice(0, 3).map((tag) => (
                                  <span key={tag} className="text-[10px] text-blue-600 bg-blue-50 px-1 rounded">
                                    #{tag}
                                  </span>
                                ))}
                                {post.hashtags.length > 3 && (
                                  <span className="text-[10px] text-gray-400">
                                    +{post.hashtags.length - 3}
                                  </span>
                                )}
                              </div>
                            )}
                            {/* Language badge */}
                            {post.language && post.language !== "en" && (
                              <span className="text-[10px] text-gray-400 uppercase">
                                {post.language}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span
                          className={`inline-flex items-center justify-center w-8 h-8 text-xs font-bold rounded-full text-white ${
                            PLATFORM_COLORS[post.platform.toLowerCase()] || PLATFORM_COLORS.unknown
                          }`}
                        >
                          {PLATFORM_ICONS[post.platform.toLowerCase()] || post.platform.slice(0, 2).toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-center">
                        {badge ? (
                          <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${badge.color}`}>
                            {badge.label}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">{"\u2014"}</span>
                        )}
                      </td>
                      {showSource && (
                        <td className="px-4 py-4 text-center">
                          <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
                            post.clip_id
                              ? "bg-purple-100 text-purple-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}>
                            {post.clip_id ? "Branded" : "Official"}
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-4 text-right">
                        <span className="text-sm font-semibold text-gray-900">
                          {formatNumber(post.view_count)}
                        </span>
                        {post.impression_count > 0 && post.impression_count !== post.view_count && (
                          <p className="text-[10px] text-gray-400">{formatNumber(post.impression_count)} impr</p>
                        )}
                      </td>
                      <td className="px-4 py-4 text-right text-sm text-gray-700">
                        {formatNumber(post.like_count)}
                      </td>
                      <td className="px-4 py-4 text-right text-sm text-gray-700">
                        {formatNumber(post.comment_count)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <span className={`text-sm font-medium ${
                          engagementRate(post) >= 5
                            ? "text-green-600"
                            : engagementRate(post) >= 2
                            ? "text-yellow-600"
                            : "text-gray-500"
                        }`}>
                          {engagementRate(post).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right text-sm text-gray-500">
                        {formatDate(post.posted_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Showing {page * pageSize + 1}{"\u2013"}{Math.min((page + 1) * pageSize, sortedPosts.length)} of {sortedPosts.length}
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  const pageNum = totalPages <= 5 ? i : Math.max(0, Math.min(page - 2, totalPages - 5)) + i;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`px-3 py-1 text-sm border rounded-md ${
                        page === pageNum
                          ? "bg-blue-600 text-white border-blue-600"
                          : "border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      {pageNum + 1}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
