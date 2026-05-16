"use client";

import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";

/** Inline confidence indicator (green/amber/red) for a verified message. */
export function VerifiedBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);

  if (score >= 0.8) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 px-2 py-0.5 text-[11px] font-medium">
        <CheckCircle className="w-3 h-3" /> Doğrulandı · {pct}%
      </span>
    );
  }
  if (score >= 0.5) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-400 px-2 py-0.5 text-[11px] font-medium">
        <AlertTriangle className="w-3 h-3" /> Kısmen · {pct}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/20 border border-destructive/50 text-destructive px-2 py-0.5 text-[11px] font-medium">
      <XCircle className="w-3 h-3" /> Doğrulanamadı
    </span>
  );
}
