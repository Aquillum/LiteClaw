# 🚀 LiteClaw

Lightweight AI Agent Bridge with Adaptive Personality. LiteClaw integrates your AI with messaging platforms (WhatsApp, Telegram, Slack) and allows it to perform browser automation, shell execution, and more.

## 🛠️ Setup Instructions

To share this repo and run it in a clean virtual environment, follow these steps:

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd LiteClaw
```

### 2. Create a Virtual Environment
We recommend using `python -m venv` or `uv` for speed.

**Using venv:**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note for Browser Automation:**
If you plan to use `browser-use`, you must install the Playwright browsers:
```bash
playwright install
```

### 4. Configuration
1. Rename `.env.example` to `.env` and fill in your API keys.
2. Ensure you have the Node.js bridge dependencies installed:
```bash
cd src/liteclaw/bridge
npm install
cd ../../../
```

### 5. Run LiteClaw
```bash
python -m src.liteclaw.cli run
```
Or, if you installed the package:
```bash
liteclaw run
```

## 🧠 Features
- **Adaptive Personality**: Soul/Personality memory that evolves.
- **Browser Automation**: Powered by `browser-use`.
- **Proactive Heartbeat**: Define periodic tasks in `HEARTBEAT.md`.
- **Multi-Platform**: Bridge to WhatsApp, Telegram, and Slack.
- **Sub-Agents**: Delegate long-running tasks to background agents.

## 🛡️ License
MIT
