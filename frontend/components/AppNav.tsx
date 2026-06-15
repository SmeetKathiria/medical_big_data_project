"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ClipboardCheck, Search } from "lucide-react";

const nav = [
  { href: "/", label: "Dashboard", icon: Activity },
  { href: "/evidence", label: "Intel Lens", icon: Search },
  { href: "/evals", label: "Signal Quality", icon: ClipboardCheck },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav className="-mx-1 flex w-full max-w-full flex-wrap items-center gap-1.5 px-1 sm:w-auto">
      {nav.map((item) => {
        const Icon = item.icon;
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-full border px-4 text-[12px] font-medium transition hover:-translate-y-0.5 ${
              active
                ? "border-green bg-green text-panel shadow-[0_18px_32px_-24px_rgba(28,50,45,0.9)]"
                : "border-line/70 bg-white/45 text-muted hover:border-green/40 hover:bg-white/75 hover:text-ink"
            }`}
          >
            <Icon size={16} strokeWidth={1.8} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
