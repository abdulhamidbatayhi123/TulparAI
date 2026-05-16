"use client";

import { Search, Apple, Calculator, CloudSun, NotebookPen, Globe, Eye } from "lucide-react";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  search_sport_kb:    Search,
  get_food_macros:    Apple,
  calc_macros:        Calculator,
  get_weather:        CloudSun,
  log_session:        NotebookPen,
  web_search_trusted: Globe,
  analyze_image:      Eye,
};

/**
 * Inline chip representing one tool call inside an assistant message.
 *
 * Used while the Reasoner is streaming: each tool the LLM calls pops up here
 * with its name, args summary and latency. This is the "you can see the AI
 * doing real work" element of the demo.
 */
export function ToolCallChip({
  tool,
  summary,
  ms,
}: {
  tool: string;
  summary: string;
  ms: number;
}) {
  const Icon = ICONS[tool] || Search;
  return (
    <div className="my-1 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/5 backdrop-blur-sm px-2.5 py-1 text-[11px] max-w-full motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-left-1 motion-safe:duration-200">
      <Icon className="w-3 h-3 text-primary shrink-0" />
      <span className="font-mono font-semibold text-foreground">{tool}</span>
      <span className="text-muted-foreground/70 shrink-0 font-mono text-[10px]">
        {ms}ms
      </span>
      <span className="text-muted-foreground/80 truncate hidden sm:inline">
        · {summary}
      </span>
    </div>
  );
}
