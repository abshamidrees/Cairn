"use client";

import { usePathname } from "next/navigation";

import { DOCS } from "@/lib/docs";

/** Mono uppercase group labels, the current page marked. */
export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <nav aria-label="Documentation" className="lg:sticky lg:top-8 lg:self-start">
      {DOCS.map((group) => (
        <div key={group.label} className="mb-8">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
            {group.label}
          </p>
          <ul className="mt-3 space-y-2">
            {group.pages.map((page) => {
              const active = pathname === page.href;
              return (
                <li key={page.href}>
                  <a
                    href={page.href}
                    aria-current={active ? "page" : undefined}
                    className={`text-[0.9375rem] ${
                      active ? "text-graphite" : "text-slate hover:text-graphite"
                    }`}
                  >
                    {page.title}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
