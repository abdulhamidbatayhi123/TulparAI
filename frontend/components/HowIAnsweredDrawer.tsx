"use client";

import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
  DrawerDescription,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import type { ToolCall } from "@/lib/api";
import { ShieldCheck, AlertTriangle, ArrowRight, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * "Nasıl cevapladım?" transparency drawer — the verifier's IP on display.
 *
 *   - lists every tool call (with latency)
 *   - shows the verification score
 *   - shows claims the verifier REMOVED (most powerful piece for the demo)
 *
 * This is the moment a judge realises the verifier is not a marketing line but
 * a real, visible model whose deletions you can audit.
 */
export function HowIAnsweredDrawer({
  trace,
  removedClaims,
  verificationScore,
}: {
  trace: ToolCall[];
  removedClaims: string[];
  verificationScore: number;
}) {
  const pct = Math.round(verificationScore * 100);
  const scoreColor =
    verificationScore >= 0.8
      ? "text-emerald-500"
      : verificationScore >= 0.5
      ? "text-amber-500"
      : "text-destructive";

  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button
          variant="link"
          size="sm"
          className="px-0 h-auto text-xs text-muted-foreground hover:text-primary group"
        >
          Nasıl cevapladım?
          <ArrowRight className="w-3 h-3 ml-0.5 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="w-4 h-4 text-primary" />
            Cevap akışı · şeffaflık
          </DrawerTitle>
          <DrawerDescription>
            Verifier her <span className="font-mono text-foreground/80">[Tx]</span> iddiasını ilgili tool çıktısıyla karşılaştırır.
            Kanıtsız iddialar otomatik silinir.
          </DrawerDescription>
        </DrawerHeader>

        <div className="space-y-5 px-4 pb-8 overflow-y-auto max-h-[70vh]">
          {/* Verification score — the visible guardrail */}
          <section className="rounded-xl border border-border bg-card/40 backdrop-blur-sm p-4">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-xs uppercase tracking-widest text-muted-foreground">
                Doğrulama Skoru
              </h3>
              <span className={cn("font-display text-4xl font-medium leading-none", scoreColor)}>
                {pct}%
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
              Verifier tarafından desteklenen cümlelerin oranı. Düşük skor → cevabın çoğu
              kaynağa bağlı değil. Yüksek skor → her cümle bir tool çıktısıyla eşleşti.
            </p>
          </section>

          {/* Tool trace */}
          <section>
            <h3 className="font-semibold mb-2 text-sm flex items-center gap-2">
              <Wrench className="w-3.5 h-3.5 text-muted-foreground" />
              Tool Çağrıları
              <span className="text-xs text-muted-foreground font-mono ml-1">
                ({trace.length})
              </span>
            </h3>
            {trace.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                Tool çağrısı yapılmadı.
              </p>
            ) : (
              <ol className="space-y-1.5">
                {trace.map((t, i) => (
                  <li
                    key={i}
                    className="rounded-lg border border-border/60 bg-card/40 p-2.5 font-mono text-[11px]"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-primary font-semibold">
                        [T{i + 1}] {t.tool}
                      </span>
                      <span className="text-muted-foreground">{t.ms}ms</span>
                    </div>
                    <div className="text-muted-foreground/80 truncate mt-1">
                      {JSON.stringify(t.args).slice(0, 240)}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {/* Removed claims — THE differentiator */}
          {removedClaims.length > 0 && (
            <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
              <h3 className="font-semibold mb-1.5 text-sm flex items-center gap-2 text-amber-600 dark:text-amber-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                Doğrulanamayan iddialar
                <span className="text-xs font-mono ml-1 opacity-70">
                  ({removedClaims.length})
                </span>
              </h3>
              <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
                Verifier bu cümleleri sildi — söylenmiş olsa zarar verirdi, kaynağı yoktu.
                <span className="block mt-0.5 text-muted-foreground/70">
                  Bu, halüsinasyona karşı uygulanan invariant'ın görünür izi.
                </span>
              </p>
              <ul className="space-y-1.5 text-sm">
                {removedClaims.map((claim, i) => (
                  <li
                    key={i}
                    className="leading-snug text-muted-foreground line-through decoration-amber-500/60 decoration-1"
                  >
                    {claim}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}
