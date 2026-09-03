/** The docs IA. One source, so the sidebar and the search cannot disagree. */

export interface DocPage {
  readonly title: string;
  readonly href: string;
}

export interface DocGroup {
  readonly label: string;
  readonly pages: readonly DocPage[];
}

export const DOCS: readonly DocGroup[] = [
  {
    label: "Start",
    pages: [
      { title: "What Cairn is", href: "/docs" },
      { title: "Quickstart", href: "/docs/quickstart" },
      { title: "Ask about a counterparty", href: "/docs/ask" },
    ],
  },
  {
    label: "Concepts",
    pages: [
      { title: "Observation", href: "/docs/concepts/observation" },
      { title: "Dossier", href: "/docs/concepts/dossier" },
      { title: "Grounding", href: "/docs/concepts/grounding" },
      { title: "Verdict and basis", href: "/docs/concepts/verdict" },
      { title: "Standing", href: "/docs/concepts/standing" },
      { title: "Reviewer weight", href: "/docs/concepts/reviewer-weight" },
    ],
  },
  {
    label: "Memory",
    pages: [
      { title: "The five tiers", href: "/docs/memory/tiers" },
      { title: "How Cairn promotes and decays", href: "/docs/memory/promotion" },
      { title: "The deletion test", href: "/docs/memory/deletion-test" },
    ],
  },
  {
    label: "API",
    pages: [
      { title: "Lookup", href: "/docs/api/lookup" },
      { title: "Observations", href: "/docs/api/observations" },
      { title: "Attestations", href: "/docs/api/attestations" },
      { title: "Webhooks", href: "/docs/api/webhooks" },
    ],
  },
  {
    label: "Partners",
    pages: [
      { title: "Base", href: "/docs/partners/base" },
      { title: "Virtuals ACP", href: "/docs/partners/acp" },
    ],
  },
];

export const ALL_PAGES: readonly DocPage[] = DOCS.flatMap((group) => group.pages);
