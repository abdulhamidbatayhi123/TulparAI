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

/**
 * "Nasıl cevapladım?" transparency drawer.
 *
 * This is the verifier's IP on display:
 *   - lists every tool call (with latency)
 *   - shows the verification score
 *   - shows claims the verifier REMOVED (most powerful piece for the demo)
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
  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="link" size="sm" className="px-0 h-auto text-xs text-muted-foreground hover:text-primary">
          Nasıl cevapladım? →
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Cevap akışı (şeffaflık)</DrawerTitle>
          <DrawerDescription>
            Verifier her [Tx] iddiasını ilgili tool çıktısıyla karşılaştırır;
            kanıtsız iddialar otomatik silinir.
          </DrawerDescription>
        </DrawerHeader>
        <div className="space-y-5 p-4 pb-8 overflow-y-auto max-h-[70vh]">
          <section>
            <h3 className="font-semibold mb-2 text-sm">Doğrulama Skoru</h3>
            <div className="text-3xl font-bold">
              {Math.round(verificationScore * 100)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Verifier tarafından desteklenen cümlelerin oranı.
            </p>
          </section>

          <section>
            <h3 className="font-semibold mb-2 text-sm">
              Tool Çağrıları ({trace.length})
            </h3>
            {trace.length === 0 ? (
              <p className="text-sm text-muted-foreground">Tool çağrısı yapılmadı.</p>
            ) : (
              <ol className="space-y-1 list-decimal pl-5">
                {trace.map((t, i) => (
                  <li
                    key={i}
                    className="rounded border border-border/60 bg-card/40 p-2 font-mono text-[11px]"
                  >
                    <div>
                      <span className="text-primary font-semibold">[T{i + 1}] {t.tool}</span>
                      <span className="text-muted-foreground"> · {t.ms}ms</span>
                    </div>
                    <div className="text-muted-foreground truncate mt-0.5">
                      {JSON.stringify(t.args).slice(0, 240)}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {removedClaims.length > 0 && (
            <section>
              <h3 className="font-semibold mb-2 text-sm text-amber-400">
                Doğrulanamayan iddialar ({removedClaims.length})
              </h3>
              <p className="text-xs text-muted-foreground mb-2">
                Bu cümleler Verifier tarafından silindi — kaynak yoktu.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-sm text-muted-foreground">
                {removedClaims.map((claim, i) => (
                  <li key={i} className="leading-snug">
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
