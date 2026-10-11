import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Mono, Schibsted_Grotesk, STIX_Two_Text } from "next/font/google";
import "./globals.css";

// Interface text.
const ui = Schibsted_Grotesk({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
// Question text: a scientific text face, so exam prose and its ∃ ∀ ∈ ⇒ sit in one design.
const exam = STIX_Two_Text({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-exam",
  display: "swap",
});
// SQL and other code lifted from an exam.
const code = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-code", display: "swap" });

export const metadata: Metadata = {
  title: "LearnIO",
  description: "Build a question bank from past exams and generate practice exams.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${ui.variable} ${exam.variable} ${code.variable}`}>
      <body>{children}</body>
    </html>
  );
}
