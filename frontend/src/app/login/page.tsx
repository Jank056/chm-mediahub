"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      const detail = error.response?.data?.detail;
      setError(detail || "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setForgotLoading(true);

    try {
      await authApi.recoverPassword(forgotEmail);
      setForgotSuccess(true);
    } catch {
      setError("Failed to send reset email. Please try again.");
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div className="flex flex-col items-center">
          <Image
            src="/CHM_logo.png"
            alt="Community Health Media"
            width={240}
            height={60}
            priority
          />
          <p className="mt-4 text-center text-gray-600">
            Sign in to MediaHub
          </p>
        </div>

        <div className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div>
            {!showForgotPassword ? (
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Forgot password?
              </button>
            ) : (
              <div className="p-4 bg-gray-50 rounded border border-gray-200">
                <h3 className="font-medium text-gray-900 mb-2">
                  Reset Password
                </h3>
                {forgotSuccess ? (
                  <div className="text-sm text-green-700 bg-green-50 p-3 rounded">
                    If an account with this email exists, a password reset link
                    has been sent. Check your email.
                  </div>
                ) : (
                  <form
                    onSubmit={handleForgotPassword}
                    className="space-y-3"
                  >
                    <input
                      type="email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="Enter your email"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={forgotLoading}
                        className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        {forgotLoading ? "Sending..." : "Send Reset Link"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowForgotPassword(false);
                          setForgotEmail("");
                          setForgotSuccess(false);
                        }}
                        className="px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded-md hover:bg-gray-300"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>

        <p className="text-center text-sm text-gray-600">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-medium text-blue-600 hover:text-blue-500">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
