"use client";

import { useAuthStore } from "@/lib/auth-store";

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);

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
