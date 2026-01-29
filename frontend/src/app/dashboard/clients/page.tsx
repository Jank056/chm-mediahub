"use client";

import { useEffect, useState } from "react";
import { clientsApi, type ClientSummary } from "@/lib/api";
import { ClientCard } from "@/components/clients";

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadClients() {
      try {
        const data = await clientsApi.list();
        setClients(data);
      } catch (err) {
        setError("Failed to load clients");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadClients();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
        <p className="text-gray-500 mt-1">
          Manage pharmaceutical company accounts and their content programs
        </p>
      </div>

      {/* Clients Grid */}
      {clients.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No clients found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {clients.map((client) => (
            <ClientCard key={client.id} client={client} />
          ))}
        </div>
      )}
    </div>
  );
}
