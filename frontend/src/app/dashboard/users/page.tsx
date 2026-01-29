"use client";

import { useState, useEffect } from "react";
import { usersApi, authApi } from "@/lib/api";
import { ProtectedRoute } from "@/components/protected-route";

interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface Invitation {
  id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  is_accepted: boolean;
}

const ROLE_DESCRIPTIONS: Record<string, { title: string; description: string; color: string }> = {
  admin: {
    title: "Admin",
    description: "Full access including user management, invitations, and all features.",
    color: "bg-purple-100 text-purple-800",
  },
  editor: {
    title: "Editor",
    description: "Can generate reports and use the AI chatbot. Cannot manage users.",
    color: "bg-green-100 text-green-800",
  },
  viewer: {
    title: "Viewer",
    description: "Read-only access. Can view analytics and content but cannot make changes.",
    color: "bg-gray-100 text-gray-800",
  },
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [error, setError] = useState("");
  const [createdInviteLink, setCreatedInviteLink] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [usersData, invitationsData] = await Promise.all([
        usersApi.list(),
        authApi.listInvitations(),
      ]);
      setUsers(usersData);
      setInvitations(invitationsData);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getInviteLink = (token: string) => {
    const baseUrl = typeof window !== "undefined" ? window.location.origin : "";
    return `${baseUrl}/accept-invite?token=${token}`;
  };

  const copyToClipboard = async (text: string, id: string) => {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for non-HTTPS contexts
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      }
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
      // Show the text in an alert as last resort
      alert(`Copy this link:\n${text}`);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const response = await authApi.invite(inviteEmail, inviteRole);
      const inviteLink = getInviteLink(response.token);
      setCreatedInviteLink(inviteLink);
      fetchData();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || "Failed to create invitation");
    }
  };

  const handleCloseInviteModal = () => {
    setShowInviteModal(false);
    setCreatedInviteLink(null);
    setInviteEmail("");
    setInviteRole("viewer");
    setError("");
  };

  const handleToggleActive = async (user: User) => {
    try {
      await usersApi.update(user.id, { is_active: !user.is_active });
      fetchData();
    } catch (err) {
      console.error("Failed to update user:", err);
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!confirm(`Are you sure you want to delete ${user.email}? This action cannot be undone.`)) {
      return;
    }
    try {
      await usersApi.delete(user.id);
      fetchData();
    } catch (err) {
      console.error("Failed to delete user:", err);
    }
  };

  const handleRevokeInvitation = async (id: string) => {
    try {
      await authApi.revokeInvitation(id);
      fetchData();
    } catch (err) {
      console.error("Failed to revoke invitation:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <div>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <button
            onClick={() => setShowInviteModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Invite User
          </button>
        </div>

        {/* Role Legend */}
        <div className="bg-white rounded-lg shadow mb-6 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Role Permissions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {Object.entries(ROLE_DESCRIPTIONS).map(([key, role]) => (
              <div key={key} className="flex items-start gap-2">
                <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${role.color} whitespace-nowrap`}>
                  {role.title}
                </span>
                <p className="text-xs text-gray-500">{role.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Users</h2>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.email}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${ROLE_DESCRIPTIONS[user.role]?.color || "bg-gray-100 text-gray-800"}`}
                      title={ROLE_DESCRIPTIONS[user.role]?.description}
                    >
                      {ROLE_DESCRIPTIONS[user.role]?.title || user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.is_active
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-3">
                    <button
                      onClick={() => handleToggleActive(user)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      {user.is_active ? "Deactivate" : "Activate"}
                    </button>
                    <button
                      onClick={() => handleDeleteUser(user)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pending Invitations */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Pending Invitations
            </h2>
          </div>
          {invitations.filter((i) => !i.is_accepted).length === 0 ? (
            <div className="px-6 py-4 text-sm text-gray-500">
              No pending invitations
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Expires
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {invitations
                  .filter((i) => !i.is_accepted)
                  .map((invitation) => (
                    <tr key={invitation.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {invitation.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                        {invitation.role}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(invitation.expires_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-3">
                        <button
                          onClick={() => copyToClipboard(getInviteLink(invitation.token), invitation.id)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          {copiedId === invitation.id ? "Copied!" : "Copy Link"}
                        </button>
                        <button
                          onClick={() => handleRevokeInvitation(invitation.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Invite Modal */}
        {showInviteModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              {createdInviteLink ? (
                // Success state - show invite link
                <>
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Invitation Created
                    </h3>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    Invitation for: <strong>{inviteEmail}</strong>
                  </p>
                  <p className="text-sm text-gray-600 mb-4">
                    Share this link with them. They will use it to set up their password and access the portal.
                  </p>
                  <div className="bg-gray-50 border border-gray-200 rounded-md p-3 mb-4">
                    <p className="text-xs text-gray-500 mb-1">Invitation Link (expires in 7 days)</p>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={createdInviteLink}
                        className="flex-1 text-sm text-gray-700 bg-transparent border-none p-0 focus:ring-0 overflow-hidden"
                      />
                      <button
                        onClick={() => copyToClipboard(createdInviteLink, "new-invite")}
                        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 whitespace-nowrap"
                      >
                        {copiedId === "new-invite" ? "Copied!" : "Copy"}
                      </button>
                    </div>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 rounded-md p-3 mb-4">
                    <p className="text-sm text-amber-800">
                      <strong>Note:</strong> No email is sent automatically. Please share this link directly with the user via email, Slack, etc.
                    </p>
                  </div>
                  <div className="flex justify-end">
                    <button
                      onClick={handleCloseInviteModal}
                      className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                    >
                      Done
                    </button>
                  </div>
                </>
              ) : (
                // Form state - invite user
                <>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Invite User
                  </h3>
                  <form onSubmit={handleInvite}>
                    {error && (
                      <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                        {error}
                      </div>
                    )}
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email
                      </label>
                      <input
                        type="email"
                        required
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        placeholder="user@example.com"
                      />
                    </div>
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Role
                      </label>
                      <select
                        value={inviteRole}
                        onChange={(e) => setInviteRole(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="editor">Editor</option>
                      </select>
                    </div>
                    {/* Role description */}
                    <div className="mb-6 bg-gray-50 border border-gray-200 rounded-md p-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">
                        {ROLE_DESCRIPTIONS[inviteRole]?.title} Permissions
                      </p>
                      <p className="text-sm text-gray-600">
                        {ROLE_DESCRIPTIONS[inviteRole]?.description}
                      </p>
                    </div>
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={handleCloseInviteModal}
                        className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                      >
                        Create Invitation
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
