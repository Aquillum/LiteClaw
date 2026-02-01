# 📡 LiteClaw Channels Guide

LiteClaw can talk to you through multiple platforms simultaneously. This guide explains how to set up each one.

---

## 🟢 WhatsApp (Primary)
LiteClaw uses a real browser instance (Puppeteer) to connect to WhatsApp Web.

### ✅ Features
- **Multi-Device Support**: Works even if your phone is offline.
- **Image/File Support**: Can send and receive images.
- **Privacy**: Creating a new session typically requires scanning a QR code once.

### 🛠️ Configuration
1. Run `liteclaw onboard` and select **WhatsApp**.
2. **Limit Allowed Numbers**: Highly recommended. Enter your phone number (with country code, no `+`) to ensure only you can control the bot.
   - Example: `919876543210` (for India +91)
3. **Pairing**:
   - Run `liteclaw pair` (or select "Yes" at the end of onboarding).
   - A QR code will appear in your terminal.
   - Open WhatsApp on your phone -> **Settings** -> **Linked Devices** -> **Link a Device**.
   - Scan the terminal QR code.

---

## 🔵 Telegram
A lightweight and fast alternative using the official Telegram Bot API.

### ✅ Features
- **Fast & Reliable**: No browser overhead.
- **Zero Setup Polling**: Works immediately without configuring webhooks or ports.

### 🛠️ Configuration
1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send the command `/newbot`.
3. Give your bot a **name** (e.g., "LiteClaw Assistant") and a **username** (e.g., "MyLiteClawBot").
4. BotFather will give you an **HTTP API Token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).
5. Run `liteclaw onboard`, select **Telegram**, and paste this token.

---

## 🔴 Slack (Advanced)
Perfect for workspace integration. LiteClaw uses **Socket Mode**, so you **do NOT** need to expose public ports or use ngrok.

### ✅ Features
- **Threads**: Can reply in threads to keep channels clean.
- **Mentions**: Listens for `@LiteClaw` mentions in channels.
- **DMs**: Works in direct messages.

### 🛠️ Configuration

#### 1. Create the App
1. Go to **[Slack API Apps](https://api.slack.com/apps)** -> **Create New App**.
2. Select **"From scratch"** -> Name it "LiteClaw" -> Select your workspace.

#### 2. Enable Socket Mode (App Token)
1. In the left sidebar, click **Socket Mode**.
2. Toggle **"Enable Socket Mode"**.
3. It will ask to generate an App-Level Token.
   - Name: `LiteClawSocket`
   - Scope: `connections:write`
   - Click **Generate**.
4. Copy the **App-Level Token** (starts with `xapp-...`). Save this!

#### 3. Configure Scopes (Bot Token)
1. Go to **OAuth & Permissions** in the sidebar.
2. Scroll down to **Scopes** -> **Bot Token Scopes**.
3. Add the following permissions:
   - `app_mentions:read` (To hear @mentions)
   - `chat:write` (To reply)
   - `im:write` (To DM you)
   - `im:history` (To read DMs)
   - `channels:history` (To read channel messages)
   - `users:read` (To know your name)
4. Scroll up and click **Install to Workspace**.
5. Copy the **Bot User OAuth Token** (starts with `xoxb-...`). Save this!

#### 4. Event Subscriptions
1. Go to **Event Subscriptions** in the sidebar.
2. Toggle **Enable Events** to **ON**.
3. Scroll down to **Subscribe to bot events**.
4. Add:
   - `message.im`
   - `message.channels`
   - `app_mention`
5. Click **Save Changes** (Bottom right).

#### 5. User Permissions
1. Go to **App Home** in the sidebar.
2. Under "Show Tabs", enable **Messages Tab**.
3. Check the box: "Allow users to send Slash commands and messages from the messages tab".

#### 6. Final Config
1. Run `liteclaw onboard` and select **Slack**.
2. Paste your `xoxb-...` (Bot Token) and `xapp-...` (App Token).
3. For **Signing Secret**, go to **Basic Information** -> **App Credentials** to find it.
