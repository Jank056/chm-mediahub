"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { analyticsApi, type ContentItem } from "@/lib/api";

// Platform URL generators
const getPlatformUrl = (platform: string, contentUrl: string | null): string | null => {
  return contentUrl || null;
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
    case "facebook":
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
        </svg>
      );
    case "instagram":
      return (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/>
        </svg>
      );
    default:
      return null;
  }
};

const getPlatformColor = (platform: string) => {
  switch (platform.toLowerCase()) {
    case "youtube": return "text-red-600";
    case "linkedin": return "text-blue-700";
    case "x": case "twitter": return "text-gray-800";
    case "facebook": return "text-blue-600";
    case "instagram": return "text-pink-600";
    default: return "text-gray-600";
  }
};

const formatNumber = (num: number): string => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
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

// Tag category display config
const TAG_CATEGORIES: Record<string, { label: string; color: string }> = {
  biomarker: { label: "Biomarker", color: "bg-purple-100 text-purple-800 border-purple-200" },
  stage: { label: "Stage", color: "bg-amber-100 text-amber-800 border-amber-200" },
  drug: { label: "Drug", color: "bg-blue-100 text-blue-800 border-blue-200" },
  trial: { label: "Trial", color: "bg-green-100 text-green-800 border-green-200" },
  topic: { label: "Topic", color: "bg-red-100 text-red-800 border-red-200" },
  doctor: { label: "Doctor", color: "bg-teal-100 text-teal-800 border-teal-200" },
  brand: { label: "Brand", color: "bg-gray-100 text-gray-800 border-gray-200" },
};

const getTagDisplay = (tag: string) => {
  if (!tag.includes(":")) return { category: "other", value: tag, color: "bg-gray-100 text-gray-600" };
  const [category, value] = tag.split(":", 2);
  const config = TAG_CATEGORIES[category];
  return {
    category,
    value,
    color: config?.color || "bg-gray-100 text-gray-600 border-gray-200",
  };
};

