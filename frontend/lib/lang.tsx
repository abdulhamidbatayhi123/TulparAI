"use client";

import * as React from "react";

export type Lang = "tr" | "en";

const STORAGE_KEY = "tulparai.lang";

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
};

const LangContext = React.createContext<Ctx>({
  lang: "tr",
  setLang: () => {},
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = React.useState<Lang>("tr");

  // Hydrate from localStorage on mount (no SSR/CSR mismatch — render with default TR)
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "tr") setLangState(saved);
  }, []);

  const setLang = React.useCallback((l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, l);
    }
  }, []);

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang(): Ctx {
  return React.useContext(LangContext);
}

/**
 * Translation table. Keys live here so individual components can stay terse:
 *   const { t } = useCopy();
 *   <h1>{t.welcomeHeadline}</h1>
 */
const COPY = {
  tr: {
    // Brand
    brandTagline: "Spor Asistanı",
    verifiedAI: "Doğrulanmış AI",

    // Sidebar
    newChat: "Yeni Sohbet",
    yourProfile: "Profilin",
    editProfile: "Profili Düzenle",
    uploadDoc: "Doküman Yükle",
    loading: "Yükleniyor...",

    // Header tooltips
    toggleSidebar: "Kenar çubuğunu aç/kapat",
    clearChat: "Sohbeti temizle",
    toggleTheme: "Tema değiştir",
    toggleLanguage: "Dili değiştir",

    // Welcome screen
    welcomeEyebrow: "4 ajan · 8 araç · doğrulanmış",
    welcomeHeadline: "Bugün sana nasıl yardımcı olabilirim?",
    welcomeSub:
      "Her cümle bir tool çıktısıyla eşleşir, ardından bir Verifier modeli kaynaksız iddiaları siler. Halüsinasyon bir slogan değil — uygulanan bir kuraldır.",
    welcomeInfraLine: "NVIDIA Nemotron · Türksat altyapısı · Sıfır halüsinasyon",

    // Example prompts
    exNutritionLabel: "Beslenme",
    exNutritionText:  "Yarın akşam maç var, ne yemeliyim?",
    exRecoveryLabel:  "İyileşme",
    exRecoveryText:   "Maç sonrası iyileşme için en iyi besinler nedir?",
    exSleepLabel:     "Uyku",
    exSleepText:      "Performansım için günde kaç saat uyumalıyım?",
    exTrainingLabel:  "Antrenman",
    exTrainingText:   "Forvet olarak hız çalışmaları haftada kaç kez?",

    // Chat input
    inputPlaceholder: "TulparAI'ye antrenmanın hakkında sor…",
    inputPlaceholderImage: "Görsel hakkında ne sormak istersin? (boş bırak = otomatik analiz)",
    inputPlaceholderBusy: "TulparAI düşünüyor…",
    voiceTooltipIdle: "Sesli giriş (Türkçe)",
    voiceTooltipListening: "Dinleniyor — durdur",
    imageTooltip: "Resim ekle (yemek, sakatlık, antrenman pozu)",
    imagePreviewHint: "Görsel TulparAI tarafından analiz edilecek (vision modeli)",

    // Messages
    thinking: "Düşünüyorum",
    imageAttached: "[Resim eklendi]",
    autoImagePrompt: "Bu görseli analiz et",

    // Status footer
    backendOnline: (model: string) => `NVIDIA · ${model}`,
    backendOffline: "Backend Offline",
    backendChecking: "Kontrol ediliyor…",

    // Alerts
    imageOnly: "Sadece resim dosyaları desteklenir (jpg / png / webp).",
    imageTooBig: "Resim çok büyük (maks 5 MB).",
    voiceUnsupported: "Tarayıcınız sesli giriş desteklemiyor (Chrome / Edge / Safari önerilir).",
    errorPrefix: "⚠ Hata: ",
  },
  en: {
    // Brand
    brandTagline: "Sport Assistant",
    verifiedAI: "Verified AI",

    // Sidebar
    newChat: "New Chat",
    yourProfile: "Your profile",
    editProfile: "Edit profile",
    uploadDoc: "Upload document",
    loading: "Loading…",

    // Header tooltips
    toggleSidebar: "Toggle sidebar",
    clearChat: "Clear chat",
    toggleTheme: "Toggle theme",
    toggleLanguage: "Change language",

    // Welcome screen
    welcomeEyebrow: "4 agents · 8 tools · verified",
    welcomeHeadline: "How can I help you today?",
    welcomeSub:
      "Every sentence is tied to a real tool output, then a separate Verifier model strips any claim its source didn't support. Zero hallucinations is not a slogan — it's an enforced rule.",
    welcomeInfraLine: "NVIDIA Nemotron · Türksat-ready infra · Zero hallucinations",

    // Example prompts
    exNutritionLabel: "Nutrition",
    exNutritionText:  "I have a match tomorrow evening — what should I eat?",
    exRecoveryLabel:  "Recovery",
    exRecoveryText:   "Best foods for post-match recovery?",
    exSleepLabel:     "Sleep",
    exSleepText:      "How many hours of sleep do I need for peak performance?",
    exTrainingLabel:  "Training",
    exTrainingText:   "As a striker, how often per week should I do speed work?",

    // Chat input
    inputPlaceholder: "Ask TulparAI about your training…",
    inputPlaceholderImage: "What would you like to know about the image? (empty = auto-analyze)",
    inputPlaceholderBusy: "TulparAI is thinking…",
    voiceTooltipIdle: "Voice input",
    voiceTooltipListening: "Listening — stop",
    imageTooltip: "Attach image (meal, injury, training pose)",
    imagePreviewHint: "TulparAI will analyse this image (vision model)",

    // Messages
    thinking: "Thinking",
    imageAttached: "[Image attached]",
    autoImagePrompt: "Analyse this image",

    // Status footer
    backendOnline: (model: string) => `NVIDIA · ${model}`,
    backendOffline: "Backend offline",
    backendChecking: "Checking…",

    // Alerts
    imageOnly: "Only image files supported (jpg / png / webp).",
    imageTooBig: "Image too large (max 5 MB).",
    voiceUnsupported: "Your browser doesn't support voice input (Chrome / Edge / Safari recommended).",
    errorPrefix: "⚠ Error: ",
  },
} as const;

export type Copy = (typeof COPY)["tr"];

export function useCopy(): Copy {
  const { lang } = useLang();
  return COPY[lang];
}
