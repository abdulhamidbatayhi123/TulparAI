"use client";

import { useEffect, useState } from "react";
import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLang, useCopy } from "@/lib/lang";

/**
 * Header pill that flips the UI between Turkish and English.
 *
 * Mirrors ThemeToggle's pattern (hidden until client mount to avoid hydration
 * mismatch, persisted to localStorage by the LanguageProvider).
 */
export function LanguageToggle() {
  const { lang, setLang } = useLang();
  const c = useCopy();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const next: "tr" | "en" = lang === "tr" ? "en" : "tr";
  const label = lang.toUpperCase();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setLang(next)}
      className="text-muted-foreground hover:text-foreground transition-colors relative"
      title={c.toggleLanguage}
      aria-label={c.toggleLanguage}
    >
      {mounted ? (
        <>
          <Languages className="w-5 h-5" />
          <span className="absolute -bottom-0.5 -right-0.5 font-mono text-[8px] font-bold text-primary bg-background rounded px-0.5 leading-tight">
            {label}
          </span>
        </>
      ) : (
        <Languages className="w-5 h-5 opacity-0" />
      )}
    </Button>
  );
}
