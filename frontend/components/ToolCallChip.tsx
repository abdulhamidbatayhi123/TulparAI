"use client";

import { Search, Apple, Calculator, CloudSun, NotebookPen, Globe } from "lucide-react";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  search_sport_kb: Search,
  get_food_macros: Apple,
  calc_macros: Calculator,
  get_weather: CloudSun,
  log_session: NotebookPen,
  web_search_trusted: Globe,
};

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
    <div className="my-1 inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/60 backdrop-blur-sm px-3 py-1 text-[11px] max-w-full">
      <Icon className="w-3 h-3 text-primary shrink-0" />
      <span className="font-mono font-semibold text-foreground">{tool}</span>
      <span className="text-muted-foreground shrink-0">· {ms}ms</span>
      <span className="text-muted-foreground/80 truncate">· {summary}</span>
    </div>
  );
}
