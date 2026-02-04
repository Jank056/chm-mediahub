"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface PlatformConnection {
  id: string;
  platform: string;
  external_account_id: string;
  external_account_name: string | null;
  connected_by_email: string | null;
  expires_at: string | null;
  is_expired: boolean;
  created_at: string;
}

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

export default function SettingsPage() {
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [linkedInStats, setLinkedInStats] = useState<LinkedInStats | null>(null);
  const [xStats, setXStats] = useState<XStats | null>(null);
  const [youtubeStats, setYoutubeStats] = useState<YouTubeStats | null>(null);
  const [facebookStats, setFacebookStats] = useState<FacebookStats | null>(null);
  const [instagramStats, setInstagramStats] = useState<InstagramStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncingLinkedIn, setIsSyncingLinkedIn] = useState(false);
  const [isSyncingX, setIsSyncingX] = useState(false);
  const [isSyncingYouTube, setIsSyncingYouTube] = useState(false);
  const [isSyncingFacebook, setIsSyncingFacebook] = useState(false);
  const [isSyncingInstagram, setIsSyncingInstagram] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [connectionsRes, linkedInStatsRes, xStatsRes, youtubeStatsRes, facebookStatsRes, instagramStatsRes] = await Promise.all([
        api.get("/api/oauth/connections"),
        api.get("/api/linkedin/stats").catch(() => null),
        api.get("/api/x/stats").catch(() => null),
        api.get("/api/youtube/stats").catch(() => null),
        api.get("/api/facebook/stats").catch(() => null),
        api.get("/api/instagram/stats").catch(() => null),
      ]);
      setConnections(connectionsRes.data.connections || []);
      setLinkedInStats(linkedInStatsRes?.data || null);
      setXStats(xStatsRes?.data || null);
      setYoutubeStats(youtubeStatsRes?.data || null);
      setFacebookStats(facebookStatsRes?.data || null);
      setInstagramStats(instagramStatsRes?.data || null);
    } catch (err: unknown) {
      console.error("Failed to fetch settings data:", err);
      setError("Failed to load settings. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Listen for OAuth success messages from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "oauth-success") {
        fetchData();
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const handleConnectLinkedIn = async () => {
    setIsConnecting(true);
    setError(null);
    try {
      const response = await api.post("/api/oauth/linkedin/start");
      const { auth_url } = response.data;

      // Open OAuth popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      window.open(
        auth_url,
        "LinkedIn OAuth",
        `width=${width},height=${height},left=${left},top=${top}`
      );
    } catch (err: unknown) {
      console.error("Failed to start LinkedIn OAuth:", err);
      setError("Failed to start LinkedIn connection. Please try again.");
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async (connectionId: string, platform: string) => {
    if (!confirm(`Are you sure you want to disconnect ${platform}?`)) {
      return;
    }

    try {
      setError(null);
      await api.delete(`/api/oauth/connections/${connectionId}`);
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to disconnect:", err);
      setError("Failed to disconnect. Please try again.");
    }
  };

  const handleSyncLinkedInStats = async () => {
    setIsSyncingLinkedIn(true);
    setError(null);
    try {
      await api.post("/api/linkedin/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync stats:", err);
      setError("Failed to sync LinkedIn stats. Please try again.");
    } finally {
      setIsSyncingLinkedIn(false);
    }
  };

  const handleSyncXStats = async () => {
    setIsSyncingX(true);
    setError(null);
    try {
      await api.post("/api/x/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync X stats:", err);
      setError("Failed to sync X stats. Please try again.");
    } finally {
      setIsSyncingX(false);
    }
  };

  const handleSyncYouTubeStats = async () => {
    setIsSyncingYouTube(true);
    setError(null);
    try {
      await api.post("/api/youtube/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync YouTube stats:", err);
      setError("Failed to sync YouTube stats. Please try again.");
    } finally {
      setIsSyncingYouTube(false);
    }
  };

  const handleSyncFacebookStats = async () => {
    setIsSyncingFacebook(true);
    setError(null);
    try {
      await api.post("/api/facebook/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync Facebook stats:", err);
      setError("Failed to sync Facebook stats. Please try again.");
    } finally {
      setIsSyncingFacebook(false);
    }
  };

  const handleSyncInstagramStats = async () => {
    setIsSyncingInstagram(true);
    setError(null);
    try {
      await api.post("/api/instagram/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync Instagram stats:", err);
      setError("Failed to sync Instagram stats. Please try again.");
    } finally {
      setIsSyncingInstagram(false);
    }
  };

  const linkedInConnection = connections.find((c) => c.platform === "linkedin");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Platform Connections Section */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Official CHM Channels
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            API connections to Community Health Media&apos;s official social accounts.
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* LinkedIn Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#0077B5] rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.32 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.79M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">
                    <a href="https://www.linkedin.com/company/community-health-media" target="_blank" rel="noopener noreferrer" className="hover:text-[#0077B5] transition-colors inline-flex items-center gap-1">
                      LinkedIn
                      <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                    </a>
                  </h3>
                  {linkedInConnection ? (
                    <p className="text-sm text-gray-500">
                      Connected as{" "}
                      {linkedInConnection.external_account_name ||
                        linkedInConnection.external_account_id}
                      {linkedInConnection.is_expired && (
                        <span className="text-red-500 ml-2">
                          (Token expired - reconnect)
                        </span>
                      )}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">Not connected</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {linkedInConnection ? (
                  <>
                    <span className="px-3 py-1.5 text-sm text-green-600 bg-green-50 rounded-md">
                      {linkedInConnection.is_expired ? "Expired" : "Active"}
                    </span>
                    <button
                      onClick={handleConnectLinkedIn}
                      disabled={isConnecting}
                      className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
                    >
                      Reconnect
                    </button>
                    <button
                      onClick={() => handleDisconnect(linkedInConnection.id, "LinkedIn")}
                      className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700"
                    >
                      Disconnect
                    </button>
                  </>
                ) : (
                  <>
                    <span className="px-3 py-1.5 text-sm text-gray-500 bg-gray-50 rounded-md">
                      Not connected
                    </span>
                    <button
                      onClick={handleConnectLinkedIn}
                      disabled={isConnecting}
                      className="px-4 py-2 bg-[#0077B5] text-white text-sm font-medium rounded-md hover:bg-[#006097] disabled:opacity-50"
                    >
                      {isConnecting ? "Connecting..." : "Connect"}
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Stats section - only show if connected */}
            {linkedInStats?.connected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700">
                    Organization Stats
                  </h4>
                  <button
                    onClick={handleSyncLinkedInStats}
                    disabled={isSyncingLinkedIn}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncingLinkedIn ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {linkedInStats.follower_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Followers</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {linkedInStats.page_views.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Page Views</div>
                  </div>
                </div>
                {linkedInStats.last_synced_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last synced:{" "}
                    {new Date(linkedInStats.last_synced_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            {linkedInConnection && !linkedInConnection.is_expired && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-400">
                  Connected on{" "}
                  {new Date(linkedInConnection.created_at).toLocaleDateString()}
                  {linkedInConnection.expires_at && (
                    <>
                      {" "}
                      · Expires{" "}
                      {new Date(
                        linkedInConnection.expires_at
                      ).toLocaleDateString()}
                    </>
                  )}
                </p>
              </div>
            )}
          </div>

          {/* X/Twitter Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.514l-5.106-6.694-5.934 6.694H2.88l7.644-8.74-8.179-10.766h6.504l4.632 6.12L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">
                    <a href="https://x.com/hlthinourhands" target="_blank" rel="noopener noreferrer" className="hover:text-gray-600 transition-colors inline-flex items-center gap-1">
                      X (Twitter)
                      <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                    </a>
                  </h3>
                  {xStats?.connected ? (
                    <p className="text-sm text-gray-500">
                      Connected as @{xStats.account_handle}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">
                      Pending configuration
                    </p>
                  )}
                </div>
              </div>

              <div>
                {xStats?.connected ? (
                  <span className="px-3 py-1.5 text-sm text-green-600 bg-green-50 rounded-md">
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1.5 text-sm text-gray-500 bg-gray-50 rounded-md">
                    Pending
                  </span>
                )}
              </div>
            </div>

            {/* Stats section - only show if connected */}
            {xStats?.connected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700">
                    Account Stats
                  </h4>
                  <button
                    onClick={handleSyncXStats}
                    disabled={isSyncingX}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncingX ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {xStats.follower_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Followers</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {xStats.tweet_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Tweets</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {xStats.following_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Following</div>
                  </div>
                </div>
                {xStats.last_synced_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last synced:{" "}
                    {new Date(xStats.last_synced_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* YouTube Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#FF0000] rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">
                    <a href="https://www.youtube.com/@CommunityHealthMedia" target="_blank" rel="noopener noreferrer" className="hover:text-[#FF0000] transition-colors inline-flex items-center gap-1">
                      YouTube
                      <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                    </a>
                  </h3>
                  {youtubeStats?.connected ? (
                    <p className="text-sm text-gray-500">
                      Connected as {youtubeStats.channel_title || youtubeStats.custom_url}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">
                      Pending configuration
                    </p>
                  )}
                </div>
              </div>

              <div>
                {youtubeStats?.connected ? (
                  <span className="px-3 py-1.5 text-sm text-green-600 bg-green-50 rounded-md">
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1.5 text-sm text-gray-500 bg-gray-50 rounded-md">
                    Pending
                  </span>
                )}
              </div>
            </div>

            {/* Stats section - only show if connected */}
            {youtubeStats?.connected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700">
                    Channel Stats
                  </h4>
                  <button
                    onClick={handleSyncYouTubeStats}
                    disabled={isSyncingYouTube}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncingYouTube ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {youtubeStats.subscriber_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Subscribers</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {youtubeStats.view_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Total Views</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {youtubeStats.video_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Videos</div>
                  </div>
                </div>
                {youtubeStats.last_synced_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last synced:{" "}
                    {new Date(youtubeStats.last_synced_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Facebook Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#1877F2] rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Facebook</h3>
                  {facebookStats?.connected ? (
                    <p className="text-sm text-gray-500">
                      Connected as {facebookStats.page_name || facebookStats.page_id}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">
                      Pending configuration
                    </p>
                  )}
                </div>
              </div>

              <div>
                {facebookStats?.connected ? (
                  <span className="px-3 py-1.5 text-sm text-green-600 bg-green-50 rounded-md">
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1.5 text-sm text-gray-500 bg-gray-50 rounded-md">
                    Pending
                  </span>
                )}
              </div>
            </div>

            {/* Stats section - only show if connected */}
            {facebookStats?.connected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700">
                    Page Stats
                  </h4>
                  <button
                    onClick={handleSyncFacebookStats}
                    disabled={isSyncingFacebook}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncingFacebook ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {facebookStats.follower_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Followers</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {facebookStats.fan_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Page Likes</div>
                  </div>
                </div>
                {facebookStats.last_synced_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last synced:{" "}
                    {new Date(facebookStats.last_synced_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Instagram Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-tr from-[#F58529] via-[#DD2A7B] to-[#8134AF] rounded-lg flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Instagram</h3>
                  {instagramStats?.connected ? (
                    <p className="text-sm text-gray-500">
                      Connected as @{instagramStats.username || instagramStats.name}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">
                      Pending configuration
                    </p>
                  )}
                </div>
              </div>

              <div>
                {instagramStats?.connected ? (
                  <span className="px-3 py-1.5 text-sm text-green-600 bg-green-50 rounded-md">
                    Active
                  </span>
                ) : (
                  <span className="px-3 py-1.5 text-sm text-gray-500 bg-gray-50 rounded-md">
                    Pending
                  </span>
                )}
              </div>
            </div>

            {/* Stats section - only show if connected */}
            {instagramStats?.connected && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-gray-700">
                    Account Stats
                  </h4>
                  <button
                    onClick={handleSyncInstagramStats}
                    disabled={isSyncingInstagram}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncingInstagram ? "Syncing..." : "Sync Now"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {instagramStats.follower_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Followers</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-gray-900">
                      {instagramStats.media_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-gray-500">Posts</div>
                  </div>
                </div>
                {instagramStats.last_synced_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    Last synced:{" "}
                    {new Date(instagramStats.last_synced_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-800 mb-1">
              About Platform Connections
            </h4>
            <p className="text-sm text-blue-700">
              Connecting platforms allows MediaHub to fetch analytics directly
              from platform APIs. This provides accurate stats for CHM&apos;s
              official channels. LinkedIn uses OAuth; X uses a bearer token;
              YouTube uses an API key; Facebook and Instagram use a Page Access
              Token — all configured on the server.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
