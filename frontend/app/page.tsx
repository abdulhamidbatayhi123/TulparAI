"use client";

import { useEffect, useRef, useState } from "react";
import {
  Plus, UserCog, UploadCloud, PanelLeft,
  BookOpen, Trash2, Image as ImageIcon, Mic, Send,
  Thermometer, Pill, Moon, Flame, Zap, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  openChatStream, getHealth, fileToBase64,
  type ChatStreamEvent, type Source, type ToolCall,
} from "@/lib/api";
import { startVoice, isVoiceSupported, type VoiceHandle } from "@/lib/speech";
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

const ATHLETE_ID =
  process.env.NEXT_PUBLIC_DEFAULT_ATHLETE || "ahmet";
const LANGUAGE: "tr" | "en" =
  (process.env.NEXT_PUBLIC_DEFAULT_LANG as "tr" | "en") || "tr";

export default function Home() {
  const [message, setMessage] = useState("");
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [currentStep, setCurrentStep] = useState<number | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [modelInfo, setModelInfo] = useState<string>("");
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
        athlete_id: ATHLETE_ID,
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
        className={`${isSidebarOpen ? "w-64" : "w-0"} transition-all duration-300 ease-in-out flex flex-col border-r border-border bg-card/30 backdrop-blur-md overflow-hidden shrink-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
              T
            </div>
            <h1 className="font-bold text-xl tracking-tight text-foreground whitespace-nowrap">
              Tulpar<span className="text-primary">AI</span>
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
            New Conversation
          </Button>

          {/* Athlete Profile */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Athlete Profile
            </h3>
            <div className="p-3 rounded-lg bg-background border border-border">
              <div className="mb-2">
                <h4 className="text-sm font-semibold text-foreground">
                  Ahmet Yılmaz
                </h4>
                <p className="text-xs text-muted-foreground">
                  Football · Striker · Süper Lig
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                className="w-full text-xs h-8 gap-2"
                disabled
              >
                <UserCog className="w-3.5 h-3.5" />
                Edit Profile (soon)
              </Button>
            </div>
          </div>

          {/* Knowledge Base */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Knowledge Base
            </h3>
            <div className="flex gap-2">
              <div className="flex-1 p-2 rounded-lg bg-background border border-border flex flex-col items-center">
                <span className="text-lg font-bold text-foreground">4</span>
                <span className="text-[10px] text-muted-foreground uppercase">Sports</span>
              </div>
              <div className="flex-1 p-2 rounded-lg bg-background border border-border flex flex-col items-center">
                <span className="text-lg font-bold text-foreground">6</span>
                <span className="text-[10px] text-muted-foreground uppercase">Tools</span>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="w-full text-xs h-8 gap-2"
              disabled
            >
              <UploadCloud className="w-3.5 h-3.5" />
              Upload Document (soon)
            </Button>
          </div>

          {/* Recents */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Recents
            </h3>
            <div className="text-sm text-muted-foreground text-center py-4">
              {messages.length > 0
                ? `${Math.floor(messages.length / 2)} message(s) in this chat`
                : "No recent chats"}
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
      <main className="flex-1 flex flex-col h-full min-w-0">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-border bg-background/50 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!isSidebarOpen)}
              className="text-muted-foreground hover:text-foreground"
            >
              <PanelLeft className="w-5 h-5" />
            </Button>
            <div className="font-medium text-foreground">
              TulparAI Sports Assistant
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              title="View Sources"
              className="text-muted-foreground hover:text-foreground"
            >
              <BookOpen className="w-5 h-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              title="Clear Chat"
              className="text-muted-foreground hover:text-destructive"
              onClick={clearChat}
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col">
          {messages.length === 0 ? (
            /* Welcome Screen */
            <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full">
              <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-6 border border-primary/30">
                <Zap className="w-8 h-8 text-primary" />
              </div>
              <h2 className="text-3xl font-bold text-foreground mb-3 text-center">
                Welcome to <span className="text-primary">TulparAI</span>
              </h2>
              <p className="text-muted-foreground text-center mb-10 max-w-lg">
                Doğrulanmış kaynaklarla cevap veren AI antrenör. Halüsinasyon yok —
                her iddia [Tx] etiketiyle kanıtlanır.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                {[
                  { icon: Thermometer, text: "Yarın akşam maç var, ne yemeliyim?" },
                  { icon: Pill, text: "Maç sonrası iyileşme için en iyi besinler nedir?" },
                  { icon: Moon, text: "Performansım için günde kaç saat uyumalıyım?" },
                  { icon: Flame, text: "Forvet olarak hız çalışmaları haftada kaç kez?" },
                ].map((item, i) => (
                  <div
                    key={i}
                    onClick={() => setQuery(item.text)}
                    className="p-4 rounded-xl border border-border bg-card/50 hover:bg-card hover:border-primary/50 cursor-pointer transition-all flex items-start gap-3 group"
                  >
                    <item.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary mt-0.5 shrink-0" />
                    <p className="text-sm text-foreground">{item.text}</p>
                  </div>
                ))}
              </div>
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
