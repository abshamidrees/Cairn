"use client";

import { useEffect, useState } from "react";

/** The headings on this page, read from the rendered document. */
export function PageToc() {
  const [headings, setHeadings] = useState<readonly { id: string; text: string }[]>([]);

  useEffect(() => {
    const found = [...document.querySelectorAll("main h2[id], main h3[id]")].map((node) => ({
      id: node.id,
      text: node.textContent ?? "",
    }));
    setHeadings(found);
  }, []);

  if (headings.length === 0) return <div aria-hidden />;

  return (
    <nav aria-label="On this page" className="hidden lg:sticky lg:top-8 lg:block lg:self-start">
      <p className="font-mono text-[0.6875rem] uppercase tracking-[0.13em] text-slate">
        On this page
      </p>
      <ul className="mt-3 space-y-2">
        {headings.map((heading) => (
          <li key={heading.id}>
            <a href={`#${heading.id}`} className="text-[0.8125rem] text-slate hover:text-graphite">
              {heading.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
