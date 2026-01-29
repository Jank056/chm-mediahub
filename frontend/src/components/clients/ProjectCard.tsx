"use client";

import Link from "next/link";
import { Badge } from "./Badge";
import { StatValue } from "./StatValue";
import type { ProjectSummary } from "@/lib/api";

interface ProjectCardProps {
  project: ProjectSummary;
  clientSlug: string;
}

export function ProjectCard({ project, clientSlug }: ProjectCardProps) {
  return (
    <Link
      href={`/dashboard/clients/${clientSlug}/projects/${project.code}`}
      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow p-5"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 text-lg">{project.name}</h3>
          {project.code && (
            <span className="text-sm text-gray-500 font-mono">{project.code}</span>
          )}
        </div>
        <Badge variant={project.is_active ? "success" : "default"}>
          {project.is_active ? "Active" : "Inactive"}
        </Badge>
      </div>

      {project.description && (
        <p className="text-sm text-gray-600 mb-4 line-clamp-2">{project.description}</p>
      )}

      <div className="flex items-center gap-6 pt-3 border-t border-gray-100">
        <StatValue
          value={project.kol_group_count}
          label="KOL Groups"
          size="sm"
        />
      </div>
    </Link>
  );
}
