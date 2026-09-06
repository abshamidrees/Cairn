import type { MDXComponents } from "mdx/types";
import { isValidElement, type ReactNode } from "react";

import { CodeBlock } from "@/components/code-block";

/**
 * Take the text out of the `<code>` that MDX puts inside every `<pre>`.
 *
 * Without this the block nests two code elements, and the inner one carries the
 * inline rule's graphite. Graphite on basalt is #16181A on #101214, a contrast
 * ratio of about 1.05 to 1, so every fenced block in the docs rendered as an
 * empty dark panel. It looked like a styling choice rather than unreadable text,
 * which is why it survived a build, a deploy and several passes over the page.
 */
function unwrapCode(children: ReactNode): ReactNode {
  // Not a check for type === "code": by the time this runs MDX has already
  // swapped in the component above, so the element's type is that function and
  // never the tag name. A fenced block always holds exactly one element, so
  // unwrapping one is the same test with none of the fragility.
  if (isValidElement<{ children?: ReactNode }>(children)) {
    return children.props.children;
  }
  return children;
}

/**
 * How MDX renders inside Firsthand's type system.
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
    // Inline code only. A fenced block arrives as <pre><code>, and `pre` below
    // unwraps that inner element before this colour can land on the dark panel.
    code: ({ children }) => (
      <code className="font-mono text-[0.8125rem] text-graphite">{children}</code>
    ),
    pre: ({ children }) => <CodeBlock>{unwrapCode(children)}</CodeBlock>,
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
