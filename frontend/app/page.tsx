"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
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
import { useLang, useCopy } from "@/lib/lang";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { ProfileDialog } from "@/components/ProfileDialog";
import { UploadDialog } from "@/components/UploadDialog";
import { AgentBadges } from "@/components/AgentBadges";
import { ToolCallChip } from "@/components/ToolCallChip";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { SourcesPanel } from "@/components/SourcesPanel";
import { HowIAnsweredDrawer } from "@/components/HowIAnsweredDrawer";

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

// Single-user app: one default athlete identity, overridable at build time.
// The profile data behind this ID is what onboarding fills in.
const ATHLETE_ID =
  process.env.NEXT_PUBLIC_DEFAULT_ATHLETE || "ahmet";

export default function Home() {
  const { lang } = useLang();
  const c = useCopy();

  const [message, setMessage] = useState("");
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [modelInfo, setModelInfo] = useState<string>("");
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [personalDocCount, setPersonalDocCount] = useState<number>(0);
  const [pendingImage, setPendingImage] = useState<{ b64: string; preview: string; name: string } | null>(null);
  const [voiceState, setVoiceState] = useState<"idle" | "listening">("idle");
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

  // Load profile + personal doc count (re-runs after profile edits via onSaved)
  const refreshProfile = () => {
    getProfile(ATHLETE_ID).then(setProfile).catch(() => setProfile(null));
    listPersonalDocs(ATHLETE_ID)
      .then((r) => setPersonalDocCount(r.files?.length || 0))
      .catch(() => setPersonalDocCount(0));
  };
  useEffect(() => { refreshProfile(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

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

  const toggleVoice = () => {
    if (voiceState === "listening") {
      voiceRef.current?.stop();
      setVoiceState("idle");
      return;
    }
    if (!isVoiceSupported()) {
      alert(c.voiceUnsupported);
      return;
    }
    setVoiceState("listening");
    voiceRef.current = startVoice({
      lang: lang === "en" ? "en-US" : "tr-TR",
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
      { role: "user", text: text || c.imageAttached },
      { role: "assistant", text: "", liveTools: [] },
    ]);

    const imageBase64 = pendingImage?.b64;
    setPendingImage(null);

    cancelRef.current = openChatStream(
      {
        athlete_id: ATHLETE_ID,
        message: text || c.autoImagePrompt,
        language: lang,
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
              text: `${c.errorPrefix}${ev.message}`,
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
      alert(c.imageOnly);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert(c.imageTooBig);
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
            <div className="relative w-9 h-9 rounded-lg overflow-hidden ring-1 ring-border bg-white flex items-center justify-center shadow-sm">
              {/* The Pegasus mark — red on white, works on both themes thanks to the small white card. */}
              <Image
                src="/logo.jpeg"
                alt="TulparAI logosu"
                width={36}
                height={36}
                className="object-contain"
                priority
              />
            </div>
            <h1 className="font-display text-2xl font-medium tracking-tight text-foreground whitespace-nowrap leading-none">
              Tulpar<span className="italic text-primary">AI</span>
            </h1>
          </div>
        </div>

        <div className="p-4 flex-1 overflow-y-auto space-y-5">
          <Button
            className="w-full justify-start gap-2"
            variant="outline"
            onClick={clearChat}
          >
            <Plus className="w-4 h-4" />
            {c.newChat}
          </Button>

          {/* Single-user profile card.
              Onboarding fills these fields conversationally on first chat. */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {c.yourProfile}
            </h3>
            <div className="p-3 rounded-lg bg-background/60 border border-border space-y-2.5">
              <div>
                <h4 className="text-sm font-semibold text-foreground leading-tight">
                  {(profile?.name as string) || "—"}
                </h4>
                <p className="text-xs text-muted-foreground capitalize mt-0.5">
                  {profile ? (
                    <>
                      {(profile.sport as string) || "—"}
                      {(() => {
                        const sp = profile.sport_profile as Record<string, unknown> | undefined;
                        const detail = sp?.position || sp?.weight_class;
                        return detail ? ` · ${detail}` : "";
                      })()}
                      {(profile.training_phase as string)
                        ? ` · ${profile.training_phase as string}`
                        : ""}
                    </>
                  ) : c.loading}
                </p>
                {personalDocCount > 0 && (
                  <p className="text-[10px] text-muted-foreground/70 mt-1 font-mono">
                    {personalDocCount} {lang === "tr" ? "kişisel doküman indekslendi" : "personal docs indexed"}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <ProfileDialog athleteId={ATHLETE_ID} onSaved={refreshProfile}>
                  <Button variant="secondary" size="sm" className="text-xs h-8 gap-1.5">
                    <UserCog className="w-3.5 h-3.5" />
                    {lang === "tr" ? "Düzenle" : "Edit"}
                  </Button>
                </ProfileDialog>
                <UploadDialog athleteId={ATHLETE_ID} onUploaded={refreshProfile}>
                  <Button variant="secondary" size="sm" className="text-xs h-8 gap-1.5">
                    <UploadCloud className="w-3.5 h-3.5" />
                    {lang === "tr" ? "Yükle" : "Upload"}
                  </Button>
                </UploadDialog>
              </div>
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
            ? c.backendOnline(modelInfo)
            : backendOnline === false
            ? c.backendOffline
            : c.backendChecking}
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
              aria-label={c.toggleSidebar}
            >
              <PanelLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-lg font-medium tracking-tight text-foreground">
                TulparAI
              </span>
              <span className="hidden sm:inline text-[11px] tracking-widest uppercase text-muted-foreground">
                {c.brandTagline}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {/* Verified-AI badge — pitch shorthand for the verifier guardrail */}
            <span
              className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-500"
              title={`${c.verifiedAI} · ${lang === "tr" ? "her [Tx] iddiası kaynak ile eşleştirilir" : "every [Tx] claim is matched to its source"}`}
            >
              <ShieldCheck className="w-3 h-3" />
              {c.verifiedAI}
            </span>
            <LanguageToggle />
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon"
              title={c.clearChat}
              className="text-muted-foreground hover:text-destructive"
              onClick={clearChat}
              aria-label={c.clearChat}
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
              {/* Pegasus mark — the brand at hero scale */}
              <div className="relative mb-6 motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95 motion-safe:duration-700">
                <div className="relative w-24 h-24 rounded-2xl overflow-hidden ring-1 ring-border bg-white flex items-center justify-center shadow-sm">
                  <Image
                    src="/logo.jpeg"
                    alt="TulparAI"
                    width={96}
                    height={96}
                    className="object-contain"
                    priority
                  />
                </div>
                {/* Subtle glow ring behind the mark */}
                <div className="absolute inset-0 -z-10 rounded-2xl bg-primary/20 blur-2xl motion-safe:animate-pulse" />
              </div>

              {/* Eyebrow tag */}
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-primary">
                <Sparkles className="w-3 h-3" />
                <span>{c.welcomeEyebrow}</span>
              </div>

              {/* Display headline — invites the user, not a slogan. Fraunces handles
                  Turkish glyphs (ş, ç, ğ) cleanly. */}
              <h2 className="font-display text-5xl md:text-6xl font-medium tracking-tight text-foreground text-center leading-[1.05] mb-5 max-w-2xl">
                {c.welcomeHeadline}
              </h2>

              <p className="text-muted-foreground text-center text-[15px] md:text-base mb-10 max-w-xl leading-relaxed">
                {c.welcomeSub}
              </p>

              {/* Example prompts — quick-starts that hit real sport-KB topics. */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                {[
                  { icon: Apple,      label: c.exNutritionLabel, text: c.exNutritionText },
                  { icon: HeartPulse, label: c.exRecoveryLabel,  text: c.exRecoveryText  },
                  { icon: Moon,       label: c.exSleepLabel,     text: c.exSleepText     },
                  { icon: Activity,   label: c.exTrainingLabel,  text: c.exTrainingText  },
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
                {c.welcomeInfraLine}
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
                            {c.thinking}
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
                  {c.imagePreviewHint}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setPendingImage(null)}
                title={lang === "tr" ? "Resmi kaldır" : "Remove image"}
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
              title={c.imageTooltip}
            >
              <ImageIcon className="w-5 h-5" />
            </Button>

            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                busy
                  ? c.inputPlaceholderBusy
                  : pendingImage
                  ? c.inputPlaceholderImage
                  : c.inputPlaceholder
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
                title={voiceState === "listening" ? c.voiceTooltipListening : c.voiceTooltipIdle}
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
