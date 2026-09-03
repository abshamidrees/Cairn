import createMDX from "@next/mdx";
import type { NextConfig } from "next";
import remarkGfm from "remark-gfm";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  pageExtensions: ["ts", "tsx", "mdx"],
};

// Without gfm, a markdown table renders as a paragraph of pipes.
const withMDX = createMDX({
  options: { remarkPlugins: [remarkGfm] },
});

export default withMDX(nextConfig);
