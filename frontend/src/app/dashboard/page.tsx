"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api, analyticsApi, type PostMetrics } from "@/lib/api";

interface LinkedInStats {
  connected: boolean;
  org_urn: string | null;
  org_name: string | null;
  follower_count: number;
  page_views: number;
  last_synced_at: string | null;
}

interface XStats {
  connected: boolean;
  account_handle: string | null;
  follower_count: number;
  tweet_count: number;
  following_count: number;
  listed_count: number;
  last_synced_at: string | null;
}

interface YouTubeStats {
  connected: boolean;
  channel_id: string | null;
  channel_title: string | null;
  custom_url: string | null;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  last_synced_at: string | null;
}

interface FacebookStats {
  connected: boolean;
  page_id: string | null;
  page_name: string | null;
  follower_count: number;
  fan_count: number;
  last_synced_at: string | null;
}

interface InstagramStats {
  connected: boolean;
  ig_account_id: string | null;
  username: string | null;
  name: string | null;
  follower_count: number;
  media_count: number;
  last_synced_at: string | null;
}

const PLATFORM_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  youtube: { bg: "bg-red-100", text: "text-red-700", icon: "text-red-500" },
  linkedin: { bg: "bg-blue-100", text: "text-blue-700", icon: "text-blue-600" },
  x: { bg: "bg-gray-100", text: "text-gray-800", icon: "text-gray-800" },
  facebook: { bg: "bg-blue-100", text: "text-blue-700", icon: "text-blue-600" },
  instagram: { bg: "bg-pink-100", text: "text-pink-700", icon: "text-pink-500" },
};

const PLATFORM_ICONS: Record<string, string> = {
  youtube: "YT",
  linkedin: "LI",
  x: "X",
  facebook: "FB",
  instagram: "IG",
};

const formatNumber = (num: number) => {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
};

