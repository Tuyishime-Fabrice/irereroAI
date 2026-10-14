import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import type { ReactNode } from "react";

import { ProvenanceProvider } from "@/components/shell/ProvenanceProvider";
import { SessionProvider } from "@/components/shell/SessionProvider";
import { TourOverlay } from "@/components/tour/TourOverlay";

import "./globals.css";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("meta");
  return {
    title: { default: "IrereroAI", template: "%s · IrereroAI" },
    description: t("description"),
  };
}

export const viewport: Viewport = { themeColor: "#1E1B18", width: "device-width", initialScale: 1 };

// Applies the projector theme before first paint so the page does not flash.
const THEME_SCRIPT = `try{if(localStorage.getItem("irerero_theme")==="projector")document.documentElement.dataset.theme="projector"}catch(e){}`;

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  return (
    <html
      lang={locale}
      className={`${fraunces.variable} ${plexSans.variable} ${plexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-paper">
        <NextIntlClientProvider>
          <SessionProvider>
            <ProvenanceProvider>
              {children}
              <TourOverlay />
            </ProvenanceProvider>
          </SessionProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
