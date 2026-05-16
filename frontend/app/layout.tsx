import type { Metadata } from "next";
import { Geist, Geist_Mono, Fraunces } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

// Body — Geist Sans (Vercel, modern geometric, full latin-ext for Turkish chars).
const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

// Mono — Geist Mono (citation markers, tool names, latency numerals).
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

// Display / heading — Fraunces (variable serif with athletic curves; editorial
// gravitas appropriate for a ministry-grade product, characterful enough to
// avoid the generic-AI-clone look).
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin", "latin-ext"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "TulparAI — Türk Sporcular için Doğrulanmış AI Antrenör",
  description:
    "Doğrulanmış, kişiselleştirilmiş AI antrenör + diyetisyen. " +
    "Türksat altyapısında, NVIDIA Nemotron ile. Halüsinasyon yok, kaynak gösterir.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="tr"
      className={`${geist.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body suppressHydrationWarning className="min-h-full flex flex-col font-sans">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
