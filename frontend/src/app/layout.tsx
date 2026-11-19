import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AetherPravah — Build AI that handles money better",
  description:
    "The world's first Causal Financial Organism. Treating your money like a living organism that predicts liquidity singularities and forges liquidity wormholes.",
  keywords: [
    "AetherPravah",
    "Causal AI",
    "Financial Organism",
    "GST Accrual Trap",
    "MSME Finance",
    "Liquidity Wormhole",
    "Money Health Genome",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="bg-darkbg text-slate-100 antialiased selection:bg-brand-500/30 selection:text-white">
        {children}
      </body>
    </html>
  );
}
