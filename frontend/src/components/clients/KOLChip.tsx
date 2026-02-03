"use client";

import { Avatar } from "./Avatar";
import type { KOLSummary } from "@/lib/api";

interface KOLChipProps {
  kol: KOLSummary;
  showDetails?: boolean;
  onClick?: () => void;
  size?: "sm" | "md" | "lg";
}

export function KOLChip({ kol, showDetails = false, onClick, size = "sm" }: KOLChipProps) {
  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      onClick={onClick}
      className={`inline-flex items-center gap-2 bg-gray-50 rounded-full pr-3 pl-1 py-1 ${
        onClick ? "hover:bg-gray-100 cursor-pointer transition-colors" : ""
      }`}
    >
      <Avatar name={kol.name} imageUrl={kol.photo_url} size={size} />
      <div className="text-left">
        <span className="text-sm font-medium text-gray-900">{kol.name}</span>
        {showDetails && kol.specialty && (
          <span className="text-xs text-gray-500 block">{kol.specialty}</span>
        )}
      </div>
    </Wrapper>
  );
}

interface KOLChipListProps {
  kols: KOLSummary[];
  maxVisible?: number;
  showDetails?: boolean;
}

export function KOLChipList({ kols, maxVisible = 3, showDetails = false }: KOLChipListProps) {
  const visible = kols.slice(0, maxVisible);
  const remaining = kols.length - maxVisible;

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {visible.map((kol) => (
        <KOLChip key={kol.id} kol={kol} showDetails={showDetails} />
      ))}
      {remaining > 0 && (
        <span className="text-sm text-gray-500 pl-1">+{remaining} more</span>
      )}
    </div>
  );
}
