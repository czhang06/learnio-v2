import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Mono, Instrument_Sans } from "next/font/google";
import "./globals.css";
import Providers from "@/lib/account";

// Interface and question text. The width axis gives the condensed headings.
const ui = Instrument_Sans({ subsets: ["latin"], axes: ["wdth"], variable: "--font-ui", display: "swap" });
// SQL and other code lifted from an exam.
const code = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-code", display: "swap" });

export const metadata: Metadata = {
  title: "LearnIO",
  description: "Build a question bank from past exams and generate practice exams.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f6f8" },
    { media: "(prefers-color-scheme: dark)", color: "#111216" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${ui.variable} ${code.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
