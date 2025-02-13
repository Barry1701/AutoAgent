import React from 'react';
import './KeyFeatures.css';

export function KeyFeatures() {
  return (
    <div className="key-features">
      <div className="intro-image">
        <img src="/img/metachain-intro-final.svg" alt="MetaChain Introduction" />
      </div>
      <h2 className="features-title">Key Features</h2>
      <ul className="features-list">
        <li>
          <span className="feature-icon">🏆</span>
          <div className="feature-content">
            <strong>Top Performer on the GAIA Benchmark</strong>
            <p>
              MetaChain has ranked the <span className="highlight">#1</span> spot among open-sourced methods, delivering comparable performance to <span className="highlight">OpenAI's Deep Research</span>.
            </p>
          </div>
        </li>

        <li>
          <span className="feature-icon">📚</span>
          <div className="feature-content">
            <strong>Agentic-RAG with Native Self-Managing Vector Database</strong>
            <p>
              MetaChain equipped with a native self-managing vector database, outperforms industry-leading solutions like <span className="highlight">LangChain</span>.
            </p>
          </div>
        </li>

        <li>
          <span className="feature-icon">✨</span>
          <div className="feature-content">
            <strong>Agent and Workflow Create with Ease</strong>
            <p>
              MetaChain leverages natural language to effortlessly build ready-to-use <span className="highlight">tools</span>, <span className="highlight">agents</span> and <span className="highlight">workflows</span> - no coding required.
            </p>
          </div>
        </li>

        <li>
          <span className="feature-icon">🌐</span>
          <div className="feature-content">
            <strong>Universal LLM Support</strong>
            <p>
              MetaChain seamlessly integrates with <span className="highlight">A Wide Range</span> of LLMs (OpenAI, Anthropic, Deepseek, vLLM, Grok, Huggingface).
            </p>
          </div>
        </li>

        <li>
          <span className="feature-icon">🔀</span>
          <div className="feature-content">
            <strong>Flexible Interaction</strong>
            <p>
              Benefit from support for both <span className="highlight">function-calling</span> and <span className="highlight">ReAct</span> interaction modes.
            </p>
          </div>
        </li>

        <li>
          <span className="feature-icon">🤖</span>
          <div className="feature-content">
            <strong>Dynamic, Extensible, Lightweight</strong>
            <p>
              MetaChain is your <span className="highlight">Personal AI Assistant</span>, designed to be dynamic, extensible, customized, and lightweight.
            </p>
          </div>
        </li>
      </ul>
    </div>
  );
} 