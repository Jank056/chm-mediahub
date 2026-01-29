"use client";

import Link from "next/link";
import { Avatar } from "./Avatar";
import { Badge } from "./Badge";
import { StatValue } from "./StatValue";
import type { ClientSummary } from "@/lib/api";

interface ClientCardProps {
  client: ClientSummary;
}

export function ClientCard({ client }: ClientCardProps) {
  return (
    <Link
      href={`/dashboard/clients/${client.slug}`}
      className="block bg-white rounded-xl shadow hover:shadow-lg transition-all p-6 border border-gray-100"
    >
      <div className="flex items-start gap-4 mb-4">
        <Avatar name={client.name} imageUrl={client.logo_url} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 text-xl truncate">{client.name}</h3>
            <Badge variant={client.is_active ? "success" : "default"}>
              {client.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>
          <span className="text-sm text-gray-500">/{client.slug}</span>
        </div>
      </div>

      <div className="flex items-center gap-8 pt-4 border-t border-gray-100">
        <StatValue value={client.project_count} label="Projects" size="sm" />
      </div>
    </Link>
  );
}

interface ClientCardCompactProps {
  client: ClientSummary;
  isSelected?: boolean;
  onClick?: () => void;
}

export function ClientCardCompact({ client, isSelected, onClick }: ClientCardCompactProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors text-left ${
        isSelected
          ? "bg-blue-50 border-blue-200 border"
          : "bg-white hover:bg-gray-50 border border-gray-200"
      }`}
    >
      <Avatar name={client.name} imageUrl={client.logo_url} size="md" />
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-gray-900 truncate">{client.name}</h4>
        <span className="text-xs text-gray-500">
          {client.project_count} project{client.project_count !== 1 ? "s" : ""}
        </span>
      </div>
    </button>
  );
}
