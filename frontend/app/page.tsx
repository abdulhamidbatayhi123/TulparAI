"use client";

import { useEffect, useRef, useState } from "react";
import {
  Plus, UserCog, UploadCloud, PanelLeft,
  Trash2, Image as ImageIcon, Mic, Send,
  Apple, HeartPulse, Moon, Activity, Sparkles, ShieldCheck, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  openChatStream, getHealth, fileToBase64, getProfile, listPersonalDocs,
  type ChatStreamEvent, type Source, type ToolCall,
} from "@/lib/api";
import { startVoice, isVoiceSupported, type VoiceHandle } from "@/lib/speech";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ProfileDialog } from "@/components/ProfileDialog";
import { UploadDialog } from "@/components/UploadDialog";
import { AgentBadges } from "@/components/AgentBadges";
import { ToolCallChip } from "@/components/ToolCallChip";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { SourcesPanel } from "@/components/SourcesPanel";
import { HowIAnsweredDrawer } from "@/components/HowIAnsweredDrawer";

/** Demo athletes seeded by `backend/scripts/seed_demo.py` — the four-athletes-one-question wow. */
const ATHLETES = [
  { id: "ahmet",   name: "Ahmet",   emoji: "⚽", sport: "Futbol" },
  { id: "ayse",    name: "Ayşe",    emoji: "🏐", sport: "Voleybol" },
  { id: "mehmet",  name: "Mehmet",  emoji: "🤼", sport: "Güreş" },
  { id: "naim",    name: "Naim",    emoji: "🏋️", sport: "Halter" },
] as const;

type Msg = {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
  trace?: ToolCall[];
  removedClaims?: string[];
  verified?: number;
  liveTools?: { tool: string; summary: string; ms: number }[];
  latencyMs?: number;
};

const DEFAULT_ATHLETE =
  process.env.NEXT_PUBLIC_DEFAULT_ATHLETE || "ahmet";
const LANGUAGE: "tr" | "en" =
  (process.env.NEXT_PUBLIC_DEFAULT_LANG as "tr" | "en") || "tr";
const ATHLETE_STORAGE_KEY = "tulparai.athleteId";

