"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

function ConfirmEmailContent() {
  const router = useRouter();
  const loginWithTokens = useAuthStore((state) => state.loginWithTokens);

  const [status, setStatus] = useState<"verifying" | "success" | "error">(
    "verifying"
  );
  const [error, setError] = useState("");

  useEffect(() => {
    const hashParams = new URLSearchParams(
      window.location.hash.substring(1)
    );
    const token = hashParams.get("confirmation_token");

    if (!token) {
      setError("Invalid confirmation link. No token provided.");
      setStatus("error");
      return;
    }

    authApi
      .verifyEmail(token)
      .then(async (tokens) => {
        await loginWithTokens(tokens.access_token, tokens.refresh_token);
        setStatus("success");
        setTimeout(() => router.push("/dashboard"), 2000);
      })
      .catch((err: unknown) => {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
        };
        setError(
          axiosError.response?.data?.detail || "Email confirmation failed."
        );
        setStatus("error");
      });
  }, [loginWithTokens, router]);

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
            Verifying Your Email
          </h2>
          <p className="text-gray-600">
            Please wait while we confirm your email address...
          </p>
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
            Email Confirmed!
          </h2>
          <p className="text-gray-600">
            Redirecting you to the dashboard...
          </p>
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
              Confirmation Failed
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

export default function ConfirmEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      }
    >
      <ConfirmEmailContent />
    </Suspense>
  );
}
