"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { clientsApi, type ProjectDetail } from "@/lib/api";
import { Badge, KOLGroupCard, StatValue } from "@/components/clients";

export default function ProjectDetailPage() {
  const params = useParams();
  const slug = params.slug as string;
  const projectCode = params.projectId as string; // Route uses [projectId] but it's actually project code

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const projectData = await clientsApi.getProject(slug, projectCode);
        setProject(projectData);
      } catch (err) {
        setError("Failed to load project");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [slug, projectCode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error || "Project not found"}
      </div>
    );
  }

  // Calculate project totals from KOL groups
  const totals = project.kol_groups.reduce(
    (acc, group) => ({
      kols: acc.kols + group.kol_count,
      clips: acc.clips + group.clip_count,
      views: acc.views + group.total_views,
      videos: acc.videos + (group.video_count || 0),
    }),
    { kols: 0, clips: 0, views: 0, videos: 0 }
  );

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500">
        <Link href="/dashboard/clients" className="hover:text-blue-600">
          Clients
        </Link>
        <span className="mx-2">/</span>
        <Link href={`/dashboard/clients/${project.client_slug}`} className="hover:text-blue-600">
          {project.client_name}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">{project.name}</span>
      </nav>

      {/* Project Header */}
      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
              <Badge variant={project.is_active ? "success" : "default"} size="md">
                {project.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            {project.code && (
              <span className="text-sm text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">
                {project.code}
              </span>
            )}
          </div>
        </div>
        {project.description && (
          <p className="text-gray-600 mb-6">{project.description}</p>
        )}

        {/* Project Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-gray-100">
          <StatValue value={project.kol_groups.length} label="KOL Groups" />
          <StatValue value={totals.kols} label="Total KOLs" />
          <StatValue value={totals.clips} label="Total Clips" />
          <StatValue value={totals.views} label="Total Views" format="compact" />
        </div>
      </div>

      {/* KOL Groups Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            KOL Groups ({project.kol_groups.length})
          </h2>
        </div>
        {project.kol_groups.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">No KOL groups yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {project.kol_groups.map((group) => (
              <KOLGroupCard
                key={group.id}
                group={group}
                clientSlug={project.client_slug}
                projectCode={project.code}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
