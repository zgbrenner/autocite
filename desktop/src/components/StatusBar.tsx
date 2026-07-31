import {
  CheckCircle,
  MagnifyingGlassMinus,
  MagnifyingGlassPlus,
} from "@phosphor-icons/react";

import type { DocumentStats } from "../lib/documentModel";

interface StatusBarProps {
  stats: DocumentStats;
  issueCount: number;
  mode: string;
  jurisdiction: string | null;
  zoom: number;
  onZoomChange(value: number): void;
}

export function StatusBar({
  stats,
  issueCount,
  mode,
  jurisdiction,
  zoom,
  onZoomChange,
}: StatusBarProps) {
  return (
    <footer className="status-bar">
      <div className="status-left">
        <span>Page 1 of {stats.estimatedPages}</span>
        <span>{stats.words.toLocaleString()} words</span>
        <span>{stats.characters.toLocaleString()} characters</span>
        <span className="status-review-count">
          <CheckCircle size={14} weight="fill" />
          {issueCount} review item{issueCount === 1 ? "" : "s"}
        </span>
      </div>
      <div className="status-right">
        <span>{mode === "auto" ? "Automatic style" : mode}</span>
        <span>{jurisdiction ?? "Automatic jurisdiction"}</span>
        <div className="status-zoom">
          <MagnifyingGlassMinus size={15} aria-hidden="true" />
          <input
            aria-label="Status bar zoom"
            type="range"
            min="70"
            max="160"
            step="5"
            value={zoom}
            onChange={(event) => onZoomChange(Number(event.currentTarget.value))}
          />
          <MagnifyingGlassPlus size={15} aria-hidden="true" />
          <span>{zoom}%</span>
        </div>
      </div>
    </footer>
  );
}
