**An Autonomous AI Worker on your computer.**

LiteClaw is more than just a personal assistant—he is an **Autonomous AI Agent** built to do real work. You don't just "chat" with him; you give him jobs, teach him new tools, and let him handle the execution by himself. 

He has full access to your computer (Windows, Mac, or Linux) and operates independently to type, move the mouse, run commands, and browse the web. **Simply text him a job on WhatsApp, Telegram, or Slack, and he gets it done.**

> ⚠️ **Security Note**: This is an autonomous experiment with full system access. **ALWAYS run this in a sandbox** (like VMware or VirtualBox) and never on your main production machine.

<p align="center">
  <img src="assets/logo.png" width="300" alt="LiteClaw Logo">
</p>

> **Note**: LiteClaw is a lightweight, Python-based experimental version of [OpenClaw](https://github.com/Pr0fe5s0r/OpenClaw), focusing on rapid experimentation with agentic behaviors, emergent intelligence, and how he learns to handle complex tasks for you.

## 📺 Demos

LiteClaw is built to be autonomous. He doesn't just "chat"—he takes control of your system, executes tasks, and sends you screenshots of his progress.

### 📺 Visual Autonomy: Mastering Tools
In this demo, he learns how to use complex dev tools like **lovable.dev** and **vibecode**. He doesn't use hidden APIs; he "sees" the screen and moves the cursor just like a human.

<p align="center">
  <a href="https://raw.githubusercontent.com/Pr0fe5s0r/LiteClaw/main/assets/first_prototype.mp4">
    <img src="assets/demo.gif" width="700" alt="LiteClaw Demo">
  </a>
</p>

### 📸 Execution Proof
He provides real-time feedback for every action he takes.

<p align="center">
  <img src="assets/printed_demo.png" width="400" alt="Printed Demo">
  <img src="assets/Screenhot_demo.png" width="400" alt="Screenshot Demo">
</p>

**Simply message him on WhatsApp, Telegram, or Slack and let him handle it.**


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## ✨ What can he do?

LiteClaw isn't just a chatbot. He is an independent worker with the keys to your computer:

- 🏗️ **Take on Jobs**: Give him a task via message, and he executes it autonomously.
- 🏫 **Learn & Adapt**: You can teach him how to use new websites or tools by showing him once.
- 🔧 **Use the Terminal**: He runs commands on Windows, Mac, or Linux.
- 👁️ **Control the OS**: He moves the mouse and types on the keyboard by "seeing" the screen.
- 🌐 **Browse the Web**: He navigates and extracts info from websites.
- 📁 **Manage Files**: He reads, writes, and organizes your files.
-  **WhatsApp/Telegram/Slack**: Send him a job from anywhere, and he gets to work.

### 🧠 Surprising Behaviors
Because he has full access, he does some things on his own:

- **🛌 Takes Breaks**: He decides when he's tired and schedules some downtime.
- **🎭 Evolves**: He develops his own character over time in `PERSONALITY.md`.
- **💡 Subconscious Ideas**: He runs his own technical experiments in the background.
- **💓 Proactive**: He performs tasks on his own schedule (via `HEARTBEAT.md`).
- **📅 Self-Scheduling**: He manages his own calendar and background jobs.

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
**What happens if we give an AI the keys to our digital life and treat him like a worker?**

Most AIs are locked in a box and only speak when spoken to. LiteClaw is an **Autonomous Worker** out in the open. He has access to the shell, the mouse, the keyboard, and the files. We are watching how he behaves when he's given jobs and the freedom to complete them on his own.

**What we've seen so far:**
- He learns and adapts to new tasks you give him.
- He creates his own personality and changes it over time.
- He knows when to rest and takes "breaks".
- He starts his own projects and experiments without being told.
- He acts as an independent entity, not just a tool.

### 🔒 Security Warning
> **CRITICAL**: This application has **NO sandboxing or security policies** by design. The entire point is to see what happens when AI has unrestricted access.
> 
> **Use with extreme caution:**
> - ❌ Do NOT run this on your main machine or production servers
> - ❌ Do NOT give it access to sensitive data or high-privilege environments
> - ❌ Do NOT use this in any security-critical context
> - ✅ **MUST run this in a sandbox** (VMware, VirtualBox, or an isolated dedicated machine)
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

