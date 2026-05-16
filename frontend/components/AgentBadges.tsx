"use client";

import { Search, Brain, ShieldCheck, Sparkles, Check } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 1, label: "Analyzer",  icon: Search,      hint: "Niyet analizi" },
  { id: 2, label: "Reasoner",  icon: Brain,       hint: "Tool kullanımı" },
  { id: 3, label: "Verifier",  icon: ShieldCheck, hint: "İddia doğrulama" },
  { id: 4, label: "Formatter", icon: Sparkles,    hint: "Cevap biçimi" },
];

/**
 * Live pipeline progress strip — the four-agent story made visible.
 *
 * `currentStep` semantics: null = idle; integer 1-4 = step in flight; once a
 * later step fires, prior steps get marked done.
 */
export function AgentBadges({ currentStep }: { currentStep: number | null }) {
  return (
    <div className="flex items-center justify-center gap-1.5 px-2 overflow-x-auto pb-1">
      {STEPS.map(({ id, label, icon: Icon, hint }, idx) => {
        const done = currentStep !== null && currentStep > id;
        const active = currentStep === id;
        const idle = !active && !done;
        return (
          <div key={id} className="flex items-center">
            {idx > 0 && (
              <div
                className={cn(
                  "w-3 h-px mx-0.5 transition-colors duration-300",
                  done ? "bg-emerald-500/50" : active ? "bg-primary/40" : "bg-border"
                )}
              />
            )}
            <div
              title={hint}
              className={cn(
                "flex items-center gap-1.5 rounded-full border whitespace-nowrap transition-all duration-300 select-none",
                "px-2.5 py-1 text-[11px] font-medium",
                active && "bg-primary/12 border-primary/50 text-primary shadow-[0_0_0_1px_oklch(from_var(--primary)_l_c_h/0.25)] motion-safe:animate-pulse",
                done   && "bg-emerald-500/10 border-emerald-500/40 text-emerald-500",
                idle   && "bg-card/60 border-border text-muted-foreground"
              )}
            >
              <span
                className={cn(
                  "inline-flex items-center justify-center w-3.5 h-3.5 rounded-full font-mono text-[9px] font-semibold leading-none transition-colors",
                  active && "bg-primary/20",
                  done   && "bg-emerald-500/20",
                  idle   && "bg-border/60"
                )}
              >
                {done ? <Check className="w-2.5 h-2.5" /> : id}
              </span>
              <Icon className="w-3 h-3" />
              {label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
