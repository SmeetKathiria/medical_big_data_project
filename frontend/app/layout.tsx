import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { Activity } from "lucide-react";
import { AppNav } from "../components/AppNav";

export const metadata: Metadata = {
  title: "MedIntel",
  description: "Clinical evidence review across CMS policy, FDA labeling, and PubMed literature"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="sticky top-0 z-20 border-b border-green/10 bg-panel/80 backdrop-blur-xl">
            <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-10">
              <Link href="/" className="group flex shrink-0 items-center gap-3">
                <span className="flex size-10 items-center justify-center rounded-full bg-green text-[11px] font-semibold uppercase text-panel shadow-[0_18px_32px_-22px_rgba(28,50,45,0.9)] transition group-hover:-translate-y-0.5">
                  MI
                </span>
                <span>
                  <span className="block font-serif text-2xl font-normal leading-none text-ink">MedIntel</span>
                  <span className="block text-[10px] font-semibold uppercase text-muted tracking-[0.18em]">clinical evidence review</span>
                </span>
              </Link>
              <div className="flex min-w-0 flex-col items-start gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <span className="status-pill">
                  <Activity size={13} />
                  System ready
                </span>
                <AppNav />
              </div>
            </div>
          </header>
          <main className="page-shell">{children}</main>
        </div>
      </body>
    </html>
  );
}
