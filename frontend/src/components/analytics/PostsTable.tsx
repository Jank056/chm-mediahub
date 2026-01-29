"use client";

import { useState } from "react";
import type { PostMetrics } from "@/lib/api";

interface PostsTableProps {
  posts: PostMetrics[];
  title?: string;
}

const PLATFORM_COLORS: Record<string, string> = {
  youtube: "bg-red-500",
  linkedin: "bg-blue-700",
  x: "bg-gray-900",
  unknown: "bg-gray-400",
};

export function PostsTable({ posts, title = "Top Performing Posts" }: PostsTableProps) {
  const [sortBy, setSortBy] = useState<"views" | "likes" | "posted_at">("views");

  const formatNumber = (num: number) => {
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
    if (sortBy === "posted_at") {
      const dateA = a.posted_at ? new Date(a.posted_at).getTime() : 0;
      const dateB = b.posted_at ? new Date(b.posted_at).getTime() : 0;
      return dateB - dateA;
    }
    return 0;
  });

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="views">Views</option>
            <option value="likes">Likes</option>
            <option value="posted_at">Date</option>
          </select>
        </div>
      </div>

      {posts.length === 0 ? (
        <div className="px-6 py-8 text-center text-gray-500">
          <p>No posts available.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Platform
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Views
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Likes
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Comments
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Posted
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedPosts.map((post) => (
                <tr key={post.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="max-w-xs truncate">
                      <span className="text-sm font-medium text-gray-900">
                        {post.title || "Untitled"}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full text-white capitalize ${
                        PLATFORM_COLORS[post.platform.toLowerCase()] || PLATFORM_COLORS.unknown
                      }`}
                    >
                      {post.platform}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-gray-900 font-medium">
                    {formatNumber(post.view_count)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-gray-900">
                    {formatNumber(post.like_count)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-gray-900">
                    {formatNumber(post.comment_count)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-gray-500">
                    {formatDate(post.posted_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
