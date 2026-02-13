"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

function ResetPasswordContent() {
  const router = useRouter();
  const loginWithTokens = useAuthStore((state) => state.loginWithTokens);

  const [status, setStatus] = useState<
    "verifying" | "form" | "success" | "error"
  >("verifying");
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const hashParams = new URLSearchParams(
      window.location.hash.substring(1)
    );
    const recoveryToken = hashParams.get("recovery_token");

    if (!recoveryToken) {
      setError("Invalid password reset link. No token provided.");
      setStatus("error");
      return;
    }

    setToken(recoveryToken);
    setStatus("form");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const tokens = await authApi.resetPassword(token, password);
      await loginWithTokens(tokens.access_token, tokens.refresh_token);
      setStatus("success");
      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { detail?: string } };
      };
      setError(
        axiosError.response?.data?.detail || "Failed to reset password."
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (status === "verifying") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <Image
            src="/CHM_logo.png"
            alt="Community Health Media"
            width={240}
            height={60}
            priority
            className="mx-auto mb-6"
          />
          <div className="flex justify-center mb-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            Verifying Reset Link
          </h2>
          <p className="text-gray-600">Please wait...</p>
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-8 h-8 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Password Reset Successfully!
          </h2>
          <p className="text-gray-600">
            Redirecting you to the dashboard...
          </p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-center mb-8">
              <Image
                src="/CHM_logo.png"
                alt="Community Health Media"
                width={240}
                height={60}
                priority
                className="mx-auto"
              />
              <h1 className="text-2xl font-bold text-gray-900 mt-4">
                Password Reset Failed
              </h1>
            </div>

            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>

            <div className="text-center">
              <Link
                href="/login"
                className="inline-block px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700"
              >
                Return to Login
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <Image
              src="/CHM_logo.png"
              alt="Community Health Media"
              width={240}
              height={60}
              priority
              className="mx-auto"
            />
            <h1 className="text-2xl font-bold text-gray-900 mt-4">
              Reset Your Password
            </h1>
            <p className="text-gray-600 mt-2">
              Enter a new password for your account
            </p>
          </div>

          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                New Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="At least 8 characters"
                minLength={8}
              />
              <p className="mt-1 text-xs text-gray-500">
                Must be at least 8 characters
              </p>
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Confirm New Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Repeat your password"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Resetting Password..." : "Reset Password"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
