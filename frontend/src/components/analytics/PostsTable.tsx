"use client";

import { useState } from "react";
import type { PostMetrics } from "@/lib/api";

interface PostsTableProps {
  posts: PostMetrics[];
  title?: string;
  showSource?: boolean;
  pageSize?: number;
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

export function PostsTable({
  posts,
  title = "Top Performing Posts",
  showSource = false,
  pageSize = 10,
}: PostsTableProps) {
  const [sortBy, setSortBy] = useState<"views" | "likes" | "comments" | "posted_at">("views");
  const [page, setPage] = useState(0);

  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const sortedPosts = [...posts].sort((a, b) => {
    if (sortBy === "views") return b.view_count - a.view_count;
    if (sortBy === "likes") return b.like_count - a.like_count;
    if (sortBy === "comments") return b.comment_count - a.comment_count;
    if (sortBy === "posted_at") {
      const dateA = a.posted_at ? new Date(a.posted_at).getTime() : 0;
      const dateB = b.posted_at ? new Date(b.posted_at).getTime() : 0;
      return dateB - dateA;
    }
    return 0;
  });

  const totalPages = Math.ceil(sortedPosts.length / pageSize);
  const paginatedPosts = sortedPosts.slice(page * pageSize, (page + 1) * pageSize);

  const engagementRate = (post: PostMetrics) => {
    if (post.view_count === 0) return 0;
    return ((post.like_count + post.comment_count + post.share_count) / post.view_count) * 100;
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <p className="text-sm text-gray-500">{posts.length} posts</p>
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
            <option value="posted_at">Date</option>
          </select>
        </div>
      </div>

      {posts.length === 0 ? (
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
                {paginatedPosts.map((post, idx) => (
                  <tr key={post.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="flex-shrink-0 text-sm font-medium text-gray-400 w-5 text-right">
                          {page * pageSize + idx + 1}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate max-w-sm">
                            {post.title || (post.platform === "x" ? "Tweet" : "Post")}
                          </p>
                          {post.provider_post_id && (
                            <p className="text-xs text-gray-400 truncate">
                              {post.provider_post_id.length > 30
                                ? `...${post.provider_post_id.slice(-20)}`
                                : post.provider_post_id}
                            </p>
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
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sortedPosts.length)} of {sortedPosts.length}
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
