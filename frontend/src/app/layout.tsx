import type { Metadata } from "next";
import "@/styles/globals.css";
import { Providers } from "@/components/layout/Providers";

export const metadata: Metadata = {
  title: "AutoShorts — Automatyczne generowanie krótkich filmów",
  description: "Platforma do automatycznego tworzenia faceless short-video na TikTok, YouTube Shorts i Instagram Reels",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
