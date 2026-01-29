"use client";

import { useState, useEffect, useCallback } from "react";
import { analyticsApi, type ClipWithPosts } from "@/lib/api";

// Platform URL generators
const getPlatformUrl = (platform: string, providerPostId: string | null): string | null => {
  if (!providerPostId) return null;

  switch (platform.toLowerCase()) {
    case "youtube":
      return `https://youtube.com/watch?v=${providerPostId}`;
    case "linkedin":
      return `https://linkedin.com/feed/update/${providerPostId}`;
    case "x":
    case "twitter":
      return `https://x.com/i/status/${providerPostId}`;
    default:
      return null;
  }
};

const getPlatformIcon = (platform: string) => {
  switch (platform.toLowerCase()) {
    case "youtube":
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
        </svg>
      );
    case "linkedin":
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>
      );
    case "x":
    case "twitter":
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
      );
    default:
      return null;
  }
};

const formatNumber = (num: number): string => {
  return num.toLocaleString();
};

const formatDate = (dateStr: string | null): string | null => {
  if (!dateStr) return null;
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return null;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "published":
      return "bg-green-100 text-green-800";
    case "scheduled":
      return "bg-blue-100 text-blue-800";
    case "ready":
      return "bg-yellow-100 text-yellow-800";
    case "draft":
      return "bg-gray-100 text-gray-800";
    case "failed":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

export default function ClipsPage() {
  const [clips, setClips] = useState<ClipWithPosts[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [platform, setPlatform] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [sortBy, setSortBy] = useState<"views" | "likes" | "recent" | "title" | "posted">("views");

  // Pagination
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 50;

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setOffset(0); // Reset pagination on search
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchClips = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyticsApi.searchClips({
        q: debouncedQuery || undefined,
        platform: platform || undefined,
        status: status || undefined,
        sort_by: sortBy,
        limit: LIMIT,
        offset,
      });
      setClips(data);
      setHasMore(data.length === LIMIT);
    } catch (err) {
      console.error("Failed to fetch clips:", err);
      setError("Failed to load clips. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [debouncedQuery, platform, status, sortBy, offset]);

  useEffect(() => {
    fetchClips();
  }, [fetchClips]);

  const handlePrevPage = () => {
    setOffset(Math.max(0, offset - LIMIT));
  };

  const handleNextPage = () => {
    if (hasMore) {
      setOffset(offset + LIMIT);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clips Library</h1>
          <p className="text-sm text-gray-500 mt-1">
            Search and view all clips with their platform posts
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Search */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, description, or tags..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Platform Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Platform
            </label>
            <select
              value={platform}
              onChange={(e) => {
                setPlatform(e.target.value);
                setOffset(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Platforms</option>
              <option value="youtube">YouTube</option>
              <option value="linkedin">LinkedIn</option>
              <option value="x">X (Twitter)</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="published">Published</option>
              <option value="scheduled">Scheduled</option>
              <option value="ready">Ready</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </div>

        {/* Sort */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-sm text-gray-500">Sort by:</span>
          <div className="flex gap-2">
            {[
              { value: "views", label: "Views" },
              { value: "likes", label: "Likes" },
              { value: "posted", label: "Date Posted" },
              { value: "recent", label: "Recent" },
              { value: "title", label: "Title" },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  setSortBy(option.value as typeof sortBy);
                  setOffset(0);
                }}
                className={`px-3 py-1 text-sm rounded-full ${
                  sortBy === option.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Clips Grid */}
      {!isLoading && clips.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clips.map((clip) => (
            <div
              key={clip.id}
              className="bg-white rounded-lg shadow overflow-hidden hover:shadow-md transition-shadow"
            >
              {/* Clip Header */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-gray-900 line-clamp-2 flex-1">
                    {clip.title || "Untitled Clip"}
                  </h3>
                  <span
                    className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(
                      clip.status
                    )}`}
                  >
                    {clip.status}
                  </span>
                </div>

                {/* Description */}
                {clip.description && (
                  <p className="text-sm text-gray-500 line-clamp-2 mb-3">
                    {clip.description}
                  </p>
                )}

                {/* Tags */}
                {clip.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {clip.tags.slice(0, 3).map((tag, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {clip.tags.length > 3 && (
                      <span className="px-2 py-0.5 text-xs text-gray-400">
                        +{clip.tags.length - 3} more
                      </span>
                    )}
                  </div>
                )}

                {/* Platform Posts with metrics */}
                {clip.posts.length > 0 ? (
                  <div className="border-t pt-3">
                    {/* Post date */}
                    {clip.earliest_posted_at && (
                      <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span>{formatDate(clip.earliest_posted_at)}</span>
                      </div>
                    )}
                    {/* Platform badges with per-post metrics */}
                    <div className="flex flex-wrap gap-2">
                      {clip.posts.map((post) => {
                        const url = getPlatformUrl(post.platform, post.provider_post_id);
                        return (
                          <a
                            key={post.id}
                            href={url || "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs ${
                              url
                                ? "bg-blue-50 text-blue-700 hover:bg-blue-100"
                                : "bg-gray-50 text-gray-500 cursor-default"
                            }`}
                            onClick={(e) => !url && e.preventDefault()}
                            title={url ? `View on ${post.platform}` : "No link available"}
                          >
                            {getPlatformIcon(post.platform)}
                            <span className="capitalize">{post.platform}</span>
                            <span className="text-gray-400">
                              {formatNumber(post.view_count)}
                            </span>
                          </a>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="border-t pt-3">
                    <p className="text-xs text-gray-400">Not yet posted</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && clips.length === 0 && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Clips Found</h3>
          <p className="text-gray-500">
            {debouncedQuery || platform || status
              ? "Try adjusting your search or filters"
              : "Clips will appear here once synced from the ops-console"}
          </p>
        </div>
      )}

      {/* Pagination */}
      {!isLoading && clips.length > 0 && (
        <div className="flex items-center justify-between bg-white rounded-lg shadow px-4 py-3">
          <div className="text-sm text-gray-500">
            Showing {offset + 1} - {offset + clips.length}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handlePrevPage}
              disabled={offset === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={handleNextPage}
              disabled={!hasMore}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
