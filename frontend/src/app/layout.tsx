import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HiringAgent AI — Premium Resume Screening",
  description: "Unbiased resume screening pipeline with verified GitHub enrichment, redacted PII, and real-time streaming LLM evaluation reports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#09090b] text-white">
        {children}
      </body>
    </html>
  );
}
