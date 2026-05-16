"use client";

import { useState } from "react";
import { ExternalLink, BookOpen, ChevronRight } from "lucide-react";
import type { Source } from "@/lib/api";
import { cn } from "@/lib/utils";

const TOOL_LABEL: Record<string, string> = {
  search_sport_kb:    "Spor KB",
  web_search_trusted: "Web (whitelisted)",
  get_food_macros:    "USDA / OFF",
  calc_macros:        "Hesap",
  get_weather:        "Hava",
  log_session:        "Kayıt",
  analyze_image:      "Görüntü",
};

/**
 * Expandable [Tx] citation list — the visible proof that the answer is grounded
 * in a real tool response. Built as a stateful disclosure (not <details>) so we
 * can drive a clean rotation on the chevron and keep the animation in our
 * design system rather than the browser default.
 */
export function SourcesPanel({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;

  return (
    <div className="mt-3 text-sm">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="group inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors select-none rounded-md px-1 -mx-1 py-0.5 focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:outline-none"
        aria-expanded={open}
      >
        <BookOpen className="w-3.5 h-3.5" />
        <span className="font-medium">Kaynaklar</span>
        <span className="text-xs text-muted-foreground/70 font-mono">({sources.length})</span>
        <ChevronRight
          className={cn(
            "w-3.5 h-3.5 transition-transform duration-200",
            open && "rotate-90"
          )}
        />
      </button>

      {open && (
        <ul className="mt-2 space-y-2 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-top-1 motion-safe:duration-200">
          {sources.map((s) => (
            <li
              key={s.marker}
              className="rounded-lg border border-border/60 bg-card/40 p-3 backdrop-blur-sm"
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-primary font-semibold">
                  <span className="inline-flex items-center justify-center min-w-[20px] h-[20px] rounded-md bg-primary/15 px-1 ring-1 ring-primary/30">
                    {s.marker}
                  </span>
                </span>
                <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">
                  {TOOL_LABEL[s.tool] || s.tool}
                </span>
              </div>
              {s.source_name && (
                <div className="text-sm text-foreground font-medium leading-snug">
                  {s.source_name}
                  {s.page_number !== undefined && s.page_number !== null
                    ? <span className="text-muted-foreground"> · p.{s.page_number}</span>
                    : null}
                </div>
              )}
              <p className="mt-1 text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                {s.text}
              </p>
              {s.url && (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:outline-none rounded"
                >
                  Kaynağa git <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
