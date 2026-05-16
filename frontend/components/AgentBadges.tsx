"use client";

import { Search, Brain, ShieldCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 1, label: "Analyzer", icon: Search },
  { id: 2, label: "Reasoner + Tools", icon: Brain },
  { id: 3, label: "Verifier", icon: ShieldCheck },
  { id: 4, label: "Formatter", icon: Sparkles },
];

/** Live pipeline progress strip. `currentStep` null = idle; integer 1-4 = in flight. */
export function AgentBadges({ currentStep }: { currentStep: number | null }) {
  return (
    <div className="flex items-center gap-2 px-2 overflow-x-auto pb-1">
      {STEPS.map(({ id, label, icon: Icon }) => {
        const done = currentStep !== null && currentStep > id;
        const active = currentStep === id;
        return (
          <div
            key={id}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] whitespace-nowrap transition-all",
              active && "bg-primary/15 border-primary/50 text-primary animate-pulse",
              done && "bg-emerald-500/15 border-emerald-500/40 text-emerald-400",
              !active && !done && "bg-card border-border text-muted-foreground"
            )}
          >
            <Icon className="w-3 h-3" />
            {label}
          </div>
        );
      })}
    </div>
  );
}
