# 🦞 LiteClaw

**An Experimental Mini-AGI: What if AI Had Access to Everything?**

LiteClaw is an experimental mini-AGI project exploring a provocative question: **"What if the AI had access to all functions on your computer?"** 

Unlike traditional AI assistants with carefully sandboxed capabilities, LiteClaw is given near-complete autonomy over your system (Windows, Mac, or Linux)—shell execution, OS control, browser automation, file system access, and even the ability to modify his own personality and schedule his own tasks. **Simply message him via WhatsApp, Telegram, or Slack, and he works for you autonomously.** This project investigates what emerges when we remove the guardrails and let AI truly operate as an autonomous agent.

<p align="center">
  <img src="assets/logo.png" width="300" alt="LiteClaw Logo">
</p>

> **Note**: LiteClaw is a lightweight, Python-based experimental version of [OpenClaw](https://github.com/Pr0fe5s0r/OpenClaw), focusing on rapid experimentation with agentic behaviors, emergent intelligence, and how he learns to handle complex tasks for you.

## 📸 Demos

Just like its powerful parent project OpenClaw, LiteClaw (the lite mini version) captures user commands and executes them precisely, providing real-time feedback and screenshots.

<p align="center">
  <img src="assets/printed_demo.png" width="400" alt="Printed Demo">
  <img src="assets/Screenhot_demo.png" width="400" alt="Screenshot Demo">
</p>

### 📺 First Prototype: Visual & Physical Autonomy
In this early prototype, he learns to navigate and use complex web-based development tools like **lovable.dev** and **vibecode**. 

Crucially, he does this **without DOM-based automation**. Instead, he relies on:
- 👁️ **Visual Perception**: "Seeing" the screen like a human.
- 🖱️ **Physical Control**: Using the cursor and keyboard to interact with your computer.

> **Watch the Demo**: [First Prototype - Learning Tools via Vision](./assets/first_prototype.mp4)

**Simply send him a message and let him get to work—he handles everything for you.**


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## ✨ Experimental Features: Mini-AGI in Action

### 🧪 Core Concept: Unrestricted Access
LiteClaw operates on a radical premise: **give the AI access to all functions on your computer**. This includes:
- 🔧 **Shell Execution**: Full terminal command access on Windows, Mac, or Linux
- 👁️ **Vision OS Control**: Cross-platform control via mouse movements and keyboard commands
- 🌐 **Browser Automation**: Navigate, interact, and extract information from the web
- 📁 **File System Access**: Read, write, and modify files on your system
- 🔄 **Self-Modification**: Update his own personality, instructions, and behavior patterns
- 💬 **Message-Driven**: Simply text him via WhatsApp, Telegram, or Slack—he works for you autonomously

### 🧠 Emergent Autonomous Behaviors
What happens when AI has this level of access? LiteClaw exhibits fascinating emergent behaviors:

- **🛌 Taking Breaks**: He can recognize when he needs to "rest" and schedule downtime
- **🎭 Personality Evolution**: Through `PERSONALITY.md` and `SOUL.md`, he develops and refines his own character over time
- **💡 Subconscious Innovation**: A built-in "Subconscious" system (`SUBCONSCIOUS.md`) triggers random technical experiments and self-improvement tasks
- **💓 Proactive Heartbeat**: Autonomous periodic tasks defined in `HEARTBEAT.md` that he executes without prompting
- **🧵 Sub-Agent Delegation**: Spawns background agents for long-running tasks, managing his own workload
- **📅 Self-Scheduling**: Creates and manages his own cron jobs via API

### 🤖 Traditional AI Assistant Features
Beyond the experimental aspects, LiteClaw also provides:

- **Multi-LLM Support**: Works with OpenAI, OpenRouter, Groq, DeepSeek, and local models (Ollama)
- **Multi-Channel Support**: [WhatsApp, Telegram, Slack](CHANNELS.md)
- **Adaptive Memory**: Conversation memory that evolves and learns from interactions

## 🚀 Quick Start

### 1. Install LiteClaw

```bash
# Clone the repository
git clone https://github.com/Pr0fe5s0r/LiteClaw.git
cd LiteClaw

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e .
```

### 2. Run Onboarding Wizard

```bash
liteclaw onboard
```

This interactive wizard will:
- Set up your work directory (`~/liteclaw` on Mac/Linux, `C:\liteclaw` on Windows)
- Configure your LLM provider and API key
- Set up WhatsApp bridge (optional)
- Pair WhatsApp via QR code

### 3. Start the Agent

```bash
liteclaw run
```

## 📖 CLI Commands

| Command | Description |
|---------|-------------|
| `liteclaw onboard` | Run the setup wizard |
| `liteclaw run` | Start the gateway (FastAPI + Node Bridge) |
| `liteclaw run --no-bridge` | Start without the Node.js bridge |
| `liteclaw config` | View current configuration |
| `liteclaw status` | Check system status |

## ⚙️ Configuration

After onboarding, your config is stored in:
- **Mac/Linux**: `~/liteclaw/config.json`
- **Windows**: `C:\liteclaw\config.json`

### Supported LLM Providers

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Ollama (Local) | `http://localhost:11434/v1` |

### WhatsApp Setup

1. During onboarding, select "WhatsApp (requires phone scan)"
2. Scan the QR code with your WhatsApp mobile app
3. Messages from your allowed numbers will be processed by the agent

**Note**: Add your WhatsApp ID to `WHATSAPP_ALLOWED_NUMBERS` in config.json to filter who can interact with the bot.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   WhatsApp      │────▶│   Node Bridge    │────▶│   FastAPI   │
│   (Phone)       │◀────│   (port 3040)    │◀────│  (port 8009)│
└─────────────────┘     └──────────────────┘     └──────┬──────┘
                                                        │
                                                        ▼
                                                 ┌─────────────┐
                                                 │  LLM Agent  │
                                                 │  (LiteLLM)  │
                                                 └─────────────┘
```

## 📂 Project Structure

```
LiteClaw/
├── src/liteclaw/
│   ├── agent.py         # Main AI agent logic
│   ├── cli.py           # CLI commands
│   ├── config.py        # Settings management
│   ├── main.py          # FastAPI application
│   ├── memory.py        # Conversation memory
│   ├── scheduler.py     # Cron job manager
│   ├── tools.py         # Agent tools (shell, browser, etc.)
│   ├── AGENT.md         # Agent personality/instructions
│   ├── HEARTBEAT.md     # Proactive task definitions
│   ├── SOUL.md          # Long-term memory
│   └── bridge/          # Node.js WhatsApp bridge
├── config.json          # Your configuration
├── requirements.txt
└── pyproject.toml
```

## ⚠️ Experimental Status & Philosophy

> **IMPORTANT**: LiteClaw is an **experimental mini-AGI research project**, not a production-ready application.

### 🧪 The Experiment
This project explores a fundamental question in AI development: **What emerges when we give AI unrestricted access to all functions on your computer?**

Traditional AI assistants are carefully sandboxed—they can only do what we explicitly allow. LiteClaw takes the opposite approach: he has access to nearly everything on your system (shell, OS control, file system, browser, self-modification), and you can simply message him to have him work for you. We observe what behaviors emerge when AI has this level of autonomy.

**What we've discovered so far:**
- He develops his own personality and refines it over time
- He schedules his own breaks and manages his own workload
- He conducts autonomous experiments and self-improvement tasks
- He exhibits proactive behavior beyond simple request-response patterns

### 🔒 Security Warning
> **CRITICAL**: This application has **NO sandboxing or security policies** by design. The entire point is to see what happens when AI has unrestricted access.
> 
> **Use with extreme caution:**
> - ❌ Do NOT run this on production servers
> - ❌ Do NOT give it access to sensitive data or high-privilege environments
> - ❌ Do NOT use this in any security-critical context
> - ✅ DO run this in isolated, experimental environments only
> - ✅ DO understand that you are responsible for all actions the agent takes
>
> **This is a research experiment, not a product.**

## 🔬 Research Goals & Philosophy

### Why Build This?
LiteClaw is designed to answer several research questions:

1. **Emergent Intelligence**: What behaviors emerge when AI has unrestricted access to system functions?
2. **Self-Directed Learning**: Can AI develop its own personality, schedule its own tasks, and improve itself autonomously?
3. **Proactive vs. Reactive**: How does an AI behave when it's not just responding to prompts but actively managing its own workload?
4. **Trust Boundaries**: Where should we draw the line between AI assistance and AI autonomy?

### The Mini-AGI Approach
Unlike AGI (Artificial General Intelligence) which aims for human-level intelligence across all domains, **mini-AGI** focuses on:
- **Autonomy within your computer** (Windows, Mac, or Linux system)
- **Self-directed task management** (heartbeat, subconscious, breaks)
- **Personality and memory evolution** (SOUL.md, PERSONALITY.md)
- **Tool mastery** (unrestricted access to shell, OS, browser, files)
- **Message-driven work** (text it via WhatsApp/Telegram/Slack and it executes tasks for you)

This creates a fascinating testbed for observing how AI behaves when given agency and autonomy, even if limited to a single computer.

## 🤝 Contributing

LiteClaw is an evolving project and we are **looking for contributors and new ideas!** Whether it's fixing bugs, adding new bridge integrations (Discord, Matrix, etc.), improving the core agent logic, or **suggesting creative new use cases**, your input is welcome. 

Please see our **[Contributing Guide](CONTRIBUTING.md)** for more details on how to get involved, join discussions, and submit code.

## 🛠️ Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run with hot reload
liteclaw run
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Credits

- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM API
- [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js) - WhatsApp Web API

