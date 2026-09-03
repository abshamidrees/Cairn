import type { ReactNode } from "react";

import { Nav } from "@/components/shell";
import { DocsSidebar } from "@/components/docs-sidebar";
import { PageToc } from "@/components/page-toc";

/**
 * The docs shell: mono uppercase group labels on the left, the page in the
 * middle, its own headings on the right. Cmd+K is in the nav, as everywhere.
 */
export default function DocsLayout({ children }: { readonly children: ReactNode }) {
  return (
    <>
      <Nav />
      <div className="mx-auto grid max-w-[78rem] gap-10 px-6 py-12 lg:grid-cols-[13rem_1fr_12rem]">
        <DocsSidebar />
        <main className="min-w-0">{children}</main>
        <PageToc />
      </div>
    </>
  );
}
