"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useState, useEffect } from "react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", roles: ["superadmin", "admin", "editor", "viewer"], requiresClientAccess: false },
  { name: "Clients", href: "/dashboard/clients", roles: ["superadmin", "admin", "editor", "viewer"], requiresClientAccess: true },
  { name: "Analytics", href: "/dashboard/analytics", roles: ["superadmin", "admin", "editor", "viewer"], requiresClientAccess: true },
  { name: "Clips", href: "/dashboard/clips", roles: ["superadmin", "admin", "editor", "viewer"], requiresClientAccess: true },
  { name: "Chatbot", href: "/dashboard/chatbot", roles: ["superadmin", "admin", "editor", "viewer"], requiresClientAccess: false },
  { name: "Reports", href: "/dashboard/reports", roles: ["superadmin", "admin", "editor"], requiresClientAccess: false },
  { name: "Users", href: "/dashboard/users", roles: ["superadmin", "admin"], requiresClientAccess: false },
  { name: "Settings", href: "/dashboard/settings", roles: ["superadmin", "admin"], requiresClientAccess: false },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  // Close mobile menu on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMobileOpen(false);
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const filteredNav = navigation.filter(
    (item) =>
      user &&
      item.roles.includes(user.role) &&
      (!item.requiresClientAccess || user.has_client_access)
  );

  const sidebarContent = (
    <>
      {/* Logo Header */}
      <div className={`flex items-center ${isCollapsed ? "justify-center" : "justify-between"} h-16 px-4 bg-gray-800`}>
        <div className={`flex items-center ${isCollapsed ? "" : "gap-3"}`}>
          <Image
            src="/CHM_logo_textless.png"
            alt="CHM Logo"
            width={32}
            height={32}
            className="rounded"
          />
          {!isCollapsed && (
            <span className="text-white text-lg font-bold">MediaHub</span>
          )}
        </div>
        {/* Desktop collapse button */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="hidden lg:flex items-center justify-center w-6 h-6 text-gray-400 hover:text-white transition-colors"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <svg
            className={`w-4 h-4 transition-transform ${isCollapsed ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {filteredNav.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center ${isCollapsed ? "justify-center" : ""} px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                isActive
                  ? "bg-gray-800 text-white"
                  : "text-gray-300 hover:bg-gray-700 hover:text-white"
              }`}
              title={isCollapsed ? item.name : undefined}
            >
              {isCollapsed ? (
                <span className="text-xs">{item.name.charAt(0)}</span>
              ) : (
                item.name
              )}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div className={`p-4 border-t border-gray-700 ${isCollapsed ? "text-center" : ""}`}>
        {!isCollapsed && (
          <Link href="/dashboard/account" className="block mb-3 rounded-md px-2 py-1.5 -mx-2 hover:bg-gray-800 transition-colors">
            <div className="text-sm text-gray-300 truncate">{user?.name || user?.email}</div>
            {user?.name && <div className="text-xs text-gray-500 truncate">{user?.email}</div>}
            <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
          </Link>
        )}
        {isCollapsed && (
          <Link
            href="/dashboard/account"
            className="flex items-center justify-center w-10 h-10 mx-auto mb-3 rounded-md text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
            title="Account"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </Link>
        )}
        <button
          onClick={handleLogout}
          className={`${isCollapsed ? "w-10 h-10 p-0 mx-auto" : "w-full px-4 py-2"} flex items-center justify-center text-sm font-medium text-gray-300 bg-gray-800 rounded-md hover:bg-gray-700 hover:text-white transition-colors`}
          title={isCollapsed ? "Sign out" : undefined}
        >
          {isCollapsed ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          ) : (
            "Sign out"
          )}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-gray-900 text-white rounded-md shadow-lg"
        aria-label="Open menu"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile overlay - only render when open */}
      <div
        className={`lg:hidden fixed inset-0 z-40 bg-black transition-opacity duration-300 ${
          isMobileOpen ? "opacity-50 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setIsMobileOpen(false)}
        aria-hidden={!isMobileOpen}
      />

      {/* Mobile sidebar */}
      <div
        className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 transform transition-transform duration-300 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Close button */}
        <button
          onClick={() => setIsMobileOpen(false)}
          className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white"
          aria-label="Close menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <div className="flex flex-col h-full">
          {/* Logo Header (mobile always expanded) */}
          <div className="flex items-center gap-3 h-16 px-4 bg-gray-800">
            <Image
              src="/CHM_logo_textless.png"
              alt="CHM Logo"
              width={32}
              height={32}
              className="rounded"
            />
            <span className="text-white text-lg font-bold">MediaHub</span>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
            {filteredNav.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? "bg-gray-800 text-white"
                      : "text-gray-300 hover:bg-gray-700 hover:text-white"
                  }`}
                >
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-gray-700">
            <Link href="/dashboard/account" className="block mb-3 rounded-md px-2 py-1.5 -mx-2 hover:bg-gray-800 transition-colors">
              <div className="text-sm text-gray-300 truncate">{user?.name || user?.email}</div>
              {user?.name && <div className="text-xs text-gray-500 truncate">{user?.email}</div>}
              <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
            </Link>
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2 text-sm font-medium text-gray-300 bg-gray-800 rounded-md hover:bg-gray-700 hover:text-white transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div
        className={`hidden lg:flex flex-col bg-gray-900 min-h-screen transition-all duration-300 ${
          isCollapsed ? "w-16" : "w-64"
        }`}
      >
        {sidebarContent}
      </div>
    </>
  );
}
