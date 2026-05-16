"use client";

import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

/**
 * Inline confidence indicator (green / amber / red) for a verified message.
 *
 * Color thresholds mirror the verifier's contract:
 *   ≥0.8  fully grounded — every cited claim survived
 *   0.5–0.8  partial — some claims were stripped, kept ones are safe
 *   <0.5  low — the verifier removed most of the answer; treat as exploratory
 *
 * Title attribute provides the verbal explanation for keyboard / hover users.
 */
export function VerifiedBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);

  if (score >= 0.8) {
    return (
      <span
        title={`Doğrulanmış · Verifier ${pct}% güvende — her [Tx] iddiası tool çıktısıyla eşleşti`}
        className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-500 px-2 py-0.5 text-[11px] font-medium ring-1 ring-emerald-500/10 shadow-[inset_0_0_0_1px_oklch(0.85_0.15_160/0.05)]"
      >
        <CheckCircle2 className="w-3 h-3" />
        Doğrulandı · <span className="font-mono">{pct}%</span>
      </span>
    );
  }
  if (score >= 0.5) {
    return (
      <span
        title={`Kısmen doğrulanmış · Verifier ${pct}% — bazı iddialar silindi, kalanlar güvenli`}
        className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-500 px-2 py-0.5 text-[11px] font-medium"
      >
        <AlertTriangle className="w-3 h-3" />
        Kısmen · <span className="font-mono">{pct}%</span>
      </span>
    );
  }
  return (
    <span
      title={`Doğrulanamadı · Verifier ${pct}% — bu cevabı yalnız bir başlangıç olarak al, kaynağa git`}
      className="inline-flex items-center gap-1 rounded-full bg-destructive/15 border border-destructive/40 text-destructive px-2 py-0.5 text-[11px] font-medium"
    >
      <XCircle className="w-3 h-3" />
      Doğrulanamadı · <span className="font-mono">{pct}%</span>
    </span>
  );
}
