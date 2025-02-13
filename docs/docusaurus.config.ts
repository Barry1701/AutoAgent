import type * as Preset from "@docusaurus/preset-classic";
import type { Config } from "@docusaurus/types";
import { themes as prismThemes } from "prism-react-renderer";

const config: Config = {
  title: "MetaChain",
  tagline: "Fully-Automated & Zero-Code LLM Agent Framework",
  favicon: "img/metachain_logo.svg",

  // Set the production url of your site here
  url: "https://metachain-ai.github.io",
  baseUrl: "/",

  // GitHub pages deployment config.
  organizationName: "metachain-ai",
  projectName: "metachain-ai.github.io",
  trailingSlash: false,
  deploymentBranch: "main",

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],
  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "docs",
          sidebarPath: "./sidebars.ts",
          exclude: [
            "**/*.test.{js,jsx,ts,tsx}",
            "**/__tests__/**",
          ],
        },
        blog: {
          showReadingTime: true,
        },
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    image: "img/docusaurus.png",
    navbar: {
      title: "MetaChain",
      logo: {
        alt: "MetaChain",
        src: "img/metachain_logo.svg",
      },
      items: [
        {
          type: "docSidebar",
          sidebarId: "docsSidebar",
          position: "left",
          label: "Docs",
        },
        {
          href: "https://github.com/HKUDS/MetaChain",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    prism: {
      theme: prismThemes.oneLight,
      darkTheme: prismThemes.oneDark,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