export default function Home() {
  const [message, setMessage] = useState("");
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [modelInfo, setModelInfo] = useState<string>("");
  const [athleteId, setAthleteId] = useState<string>(DEFAULT_ATHLETE);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [personalDocCount, setPersonalDocCount] = useState<number>(0);
  const [pendingImage, setPendingImage] = useState<{ b64: string; preview: string; name: string } | null>(null);
  const [voiceState, setVoiceState] = useState<"idle" | "listening">("idle");

  // Hydrate athlete from localStorage on mount (avoids SSR/CSR mismatch)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem(ATHLETE_STORAGE_KEY);
    if (saved && ATHLETES.some((a) => a.id === saved)) {
      setAthleteId(saved);
    }
  }, []);
  const endRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);
  const voiceRef = useRef<VoiceHandle | null>(null);

  // Health-poll once on mount so the footer dot reflects reality
  useEffect(() => {
    getHealth()
      .then((h) => {
        setBackendOnline(true);
        setModelInfo(h.models?.reasoner?.split("/").pop() || "online");
      })
      .catch(() => setBackendOnline(false));
  }, []);

  // Load profile + personal doc count whenever athlete changes (or after edits)
  const refreshProfile = () => {
    getProfile(athleteId).then(setProfile).catch(() => setProfile(null));
    listPersonalDocs(athleteId)
      .then((r) => setPersonalDocCount(r.files?.length || 0))
      .catch(() => setPersonalDocCount(0));
  };
  // Re-fetch whenever the active athlete changes
  useEffect(() => { refreshProfile(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [athleteId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentStep]);

  // Cleanup any in-flight stream on unmount
  useEffect(() => () => cancelRef.current?.(), []);

  const setQuery = (q: string) => setMessage(q);

  const clearChat = () => {
    cancelRef.current?.();
    cancelRef.current = null;
    setMessages([]);
    setCurrentStep(null);
    setBusy(false);
  };

  // Switch the active athlete — clears chat so context doesn't bleed across personas,
  // persists the choice to localStorage, and triggers a profile re-fetch via the
  // `[athleteId]` effect above. The four-sporcular-aynı-soru demo is one click each.
  const switchAthlete = (id: string) => {
    if (id === athleteId || busy) return;
    setAthleteId(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ATHLETE_STORAGE_KEY, id);
    }
    clearChat();
  };

  const toggleVoice = () => {
    if (voiceState === "listening") {
      voiceRef.current?.stop();
      setVoiceState("idle");
      return;
    }
    if (!isVoiceSupported()) {
      alert("Tarayıcınız sesli giriş desteklemiyor (Chrome / Edge / Safari önerilir).");
      return;
    }
    setVoiceState("listening");
    voiceRef.current = startVoice({
      lang: LANGUAGE === "en" ? "en-US" : "tr-TR",
      onPartial: (text) => setMessage(text),
      onFinal: (text) => {
        setMessage(text);
        // small delay so the user sees the final transcript before submission
        setTimeout(() => {
          setVoiceState("idle");
          // auto-send after voice command (mobile-friendly hands-free flow)
          if (text.trim()) {
            // need a stale-free send: read latest message from state
            setMessage((curr) => {
              const final = curr.trim() || text.trim();
              // schedule send after state settles
              setTimeout(() => sendWithText(final), 0);
              return "";
            });
          }
        }, 300);
      },
      onError: (msg) => {
        setVoiceState("idle");
        alert(msg);
      },
      onEnd: () => setVoiceState("idle"),
    });
  };

  const sendWithText = (overrideText?: string) => {
    const text = (overrideText ?? message).trim();
    if ((!text && !pendingImage) || busy) return;
    setMessage("");
    setBusy(true);
    setCurrentStep(1);

    setMessages((m) => [
      ...m,
      { role: "user", text: text || "[Resim eklendi]" },
      { role: "assistant", text: "", liveTools: [] },
    ]);

    const imageBase64 = pendingImage?.b64;
    setPendingImage(null);

    cancelRef.current = openChatStream(
      {
        athlete_id: athleteId,
        message: text || "Bu görseli analiz et",
        language: LANGUAGE,
        image_base64: imageBase64,
      },
      (ev: ChatStreamEvent) => {
        if (ev.type === "step") {
          setCurrentStep(ev.step);
        } else if (ev.type === "tool_call") {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            last.liveTools = [
              ...(last.liveTools || []),
              { tool: ev.tool, summary: ev.summary, ms: ev.ms },
            ];
            return copy;
          });
        } else if (ev.type === "token") {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            last.text = (last.text || "") + ev.content;
            return copy;
          });
        } else if (ev.type === "done") {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = {
              role: "assistant",
              text: ev.answer,
              sources: ev.sources,
              trace: ev.trace,
              removedClaims: ev.removed_claims || [],
              verified: ev.verification_score,
              liveTools: last.liveTools,
              latencyMs: ev.latency_ms,
            };
            return copy;
          });
          setBusy(false);
          setCurrentStep(null);
          cancelRef.current = null;
        } else if (ev.type === "error") {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              role: "assistant",
              text: `⚠ Hata: ${ev.message}`,
            };
            return copy;
          });
          setBusy(false);
          setCurrentStep(null);
          cancelRef.current = null;
        }
      }
    );
  };

  const handleFilePick = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      alert("Sadece resim dosyaları desteklenir (jpg / png / webp).");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert("Resim çok büyük (maks 5 MB).");
      return;
    }
    const b64 = await fileToBase64(file);
    setPendingImage({
      b64,
      preview: URL.createObjectURL(file),
      name: file.name,
    });
  };

  const send = () => sendWithText();

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className={`relative z-10 ${isSidebarOpen ? "w-64" : "w-0"} transition-all duration-300 ease-in-out flex flex-col border-r border-border bg-card/40 backdrop-blur-md overflow-hidden shrink-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-primary via-primary to-primary/80 flex items-center justify-center text-primary-foreground shadow-sm ring-1 ring-primary/30">
              <span className="font-display text-lg font-medium italic leading-none translate-y-[1px]">T</span>
            </div>
            <h1 className="font-display text-2xl font-medium tracking-tight text-foreground whitespace-nowrap leading-none">
              Tulpar<span className="italic text-primary">AI</span>
            </h1>
          </div>
        </div>

        <div className="p-4 flex-1 overflow-y-auto space-y-6">
          <Button
            className="w-full justify-start gap-2"
            variant="outline"
            onClick={clearChat}
          >
            <Plus className="w-4 h-4" />
            Yeni Sohbet
          </Button>

          {/* Athlete switcher — the live demo magic.
              4 sporcular, tek tıkla geçiş. Aynı soru sorulduğunda kişiselleştirme görünür. */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              <span>Demo Sporcuları</span>
              <span className="text-[9px] font-mono normal-case tracking-normal text-muted-foreground/60">
                ↻ aynı soru
              </span>
            </h3>
            <div className="grid grid-cols-2 gap-1.5">
              {ATHLETES.map((a) => {
                const active = a.id === athleteId;
                return (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => switchAthlete(a.id)}
                    disabled={busy}
                    title={busy ? "Cevap akarken geçiş yapılamaz" : `${a.name} (${a.sport})`}
                    className={cn(
                      "group relative rounded-lg border p-2 flex flex-col items-center gap-0.5 transition-all",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      active
                        ? "border-primary/60 bg-primary/8 ring-1 ring-primary/30 shadow-[0_0_0_3px_oklch(from_var(--primary)_l_c_h/0.08)]"
                        : "border-border bg-background/40 hover:border-primary/40 hover:bg-card/60"
                    )}
                  >
                    <span className="text-xl leading-none" aria-hidden="true">{a.emoji}</span>
                    <span className={cn("text-[11px] font-semibold leading-tight", active && "text-primary")}>
                      {a.name}
                    </span>
                    <span className="text-[8.5px] uppercase tracking-[0.12em] text-muted-foreground leading-tight">
                      {a.sport}
                    </span>
                    {active && (
                      <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-primary ring-2 ring-background" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active athlete details */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Aktif Profil
            </h3>
            <div className="p-3 rounded-lg bg-background/60 border border-border">
              <div className="mb-2">
                <h4 className="text-sm font-semibold text-foreground leading-tight">
                  {(profile?.name as string) || "—"}
                </h4>
                <p className="text-xs text-muted-foreground capitalize mt-0.5">
                  {profile ? (
                    <>
                      {(profile.sport as string) || "?"}
                      {(() => {
                        const sp = profile.sport_profile as Record<string, unknown> | undefined;
                        const detail = sp?.position || sp?.weight_class;
                        return detail ? ` · ${detail}` : "";
                      })()}
                      {(profile.training_phase as string)
                        ? ` · ${profile.training_phase as string}`
                        : ""}
                    </>
                  ) : "Yükleniyor..."}
                </p>
              </div>
              <ProfileDialog athleteId={athleteId} onSaved={refreshProfile}>
                <Button variant="secondary" size="sm" className="w-full text-xs h-8 gap-2">
                  <UserCog className="w-3.5 h-3.5" />
                  Profili Düzenle
                </Button>
              </ProfileDialog>
            </div>
          </div>

          {/* Knowledge Base */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Bilgi Tabanı
            </h3>
            <div className="flex gap-2">
              <div className="flex-1 p-2 rounded-lg bg-background/60 border border-border flex flex-col items-center">
                <span className="font-display text-xl font-medium text-foreground leading-none">7</span>
                <span className="text-[10px] text-muted-foreground uppercase mt-1">Araç</span>
              </div>
              <div className="flex-1 p-2 rounded-lg bg-background/60 border border-border flex flex-col items-center">
                <span className="font-display text-xl font-medium text-foreground leading-none">{personalDocCount}</span>
                <span className="text-[10px] text-muted-foreground uppercase mt-1">Doküman</span>
              </div>
            </div>
            <UploadDialog athleteId={athleteId} onUploaded={refreshProfile}>
              <Button variant="secondary" size="sm" className="w-full text-xs h-8 gap-2">
                <UploadCloud className="w-3.5 h-3.5" />
                Doküman Yükle
              </Button>
            </UploadDialog>
          </div>

          {/* Recents */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Geçmiş
            </h3>
            <div className="text-sm text-muted-foreground text-center py-4">
              {messages.length > 0
                ? `Bu sohbette ${Math.floor(messages.length / 2)} mesaj`
                : "Henüz sohbet yok"}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex items-center gap-2 text-xs text-muted-foreground">
          <div
            className={`w-2 h-2 rounded-full ${
              backendOnline === true
                ? "bg-emerald-500 animate-pulse"
                : backendOnline === false
                ? "bg-destructive"
                : "bg-muted-foreground/40"
            }`}
          ></div>
          {backendOnline === true
            ? `NVIDIA · ${modelInfo}`
            : backendOnline === false
            ? "Backend Offline"
            : "Checking..."}
        </div>
      </aside>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col h-full min-w-0">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-border bg-background/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!isSidebarOpen)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Kenar çubuğunu aç/kapat"
            >
              <PanelLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-lg font-medium tracking-tight text-foreground">
                TulparAI
              </span>
              <span className="hidden sm:inline text-[11px] tracking-widest uppercase text-muted-foreground">
                Spor Asistanı
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {/* Verified-AI badge — pitch shorthand for the verifier guardrail */}
            <span
              className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-500"
              title="Doğrulanmış AI · her [Tx] iddiası kaynak ile eşleştirilir"
            >
              <ShieldCheck className="w-3 h-3" />
              Doğrulanmış AI
            </span>
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon"
              title="Sohbeti temizle"
              className="text-muted-foreground hover:text-destructive"
              onClick={clearChat}
              aria-label="Sohbeti temizle"
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col">
          {messages.length === 0 ? (
            /* Welcome Screen — the hero moment of the demo */
            <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full px-2">
              {/* Eyebrow tag */}
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-primary">
                <Sparkles className="w-3 h-3" />
                <span>4 ajan · 7 araç · doğrulanmış</span>
              </div>

              {/* Display headline. Fraunces handles Turkish glyphs (ş, ç, ğ) cleanly. */}
              <h2 className="font-display text-5xl md:text-6xl font-medium tracking-tight text-foreground text-center leading-[1.02] mb-5 max-w-2xl">
                Türk sporcusunun{" "}
                <span className="italic text-primary" style={{ fontFeatureSettings: '"ss01"' }}>
                  doğrulanmış
                </span>{" "}
                AI antrenörü.
              </h2>

              <p className="text-muted-foreground text-center text-[15px] md:text-base mb-10 max-w-xl leading-relaxed">
                Her cümle bir tool çıktısıyla eşleşir, ardından bir Verifier modeli
                kaynaksız iddiaları siler. Halüsinasyon bir slogan değil — uygulanan
                bir kuraldır.
              </p>

              {/* Example prompts — each opens a real sport-KB question Ahmet would ask. */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                {[
                  {
                    icon: Apple,
                    label: "Beslenme",
                    text: "Yarın akşam maç var, ne yemeliyim?",
                  },
                  {
                    icon: HeartPulse,
                    label: "İyileşme",
                    text: "Maç sonrası iyileşme için en iyi besinler nedir?",
                  },
                  {
                    icon: Moon,
                    label: "Uyku",
                    text: "Performansım için günde kaç saat uyumalıyım?",
                  },
                  {
                    icon: Activity,
                    label: "Antrenman",
                    text: "Forvet olarak hız çalışmaları haftada kaç kez?",
                  },
                ].map((item, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setQuery(item.text)}
                    style={{ animationDelay: `${i * 60}ms` }}
                    className="group text-left p-3.5 rounded-xl border border-border bg-card/40 hover:bg-card hover:border-primary/40 cursor-pointer transition-all flex items-start gap-3 backdrop-blur-sm motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-safe:duration-500"
                  >
                    <div className="shrink-0 w-9 h-9 rounded-lg bg-background border border-border flex items-center justify-center text-muted-foreground group-hover:text-primary group-hover:border-primary/40 transition-colors">
                      <item.icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground group-hover:text-primary/70 transition-colors mb-0.5">
                        {item.label}
                      </div>
                      <p className="text-sm text-foreground leading-snug">{item.text}</p>
                    </div>
                  </button>
                ))}
              </div>

              {/* Tiny infra line — pitch credibility without being heavy */}
              <p className="mt-8 text-[10px] uppercase tracking-[0.22em] text-muted-foreground/70 text-center">
                NVIDIA Nemotron · Türksat altyapısı · Sıfır halüsinasyon
              </p>
            </div>
          ) : (
            /* Chat messages */
            <div className="max-w-3xl mx-auto w-full space-y-6">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-2xl rounded-2xl px-4 py-3 ${
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-card/70 border border-border backdrop-blur-sm"
                    }`}
                  >
                    {/* Live tool chips while reasoner is calling tools */}
                    {m.role === "assistant" && m.liveTools && m.liveTools.length > 0 && (
                      <div className="mb-3 flex flex-wrap gap-1.5">
                        {m.liveTools.map((t, j) => (
                          <ToolCallChip
                            key={j}
                            tool={t.tool}
                            summary={t.summary}
                            ms={t.ms}
                          />
                        ))}
                      </div>
                    )}

                    {/* Answer text (or thinking dots while busy on this msg) */}
                    <div className="whitespace-pre-wrap leading-relaxed">
                      {m.text ||
                        (busy && i === messages.length - 1 ? (
                          <span className="text-muted-foreground italic">
                            Düşünüyorum
                            <span className="animate-pulse">...</span>
                          </span>
                        ) : (
                          ""
                        ))}
                    </div>

                    {/* Footer: verified badge + how-i-answered drawer + latency */}
                    {m.role === "assistant" && m.verified !== undefined && (
                      <div className="mt-3 flex flex-wrap items-center gap-3">
                        <VerifiedBadge score={m.verified} />
                        {m.trace && (
                          <HowIAnsweredDrawer
                            trace={m.trace}
                            removedClaims={m.removedClaims || []}
                            verificationScore={m.verified}
                          />
                        )}
                        {m.latencyMs !== undefined && (
                          <span className="text-[10px] text-muted-foreground font-mono">
                            {(m.latencyMs / 1000).toFixed(1)}s
                          </span>
                        )}
                      </div>
                    )}

                    {/* Sources panel */}
                    {m.role === "assistant" && m.sources && (
                      <SourcesPanel sources={m.sources} />
                    )}
                  </div>
                </div>
              ))}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 w-full max-w-4xl mx-auto">
          {/* Agent Orchestration — lights up live during streaming */}
          <div className="mb-3">
            <AgentBadges currentStep={currentStep} />
          </div>

          {/* Pending image preview chip */}
          {pendingImage && (
            <div className="mb-2 flex items-center gap-3 rounded-lg border border-primary/40 bg-primary/5 p-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pendingImage.preview}
                alt="ek görsel"
                className="h-12 w-12 rounded object-cover"
              />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">
                  {pendingImage.name}
                </div>
                <div className="text-[10px] text-muted-foreground">
                  Görsel TulparAI tarafından analiz edilecek (vision modeli)
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setPendingImage(null)}
                title="Resmi kaldır"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          )}

          {/* Hidden file input bound to the image button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) await handleFilePick(f);
              e.target.value = ""; // allow re-selecting the same file
            }}
          />

          <div className="relative flex items-end gap-2 bg-card border border-border rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all">
            <Button
              variant="ghost"
              size="icon"
              className="shrink-0 text-muted-foreground hover:text-primary rounded-xl h-10 w-10"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              title="Resim ekle (yemek, sakatlık, antrenman pozu)"
            >
              <ImageIcon className="w-5 h-5" />
            </Button>

            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                busy
                  ? "TulparAI düşünüyor..."
                  : pendingImage
                  ? "Görsel hakkında ne sormak istersin? (boş bırak = otomatik analiz)"
                  : "TulparAI'ye antrenmanın hakkında sor..."
              }
              disabled={busy}
              className="min-h-[40px] max-h-[200px] border-0 focus-visible:ring-0 px-0 py-2.5 resize-none bg-transparent"
              rows={1}
            />

            <div className="flex items-center gap-1 shrink-0 pb-0.5">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleVoice}
                disabled={busy}
                className={`rounded-xl h-10 w-10 ${
                  voiceState === "listening"
                    ? "bg-destructive/20 text-destructive animate-pulse"
                    : "text-muted-foreground hover:text-primary"
                }`}
                title={voiceState === "listening" ? "Dinleniyor — durdur" : "Sesli giriş (Türkçe)"}
              >
                <Mic className="w-5 h-5" />
              </Button>
              <Button
                size="icon"
                onClick={send}
                disabled={(!message.trim() && !pendingImage) || busy}
                className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl h-10 w-10 disabled:opacity-50"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
