"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

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

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [linkedinStats, setLinkedinStats] = useState<LinkedInStats | null>(null);
  const [xStats, setXStats] = useState<XStats | null>(null);
  const [youtubeStats, setYoutubeStats] = useState<YouTubeStats | null>(null);

  useEffect(() => {
    // Fetch platform stats for admins
    if (user?.role === "admin") {
      Promise.all([
        api.get("/api/linkedin/stats").catch(() => null),
        api.get("/api/x/stats").catch(() => null),
        api.get("/api/youtube/stats").catch(() => null),
      ]).then(([linkedinRes, xRes, youtubeRes]) => {
        setLinkedinStats(linkedinRes?.data || null);
        setXStats(xRes?.data || null);
        setYoutubeStats(youtubeRes?.data || null);
      });
    }
  }, [user?.role]);

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
          <h3 className="text-sm font-medium text-gray-500">Account Status</h3>
          <p className="mt-2 text-base lg:text-xl font-semibold text-green-600">Active</p>
        </div>
      </div>

      {/* Official CHM Channel Stats - Admin Only */}
      {user?.role === "admin" && (
        <>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Official CHM Channels</h2>
          <p className="text-sm text-gray-500">Account-level metrics from Community Health Media&apos;s official social profiles.</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6 mb-6 lg:mb-8">
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
                  Updated {new Date(linkedinStats.last_synced_at).toLocaleDateString()}
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
                  Updated {new Date(xStats.last_synced_at).toLocaleDateString()}
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
                  Updated {new Date(youtubeStats.last_synced_at).toLocaleDateString()}
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
                    {youtubeStats.view_count.toLocaleString()}
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
