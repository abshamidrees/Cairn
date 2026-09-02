import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { fontVars } from "@/fonts";
import { canonicalFor } from "@/lib/host";

// tokens.css is the only source of colour, spacing, radius and motion, and it
// imports Tailwind itself. There is deliberately no globals.css to accumulate
// values that escape the token file.
import "@/styles/tokens.css";

export const metadata: Metadata = {
  metadataBase: new URL(canonicalFor("landing")),
  title: { default: "Cairn", template: "%s · Cairn" },
  description:
    "Cairn is a memory-native trust layer for agent commerce. Every verdict points at the observations it came from.",
  alternates: { canonical: canonicalFor("landing") },
  openGraph: {
    title: "Cairn",
    description: "A record, not a rating.",
    url: canonicalFor("landing"),
    siteName: "Cairn",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#F2F3EF",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={fontVars}>
      <body>{children}</body>
    </html>
  );
}
