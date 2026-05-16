import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "latin-ext"],
});

export const metadata: Metadata = {
  title: "TulparAI — Türk Sporcular için Doğrulanmış AI Antrenör",
  description:
    "Doğrulanmış, kişiselleştirilmiş AI antrenör + diyetisyen. " +
    "Türksat altyapısında, NVIDIA Nemotron ile.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="tr" className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <body suppressHydrationWarning className="min-h-full flex flex-col font-sans">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
