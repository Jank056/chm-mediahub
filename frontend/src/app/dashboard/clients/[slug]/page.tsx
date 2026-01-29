"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { clientsApi, type ClientDetail, type ClientAnalytics } from "@/lib/api";
import { Avatar, Badge, ProjectCard, StatsGrid } from "@/components/clients";

export default function ClientDetailPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [client, setClient] = useState<ClientDetail | null>(null);
  const [analytics, setAnalytics] = useState<ClientAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadClient() {
      try {
        const [clientData, analyticsData] = await Promise.all([
          clientsApi.get(slug),
          clientsApi.getAnalytics(slug).catch(() => null),
        ]);
        setClient(clientData);
        setAnalytics(analyticsData);
      } catch (err) {
        setError("Failed to load client");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadClient();
  }, [slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error || "Client not found"}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        <Link href="/dashboard/clients" className="hover:text-blue-600">
          Clients
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{client.name}</span>
      </nav>

      {/* Client Header */}
      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-start gap-6">
          <Avatar name={client.name} imageUrl={client.logo_url} size="xl" />
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{client.name}</h1>
              <Badge variant={client.is_active ? "success" : "default"} size="md">
                {client.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <p className="text-gray-500 mb-4">/{client.slug}</p>
            {client.primary_contact_name && (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Contact:</span> {client.primary_contact_name}
                {client.primary_contact_email && (
                  <span className="ml-2 text-blue-600">{client.primary_contact_email}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Analytics Overview */}
      {analytics && (
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Analytics Overview</h2>
          <StatsGrid analytics={analytics} />
        </section>
      )}

      {/* Projects Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Projects ({client.projects.length})
          </h2>
        </div>
        {client.projects.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">No projects yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {client.projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                clientSlug={client.slug}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