const formatRelativeTime = (dateStr: string | null) => {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [linkedinStats, setLinkedinStats] = useState<LinkedInStats | null>(null);
  const [xStats, setXStats] = useState<XStats | null>(null);
  const [youtubeStats, setYoutubeStats] = useState<YouTubeStats | null>(null);
  const [facebookStats, setFacebookStats] = useState<FacebookStats | null>(null);
  const [instagramStats, setInstagramStats] = useState<InstagramStats | null>(null);
  const [recentPosts, setRecentPosts] = useState<PostMetrics[]>([]);
  const [topPosts, setTopPosts] = useState<PostMetrics[]>([]);

  useEffect(() => {
    // Fetch platform stats for admins
    if (user?.role === "admin") {
      Promise.all([
        api.get("/api/linkedin/stats").catch(() => null),
        api.get("/api/x/stats").catch(() => null),
        api.get("/api/youtube/stats").catch(() => null),
        api.get("/api/facebook/stats").catch(() => null),
        api.get("/api/instagram/stats").catch(() => null),
        analyticsApi.getPosts({ source: "official", sort_by: "posted_at", limit: 10 }).catch(() => []),
        analyticsApi.getTopPosts({ source: "official", limit: 5 }).catch(() => []),
      ]).then(([linkedinRes, xRes, youtubeRes, facebookRes, instagramRes, posts, top]) => {
        setLinkedinStats(linkedinRes?.data || null);
        setXStats(xRes?.data || null);
        setYoutubeStats(youtubeRes?.data || null);
        setFacebookStats(facebookRes?.data || null);
        setInstagramStats(instagramRes?.data || null);
        setRecentPosts(posts as PostMetrics[]);
        setTopPosts(top as PostMetrics[]);
      });
    }
  }, [user?.role]);

  // Compute totals across connected platforms
  const totalFollowers =
    (youtubeStats?.connected ? youtubeStats.subscriber_count : 0) +
    (xStats?.connected ? xStats.follower_count : 0) +
    (linkedinStats?.connected ? linkedinStats.follower_count : 0) +
    (facebookStats?.connected ? facebookStats.follower_count : 0) +
    (instagramStats?.connected ? instagramStats.follower_count : 0);

  const connectedCount = [youtubeStats, xStats, linkedinStats, facebookStats, instagramStats]
    .filter((s) => s?.connected).length;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 mb-6 lg:mb-8">
        <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Welcome back</h3>
          <p className="mt-2 text-base lg:text-xl font-semibold text-gray-900 truncate" title={user?.email}>
            {user?.email}
          </p>
        </div>

        <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Your Role</h3>
          <p className="mt-2 text-base lg:text-xl font-semibold text-gray-900 capitalize">
            {user?.role}
          </p>
        </div>

        <div className="bg-white p-4 lg:p-6 rounded-lg shadow sm:col-span-2 lg:col-span-1">
          <h3 className="text-sm font-medium text-gray-500">Total Audience</h3>
          <p className="mt-2 text-base lg:text-xl font-semibold text-gray-900">
            {totalFollowers > 0 ? formatNumber(totalFollowers) : "—"}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {connectedCount > 0 ? `across ${connectedCount} platform${connectedCount > 1 ? "s" : ""}` : "No platforms connected"}
          </p>
        </div>
      </div>

      {/* Official CHM Channel Stats - Admin Only */}
      {user?.role === "admin" && (
        <>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Official CHM Channels</h2>
          <p className="text-sm text-gray-500">Account-level metrics from Community Health Media&apos;s official social profiles.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 mb-6 lg:mb-8">
          {/* LinkedIn Stats Widget */}
          <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <a href="https://www.linkedin.com/company/community-health-media" target="_blank" rel="noopener noreferrer" className="text-lg font-semibold text-gray-900 flex items-center gap-2 hover:text-[#0A66C2] transition-colors">
                <svg className="w-5 h-5 text-[#0A66C2]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                LinkedIn
                <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
              {linkedinStats?.connected && linkedinStats.last_synced_at && (
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(linkedinStats.last_synced_at)}
                </span>
              )}
            </div>
            {linkedinStats?.connected ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Followers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {linkedinStats.follower_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Page Views</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {linkedinStats.page_views.toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Connect LinkedIn in Settings to see stats</p>
            )}
          </div>

          {/* X Stats Widget */}
          <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <a href="https://x.com/hlthinourhands" target="_blank" rel="noopener noreferrer" className="text-lg font-semibold text-gray-900 flex items-center gap-2 hover:text-gray-600 transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.514l-5.106-6.694-5.934 6.694H2.88l7.644-8.74-8.179-10.766h6.504l4.632 6.12L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                X
                <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
              {xStats?.connected && xStats.last_synced_at && (
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(xStats.last_synced_at)}
                </span>
              )}
            </div>
            {xStats?.connected ? (
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Followers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {xStats.follower_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Tweets</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {xStats.tweet_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Following</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {xStats.following_count.toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Pending API configuration</p>
            )}
          </div>

          {/* YouTube Stats Widget */}
          <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <a href="https://www.youtube.com/@CommunityHealthMedia" target="_blank" rel="noopener noreferrer" className="text-lg font-semibold text-gray-900 flex items-center gap-2 hover:text-[#FF0000] transition-colors">
                <svg className="w-5 h-5 text-[#FF0000]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
                YouTube
                <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
              {youtubeStats?.connected && youtubeStats.last_synced_at && (
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(youtubeStats.last_synced_at)}
                </span>
              )}
            </div>
            {youtubeStats?.connected ? (
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Subscribers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {youtubeStats.subscriber_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Views</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatNumber(youtubeStats.view_count)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Videos</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {youtubeStats.video_count.toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Pending API configuration</p>
            )}
          </div>

          {/* Facebook Stats Widget */}
          <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <span className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <svg className="w-5 h-5 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Facebook
              </span>
              {facebookStats?.connected && facebookStats.last_synced_at && (
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(facebookStats.last_synced_at)}
                </span>
              )}
            </div>
            {facebookStats?.connected ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Followers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {facebookStats.follower_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Page Likes</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {facebookStats.fan_count.toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Pending Meta App configuration</p>
            )}
          </div>

          {/* Instagram Stats Widget */}
          <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <span className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <svg className="w-5 h-5 text-[#E4405F]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678a6.162 6.162 0 100 12.324 6.162 6.162 0 100-12.324zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405a1.441 1.441 0 11-2.88 0 1.441 1.441 0 012.88 0z"/>
                </svg>
                Instagram
              </span>
              {instagramStats?.connected && instagramStats.last_synced_at && (
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(instagramStats.last_synced_at)}
                </span>
              )}
            </div>
            {instagramStats?.connected ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Followers</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {instagramStats.follower_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Posts</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {instagramStats.media_count.toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Pending Meta App configuration</p>
            )}
          </div>
        </div>

        {/* Content sections side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 lg:mb-8">
          {/* Recent Official Content */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-gray-900">Recent Content</h3>
              <a href="/dashboard/analytics?source=official" className="text-sm text-blue-600 hover:text-blue-800">
                View all &rarr;
              </a>
            </div>
            <div className="bg-white rounded-lg shadow divide-y divide-gray-100">
              {recentPosts.length > 0 ? (
                recentPosts.map((post) => {
                  const colors = PLATFORM_COLORS[post.platform] || { bg: "bg-gray-100", text: "text-gray-700", icon: "text-gray-500" };
                  return (
                    <div key={post.id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors">
                      <span className={`flex-shrink-0 w-9 h-9 rounded-full ${colors.bg} flex items-center justify-center text-xs font-bold ${colors.text}`}>
                        {PLATFORM_ICONS[post.platform] || post.platform.slice(0, 2).toUpperCase()}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {post.title || (post.platform === "x" ? "Tweet" : "Post")}
                        </p>
                        <p className="text-xs text-gray-500">
                          {post.posted_at ? formatRelativeTime(post.posted_at) : "No date"}
                        </p>
                      </div>
                      <div className="flex-shrink-0 text-right space-y-0.5">
                        <p className="text-sm font-semibold text-gray-900">
                          {formatNumber(post.view_count)} <span className="text-xs font-normal text-gray-400">views</span>
                        </p>
                        <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                          <span>{formatNumber(post.like_count)} likes</span>
                          <span>{formatNumber(post.comment_count)} comments</span>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-8 text-center text-sm text-gray-400">
                  No official channel posts yet. Sync platforms in Settings.
                </div>
              )}
            </div>
          </div>

          {/* Top Performing Official Posts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-gray-900">Top Performing</h3>
              <a href="/dashboard/analytics?source=official" className="text-sm text-blue-600 hover:text-blue-800">
                Full analytics &rarr;
              </a>
            </div>
            <div className="bg-white rounded-lg shadow divide-y divide-gray-100">
              {topPosts.length > 0 ? (
                topPosts.map((post, idx) => {
                  const colors = PLATFORM_COLORS[post.platform] || { bg: "bg-gray-100", text: "text-gray-700", icon: "text-gray-500" };
                  const engRate = post.view_count > 0
                    ? ((post.like_count + post.comment_count + post.share_count) / post.view_count * 100)
                    : 0;
                  return (
                    <div key={post.id} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors">
                      <span className="flex-shrink-0 w-6 text-sm font-bold text-gray-300 text-right">
                        {idx + 1}
                      </span>
                      <span className={`flex-shrink-0 w-9 h-9 rounded-full ${colors.bg} flex items-center justify-center text-xs font-bold ${colors.text}`}>
                        {PLATFORM_ICONS[post.platform] || post.platform.slice(0, 2).toUpperCase()}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {post.title || (post.platform === "x" ? "Tweet" : "Post")}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-gray-500">{formatNumber(post.view_count)} views</span>
                          <span className={`text-xs font-medium ${
                            engRate >= 5 ? "text-green-600" : engRate >= 2 ? "text-yellow-600" : "text-gray-400"
                          }`}>
                            {engRate.toFixed(1)}% eng.
                          </span>
                        </div>
                      </div>
                      <div className="flex-shrink-0 text-right">
                        <p className="text-sm font-semibold text-gray-900">
                          {formatNumber(post.like_count)}
                        </p>
                        <p className="text-xs text-gray-400">likes</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="px-4 py-8 text-center text-sm text-gray-400">
                  Top posts will appear after sync.
                </div>
              )}
            </div>
          </div>
        </div>
        </>
      )}

      <div className="bg-white p-4 lg:p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <a
            href="/dashboard/analytics"
            className="block p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow transition-all"
          >
            <h3 className="font-medium text-gray-900">View Analytics</h3>
            <p className="text-sm text-gray-500 mt-1">
              Check platform metrics and performance
            </p>
          </a>

          <a
            href="/dashboard/chatbot"
            className="block p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow transition-all"
          >
            <h3 className="font-medium text-gray-900">Search Content</h3>
            <p className="text-sm text-gray-500 mt-1">
              Ask questions about CHM podcasts
            </p>
          </a>

          {(user?.role === "admin" || user?.role === "editor") && (
            <a
              href="/dashboard/reports"
              className="block p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:shadow transition-all"
            >
              <h3 className="font-medium text-gray-900">Generate Reports</h3>
              <p className="text-sm text-gray-500 mt-1">
                Create webinar recap presentations
              </p>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