export default function ContentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [content, setContent] = useState<ContentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Source filter from URL or default
  const initialSource = searchParams.get("source") as "official" | "branded" | null;
  const initialTag = searchParams.get("tag");

  const [source, setSource] = useState<"official" | "branded" | "">(initialSource || "official");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [platform, setPlatform] = useState<string>("");
  const [sortBy, setSortBy] = useState<"views" | "likes" | "posted_at" | "comments">("views");

  // Tag filters
  const [availableTags, setAvailableTags] = useState<Record<string, string[]>>({});
  const [selectedTags, setSelectedTags] = useState<string[]>(initialTag ? [initialTag] : []);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [openTagRow, setOpenTagRow] = useState<string | null>(null);

  // Pagination
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 50;

  // Load available tags on mount
  useEffect(() => {
    analyticsApi.getTags().then(setAvailableTags).catch(() => {});
  }, []);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const toggleTag = (fullTag: string) => {
    setSelectedTags((prev) =>
      prev.includes(fullTag) ? prev.filter((t) => t !== fullTag) : [...prev, fullTag]
    );
    setOffset(0);
  };

  const clearTags = () => {
    setSelectedTags([]);
    setExpandedCategory(null);
    setOffset(0);
  };

  const fetchContent = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyticsApi.searchContent({
        q: debouncedQuery || undefined,
        platform: platform || undefined,
        source: source || undefined,
        tag: selectedTags.length > 0 ? selectedTags.join(",") : undefined,
        sort_by: sortBy,
        limit: LIMIT,
        offset,
      });
      setContent(data);
      setHasMore(data.length === LIMIT);
    } catch (err) {
      console.error("Failed to fetch content:", err);
      setError("Failed to load content. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [debouncedQuery, platform, source, selectedTags, sortBy, offset]);

  useEffect(() => {
    fetchContent();
  }, [fetchContent]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-tag-dropdown]")) {
        setExpandedCategory(null);
      }
      if (!target.closest("[data-row-tags]")) {
        setOpenTagRow(null);
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Content Library</h1>
          <p className="text-sm text-gray-500 mt-1">
            Browse all content across official and branded channels
          </p>
        </div>
      </div>

      {/* Source Toggle + Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        {/* Source toggle */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm font-medium text-gray-700">Source:</span>
          <div className="flex gap-1">
            {[
              { value: "", label: "All Content" },
              { value: "official", label: "Official Channels" },
              { value: "branded", label: "Branded Accounts" },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  setSource(option.value as typeof source);
                  setOffset(0);
                }}
                className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                  source === option.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

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
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
            </select>
          </div>

          {/* Sort */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sort by
            </label>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as typeof sortBy);
                setOffset(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="views">Most Views</option>
              <option value="likes">Most Likes</option>
              <option value="comments">Most Comments</option>
              <option value="posted_at">Most Recent</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tag Filters */}
      {Object.keys(availableTags).length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          {/* Active tag pills */}
          {selectedTags.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="text-xs font-medium text-gray-500">Active filters:</span>
              {selectedTags.map((tag) => {
                const { category, value, color } = getTagDisplay(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${color}`}
                  >
                    <span className="opacity-60">{TAG_CATEGORIES[category]?.label || category}:</span>
                    {value}
                    <svg className="w-3 h-3 ml-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                );
              })}
              <button
                onClick={clearTags}
                className="text-xs text-gray-400 hover:text-gray-600 underline"
              >
                Clear all
              </button>
            </div>
          )}

          {/* Category chips */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(availableTags)
              .filter(([cat]) => TAG_CATEGORIES[cat])
              .sort(([a], [b]) => {
                const order = Object.keys(TAG_CATEGORIES);
                return order.indexOf(a) - order.indexOf(b);
              })
              .map(([category, values]) => (
                <div key={category} className="relative" data-tag-dropdown>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedCategory(expandedCategory === category ? null : category);
                    }}
                    className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                      expandedCategory === category
                        ? "bg-blue-600 text-white border-blue-600"
                        : selectedTags.some((t) => t.startsWith(category + ":"))
                          ? "bg-blue-50 text-blue-700 border-blue-300"
                          : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    {TAG_CATEGORIES[category]?.label || category}
                    <span className="ml-1 opacity-60">({values.length})</span>
                  </button>

                  {/* Expanded values dropdown */}
                  {expandedCategory === category && (
                    <div
                      data-tag-dropdown
                      className="absolute top-full left-0 mt-1 z-10 bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[200px] max-h-[300px] overflow-y-auto"
                    >
                      {values.map((value) => {
                        const fullTag = `${category}:${value}`;
                        const isSelected = selectedTags.includes(fullTag);
                        return (
                          <button
                            key={fullTag}
                            onClick={() => toggleTag(fullTag)}
                            className={`block w-full text-left px-3 py-1.5 text-sm rounded ${
                              isSelected
                                ? "bg-blue-50 text-blue-700 font-medium"
                                : "text-gray-700 hover:bg-gray-50"
                            }`}
                          >
                            {isSelected && (
                              <svg className="w-3.5 h-3.5 inline mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            )}
                            {value}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

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

      {/* Content List */}
      {!isLoading && content.length > 0 && (
        <div className="bg-white rounded-lg shadow divide-y divide-gray-100">
          {content.map((item) => {
            const platformBg: Record<string, string> = {
              youtube: "bg-red-100",
              linkedin: "bg-blue-100",
              x: "bg-gray-200",
              twitter: "bg-gray-200",
              facebook: "bg-blue-100",
              instagram: "bg-pink-100",
            };
            const platformTextColor: Record<string, string> = {
              youtube: "text-red-300",
              linkedin: "text-blue-300",
              x: "text-gray-400",
              twitter: "text-gray-400",
              facebook: "text-blue-300",
              instagram: "text-pink-300",
            };
            return (
              <div
                key={item.id}
                className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors"
              >
                {/* Thumbnail */}
                <div className="shrink-0 w-[120px] h-[68px] rounded overflow-hidden bg-gray-100">
                  {item.thumbnail_url ? (
                    <a
                      href={item.content_url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block relative w-full h-full"
                    >
                      <img
                        src={item.thumbnail_url}
                        alt={item.title || ""}
                        className="w-full h-full object-cover"
                      />
                      {item.duration_seconds != null && (
                        <span className="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] px-1 py-0.5 rounded leading-none">
                          {Math.floor(item.duration_seconds / 60)}:{(item.duration_seconds % 60).toString().padStart(2, "0")}
                        </span>
                      )}
                      {item.is_short && (
                        <span className="absolute top-1 left-1 bg-red-600 text-white text-[10px] px-1 py-0.5 rounded leading-none font-medium">
                          Short
                        </span>
                      )}
                    </a>
                  ) : (
                    <div className={`w-full h-full flex items-center justify-center ${platformBg[item.platform.toLowerCase()] || "bg-gray-100"}`}>
                      <span className={`opacity-40 ${platformTextColor[item.platform.toLowerCase()] || "text-gray-400"}`}>
                        {getPlatformIcon(item.platform)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Title + meta */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {item.title || item.description?.slice(0, 80) || "Untitled"}
                    </h3>
                    {item.content_source === "branded" && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-emerald-100 text-emerald-700">
                        Branded
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className={`inline-flex items-center gap-1 ${getPlatformColor(item.platform)}`}>
                      {getPlatformIcon(item.platform)}
                      <span className="capitalize">{item.platform}</span>
                    </span>
                    {item.posted_at && (
                      <>
                        <span className="text-gray-300">|</span>
                        <span>{formatDate(item.posted_at)}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Tags (lg+ only) */}
                <div className="hidden lg:flex items-center w-[100px] shrink-0 relative" data-row-tags>
                  {item.tags.length > 0 ? (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpenTagRow(openTagRow === item.id ? null : item.id);
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        {item.tags.length} {item.tags.length === 1 ? "tag" : "tags"}
                      </button>
                      {openTagRow === item.id && (
                        <div
                          data-row-tags
                          className="absolute top-full right-0 mt-1 z-20 bg-white rounded-lg shadow-lg border border-gray-200 p-2 min-w-[220px] max-h-[250px] overflow-y-auto"
                        >
                          <div className="flex flex-wrap gap-1.5">
                            {item.tags.map((tag) => {
                              const { category, value, color } = getTagDisplay(tag);
                              const isSelected = selectedTags.includes(tag);
                              return (
                                <button
                                  key={tag}
                                  onClick={() => toggleTag(tag)}
                                  className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border cursor-pointer hover:opacity-80 ${color} ${
                                    isSelected ? "ring-2 ring-blue-400" : ""
                                  }`}
                                >
                                  <span className="opacity-60 text-[10px]">
                                    {TAG_CATEGORIES[category]?.label || category}:
                                  </span>
                                  {value}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <span className="text-[10px] text-gray-300">No tags</span>
                  )}
                </div>

                {/* Metrics (md+ only) */}
                <div className="hidden md:flex items-center gap-3 w-[180px] shrink-0 text-xs text-gray-500">
                  <span title="Views" className="inline-flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    {formatNumber(item.view_count)}
                  </span>
                  <span title="Likes" className="inline-flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                    </svg>
                    {formatNumber(item.like_count)}
                  </span>
                  <span title="Comments" className="inline-flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    {formatNumber(item.comment_count)}
                  </span>
                </div>

                {/* View link */}
                {item.content_url ? (
                  <a
                    href={item.content_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                    title="Open in platform"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ) : (
                  <div className="shrink-0 w-7" />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && content.length === 0 && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Content Found</h3>
          <p className="text-gray-500">
            {debouncedQuery || platform || source || selectedTags.length > 0
              ? "Try adjusting your search or filters"
              : "Content will appear here once posts are synced"}
          </p>
        </div>
      )}

      {/* Pagination */}
      {!isLoading && content.length > 0 && (
        <div className="flex items-center justify-between bg-white rounded-lg shadow px-4 py-3">
          <div className="text-sm text-gray-500">
            Showing {offset + 1} - {offset + content.length}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              disabled={offset === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => hasMore && setOffset(offset + LIMIT)}
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
