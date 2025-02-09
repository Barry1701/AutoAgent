<a name="readme-top"></a>

<div align="center">
  <img src="./assets/metachain_logo.svg" alt="Logo" width="200">
  <h1 align="center">MetaChain: Fully-Automated, Zero-Code Agent Framework</h1>
</div>



<div align="center">
  <a href="https://metachain-ai.github.io"><img src="https://img.shields.io/badge/Project-Page-blue?style=for-the-badge&color=FFE165&logo=homepage&logoColor=white" alt="Credits"></a>
  <a href="https://join.slack.com/t/metachain-workspace/shared_invite/zt-2zibtmutw-v7xOJObBf9jE2w3x7nctFQ"><img src="https://img.shields.io/badge/Slack-Join%20Us-red?logo=slack&logoColor=white&style=for-the-badge" alt="Join our Slack community"></a>
  <a href="https://discord.gg/z68KRvwB"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <br/>
  <a href="https://metachain-ai.github.io/docs"><img src="https://img.shields.io/badge/Documentation-000?logo=googledocs&logoColor=FFE165&style=for-the-badge" alt="Check out the documentation"></a>
  <a href="#"><img src="https://img.shields.io/badge/Paper%20on%20Arxiv-000?logoColor=FFE165&logo=arxiv&style=for-the-badge" alt="Paper"></a>
  <a href="https://gaia-benchmark-leaderboard.hf.space/"><img src="https://img.shields.io/badge/GAIA%20Benchmark-000?logoColor=FFE165&logo=huggingface&style=for-the-badge" alt="Evaluation Benchmark Score"></a>
  <hr>
</div>

Welcome to MetaChain! MetaChain is a **Fully-Automated** and highly **Self-Developing** framework that enables users to create and deploy LLM agents through **Natural Language Alone**. 

## ✨Features

* **Top 1** 🏆 open-sourced method in GAIA benchmark, with performance comparable to **OpenAI's Deep Research**.
* **Top 1** 🏆 Agentic-RAG with native self-managing vector database, outperforming **LangChain**. 
* Create ready-to-use **tools**, **agents** and **workflows** using natural language **only**.
* Support for **ALL** LLMs (OpenAI, Anthropic, vLLM, Grok, Huggingface ...)
* Support both **function-calling** and **ReAct**.
* Dynamic, extensible, and lightweight - your **personal** agent system.
* Try it now!

<div align="center">
  <!-- <img src="./assets/metachainnew-intro.pdf" alt="Logo" width="100%"> -->
  <figure>
    <img src="./assets/metachain-intro-final.svg" alt="Logo" style="max-width: 100%; height: auto;">
    <figcaption><em>Quick Overview of MetaChain.</em></figcaption>
  </figure>
</div>


## 🔥 News

<div class="scrollable">
    <ul>
      <li><strong>[2025, Feb 10]</strong>: &nbsp;🎉🎉We've released <b>MetaChain!</b>, including framework, evaluation codes and CLI mode!</li>
    </ul>
</div>

## ⚡ Quick Start

### Installation

#### MetaChain Installation

```bash
git clone https://github.com/HKUDS/MetaChain.git
cd MetaChain
pip install -e .
```

#### Docker Installation

We use Docker to containerize the agent-interactive environment. So please install [Docker](https://www.docker.com/) first. And pull the pre-built image with the following command.

```bash
docker pull tjbtech1/metachain:latest
```

### API Keys Setup

Create a environment variable file, just like `.env.template`, and set the API keys for the LLMs you want to use. Not every LLM API Key is required, use what you need.

```bash
# Required Github Tokens of your own
GITHUB_AI_TOKEN=

# Optional API Keys
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
HUGGINGFACE_API_KEY=
GROQ_API_KEY=
XAI_API_KEY=
```

### Start with CLI Mode
Just run the following command to start the CLI mode. (use shell script `cd path/to/MetaChain && sh playground/cli/metachain_cli.sh`)

```bash
current_dir=$(dirname "$(readlink -f "$0")")

cd $current_dir
cd ../.. 
export DOCKER_WORKPLACE_NAME=workplace
export EVAL_MODE=True
export BASE_IMAGES=tjbtech1/metachain:latest
export COMPLETION_MODEL=claude-3-5-sonnet-20241022
export DEBUG=False # If you want to see detailed messages of agents' actions, set to True
export MC_MODE=True # If you want to ignore the retry information of LLM connection, set to True
export AI_USER=tjb-tech # Your Github username

port=12345 # The port of the agent-interactive environment

python playground/cli/metachain_cli.py --container_name quick_start --model ${COMPLETION_MODEL} --test_pull_name mirror_branch_0207 --debug --port ${port} --git_clone
```

After the CLI mode is started, you can see the start page of MetaChain: 

<div align="center">
  <!-- <img src="./assets/metachainnew-intro.pdf" alt="Logo" width="100%"> -->
  <figure>
    <img src="./assets/cover.png" alt="Logo" style="max-width: 100%; height: auto;">
    <figcaption><em>Start Page of MetaChain.</em></figcaption>
  </figure>
</div>

## 🔍 How to Use MetaChain

### 1. `user mode` (SOTA 🏆 Open Deep Research)

MetaChain have a out-of-the-box multi-agent system, which you could choose `user mode` in the start page to use it. This multi-agent system is a general AI assistant, having the same functionality with **OpenAI's Deep Research** and the comparable performance with it in [GAIA](https://gaia-benchmark-leaderboard.hf.space/) benchmark. 

<table>
<tr align="center">
    <td width="33%">
        <img src="./assets/user_mode/input.png" alt="Input" width="100%"/>
        <br>
        <em>Input your request.</em>
    </td>
    <td width="33%">
        <img src="./assets/user_mode/output.png" alt="Output" width="100%"/>
        <br>
        <em>Agent will give you the response.</em>
    </td>
    <td width="33%">
        <img src="./assets/user_mode/select_agent.png" alt="Select Agent" width="100%"/>
        <br>
        <em>Use @ to mention the agent you want to use. (Optional)</em>
    </td>
</tr>
</table>

### 2. `agent editor` 

### 3. `workflow editor`

## ☑️ Todo List



## 📖 Documentation


## 🤝 How to Join the Community

OpenHands is a community-driven project, and we welcome contributions from everyone. We do most of our communication
through Slack, so this is the best place to start, but we also are happy to have you contact us on Discord or Github:

- [Join our Slack workspace]() - Here we talk about research, architecture, and future development.
- [Join our Discord server]() - This is a community-run server for general discussion, questions, and feedback.
- [Read or post Github Issues](https://github.com/HKUDS/MetaChain/issues) - Check out the issues we're working on, or add your own ideas.

See more about the community in [COMMUNITY.md](./COMMUNITY.md) or find details on contributing in [CONTRIBUTING.md](./CONTRIBUTING.md).


## 🙏 Acknowledgements

OpenHands is built by a large number of contributors, and every contribution is greatly appreciated! We also build upon other open source projects, and we are deeply thankful for their work.

For a list of open source projects and licenses used in OpenHands, please see our [CREDITS.md](./CREDITS.md) file.

## 🌟 Cite

```

```
