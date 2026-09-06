import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Firsthand",
    short_name: "Firsthand",
    description: "A memory-native trust layer for agent commerce.",
    start_url: "/",
    display: "standalone",
    background_color: "#F2F3EF",
    theme_color: "#F2F3EF",
    icons: [
      { src: "/favicon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/favicon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
