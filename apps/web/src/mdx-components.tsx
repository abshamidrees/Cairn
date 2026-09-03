import type { MDXComponents } from "mdx/types";

import { CodeBlock } from "@/components/code-block";

/**
 * How MDX renders inside Cairn's type system.
 *
 * Nothing here names a font family: the tokens map display, sans and mono onto
 * roles, so a docs page inherits the same scale as the rest of the product.
 */
export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: ({ children }) => (
      <h1 className="text-[length:var(--text-section)] leading-[var(--text-section-lead)] tracking-[var(--text-section-track)]">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2
        id={slug(children)}
        className="mt-14 scroll-mt-24 text-[1.5rem] tracking-[-0.015em] text-graphite"
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 id={slug(children)} className="mt-10 scroll-mt-24 text-[1.125rem] text-graphite">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="mt-4 max-w-[42rem] text-[length:var(--text-lead)] leading-[var(--text-lead-lead)] text-slate">
        {children}
      </p>
    ),
    ul: ({ children }) => (
      <ul className="mt-4 max-w-[42rem] list-disc space-y-2 pl-5 text-slate">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="mt-4 max-w-[42rem] list-decimal space-y-2 pl-5 text-slate">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    strong: ({ children }) => <strong className="font-medium text-graphite">{children}</strong>,
    a: ({ href, children }) => (
      <a href={href} className="text-lapis underline underline-offset-[1px]">
        {children}
      </a>
    ),
    table: ({ children }) => (
      <div className="mt-6 overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.8125rem]">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="border-b border-seam py-2 pr-6 text-left text-[0.6875rem] font-normal uppercase tracking-[0.13em] text-slate">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border-b border-seam py-2 pr-6 align-top text-slate">{children}</td>
    ),
    code: ({ children }) => (
      <code className="font-mono text-[0.8125rem] text-graphite">{children}</code>
    ),
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    blockquote: ({ children }) => (
      <blockquote className="mt-6 max-w-[42rem] border-l-2 border-seam pl-5 text-slate">
        {children}
      </blockquote>
    ),
    ...components,
  };
}

function slug(children: React.ReactNode): string {
  return String(children)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
