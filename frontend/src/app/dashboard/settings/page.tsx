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

export default function SettingsPage() {
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [linkedInStats, setLinkedInStats] = useState<LinkedInStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [connectionsRes, statsRes] = await Promise.all([
        api.get("/api/oauth/connections"),
        api.get("/api/linkedin/stats"),
      ]);
      setConnections(connectionsRes.data.connections || []);
      setLinkedInStats(statsRes.data);
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

  const handleDisconnect = async (connectionId: string) => {
    if (!confirm("Are you sure you want to disconnect LinkedIn?")) {
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

  const handleSyncStats = async () => {
    setIsSyncing(true);
    setError(null);
    try {
      await api.post("/api/linkedin/stats/sync");
      fetchData();
    } catch (err: unknown) {
      console.error("Failed to sync stats:", err);
      setError("Failed to sync LinkedIn stats. Please try again.");
    } finally {
      setIsSyncing(false);
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
            Platform Connections
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Connect platforms to fetch analytics directly from their APIs.
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* LinkedIn Connection */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* LinkedIn Icon */}
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
                  <h3 className="font-medium text-gray-900">LinkedIn</h3>
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

              <div>
                {linkedInConnection ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleConnectLinkedIn}
                      disabled={isConnecting}
                      className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
                    >
                      Reconnect
                    </button>
                    <button
                      onClick={() => handleDisconnect(linkedInConnection.id)}
                      className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700"
                    >
                      Disconnect
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={handleConnectLinkedIn}
                    disabled={isConnecting}
                    className="px-4 py-2 bg-[#0077B5] text-white text-sm font-medium rounded-md hover:bg-[#006097] disabled:opacity-50"
                  >
                    {isConnecting ? "Connecting..." : "Connect LinkedIn"}
                  </button>
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
                    onClick={handleSyncStats}
                    disabled={isSyncing}
                    className="px-3 py-1 text-xs text-blue-600 hover:text-blue-700 disabled:opacity-50"
                  >
                    {isSyncing ? "Syncing..." : "Sync Now"}
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

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-medium text-blue-800 mb-1">
              About Platform Connections
            </h4>
            <p className="text-sm text-blue-700">
              Connecting platforms allows MediaHub to fetch analytics directly
              from platform APIs. This provides accurate stats for CHM&apos;s
              official channels. Currently supports LinkedIn organization stats.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
