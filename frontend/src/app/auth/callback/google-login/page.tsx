"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export default function GoogleLoginCallbackPage() {
  const router = useRouter();
  const loginWithTokens = useAuthStore((state) => state.loginWithTokens);
  const [error, setError] = useState("");

  useEffect(() => {
    async function handleCallback() {
      // GoTrue returns tokens in the URL fragment (#access_token=...)
      const hash = window.location.hash.substring(1);
      const hashParams = new URLSearchParams(hash);

      const accessToken = hashParams.get("access_token");

      if (!accessToken) {
        setError("Missing authentication data. Please try again.");
        return;
      }

      try {
        const tokens = await authApi.loginGoogle(accessToken);
        await loginWithTokens(tokens.access_token, tokens.refresh_token);
        router.push("/dashboard");
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } };
        setError(
          error.response?.data?.detail ||
            "Failed to sign in with Google. Please try again."
        );
      }
    }

    handleCallback();
  }, [router, loginWithTokens]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-8 bg-white rounded-lg shadow">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
          <a
            href="/login"
            className="block w-full text-center py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
        <p className="mt-4 text-gray-600">Signing in with Google...</p>
      </div>
    </div>
  );
}
