# LiteClaw (Beta) 🦞

LiteClaw is a lightweight, agentic AI bridge you run on your own local environment. It answers you on the channels you already use (**WhatsApp**, **Telegram**, and **Slack**). It treats your favorite messaging apps as a "command-line for the real world"—allowing you to run shell commands, automate browsers, and manage your system directly from your phone.

If you want a personal, single-user assistant that feels local, fast, and always-on, this is it.

[Inspiration Project](https://github.com/openclaw/openclaw)  · [License](LICENSE) · [Beta FAQ](#-beta-warning)

**Preferred setup**: Run the onboarding wizard (`python onboarding.py`). It walks you through setting up your LLM keys, connecting your channels (WhatsApp/Telegram), and configuring hilarious GIF support. Designed to work on Windows (Powershell), Linux and macOS with zero friction.

```bash
python onboarding.py
```

**Model Note**: While any model via OpenRouter or Ollama is supported, we strongly recommend **Gemini 2.0 Flash** or **Claude 3.5 Sonnet** for the best tool-calling accuracy and prompt-injection resistance.

## Inspiration & Lineage
LiteClaw is the "lite" successor inspired by the powerful **[OpenClaw](https://github.com/openclaw/openclaw)** project. While OpenClaw is built for scale and deep OS integration, LiteClaw focuses on a zero-config, single-binary feel for local environments. We aim to bring the best tool-using "Lobster" vibes to a simpler, more accessible bridge.

> **⚠️ BETA WARNING**: This project is currently in **active development**. It is in a pre-release stage—highly experimental and built for early testers. We are polishing the core engine for a stable v1.0 release very soon. Use at your own risk.
>
> **Security Notice**: No security layer is currently implemented. We are working on integrating **[Hipocap](https://github.com/hipocap/hipocap)** to provide better security and permission management in the near future.

## Features & Status

- [x] **Multi-Channel Support**: WhatsApp, Telegram & Slack are fully active.
- [ ] **Next Channels**: Signal, iMessage, and Discord support coming soon.
- [ ] **Roadmap**:
  - [ ] **[Hipocap](https://github.com/hipocap/hipocap)** Security Layer Integration.
  - [ ] **ClawHub**: A registry for community-driven skills and tools.
  - [ ] **Tailscale Integration**: Securely access your local agent from anywhere.
  - [ ] **Agent-to-Agent**: Multi-agent sessions for complex task orchestration.
- [x] **Unified Bridge**: A single Node.js process handles all platform protocols.
- [x] **Agentic Capabilities**:
  - [x] **Shell Execution**: Full PowerShell integration.
  - [x] **Browser Automation**: `browser_task` for complex web flows.
  - [x] **Media Support**: Images, Videos, and Giphy integration.
- [x] **System Dashboard**: Professional control center at root `/`.
- [x] **Local Memory**: SQLite-based persistent session history.

## Installation

1.  **Clone the repo**:
    ```bash
    git clone https://github.com/yourusername/openclaw_lite.git
    cd openclaw_lite
    ```

2.  **Run Onboarding**:
    The onboarding script handles dependencies (Python & Node.js), config generation, and API key setup.
    ```bash
    python onboarding.py
    ```

3.  **Start the Engine**:
    This launches both the Python backend and the Unified Node.js Bridge.
    ```bash
    python run.py
    ```

## Contributing

We welcome contributions! We want to make LiteClaw the de-facto standard for lightweight agentic comms.

1.  **Fork the Project**
2.  **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
3.  **Commit your Changes** (`git commit -m 'Add some AmazingFeature'`)
4.  **Push to the Branch** (`git push origin feature/AmazingFeature`)
5.  **Open a Pull Request**

### Contribution Areas
- **Frontend**: The control center is live! Help us add more real-time monitoring and agent "thought" streams.
- **New Channels**: Help us add Discord or Matrix support.
- **Skills**: Add new `.md` skill files to the `skills/` directory.

## License

Distributed under the MIT License. See `LICENSE` for more information.
