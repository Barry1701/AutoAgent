import React from 'react';
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Heading from "@theme/Heading";
import { KeyFeatures } from "../KeyFeatures/KeyFeatures";
import Translate from '@docusaurus/Translate';
import "../../css/homepageHeader.css";

export function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <div className="homepage-header">
      <div className="header-content">
        <Heading as="h1" className="header-title">
          {siteConfig.title}
        </Heading>

        <p className="header-subtitle">{siteConfig.tagline}</p>

        <div className="social-links">
          <div className="link-row">
            <a href="https://metachain-ai.github.io" className="link-button project">
              <span className="icon">📋</span>
              <span className="text">PROJECT</span>
              <span className="highlight">PAGE</span>
            </a>
            <a href="https://join.slack.com/t/metachain-workspace/shared_invite/zt-2zibtmutw-v7xOJObBf9jE2w3x7nctFQ" className="link-button slack">
              <span className="icon">💬</span>
              <span className="text">SLACK</span>
              <span className="highlight">JOIN US</span>
            </a>
            <a href="https://discord.gg/z68KRvwB" className="link-button discord">
              <span className="icon">🎮</span>
              <span className="text">DISCORD</span>
              <span className="highlight">JOIN US</span>
            </a>
          </div>
          <div className="link-row">
            <a href="https://metachain-ai.github.io/docs" className="link-button docs">
              <span className="icon">📚</span>
              <span className="text">DOCUMENTATION</span>
            </a>
            <a href="https://arxiv.org/abs/2502.05957" className="link-button paper">
              <span className="icon">📄</span>
              <span className="text">PAPER ON ARXIV</span>
            </a>
            <a href="https://gaia-benchmark-leaderboard.hf.space/" className="link-button benchmark">
              <span className="icon">📊</span>
              <span className="text">GAIA BENCHMARK</span>
            </a>
          </div>
        </div>

        <KeyFeatures />
      </div>
    </div>
  );
}
