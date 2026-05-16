"use client";

import { ExternalLink } from "lucide-react";
import type { Source } from "@/lib/api";

/** Expandable [Tx] citation list shown under each verified assistant message. */
export function SourcesPanel({ sources }: { sources: Source[] }) {
  if (!sources?.length) return null;
  return (
    <details className="mt-3 text-sm group">
      <summary className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors select-none">
        Kaynaklar ({sources.length}) ▾
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map((s) => (
          <li
            key={s.marker}
            className="rounded-lg border border-border/60 bg-card/40 p-3 backdrop-blur-sm"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-xs text-primary font-semibold">
                [{s.marker}]
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                {s.tool}
              </span>
            </div>
            {s.source_name && (
              <div className="text-sm text-foreground font-medium">
                {s.source_name}
                {s.page_number !== undefined && s.page_number !== null
                  ? ` · p.${s.page_number}`
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
                className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Kaynağa git <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
