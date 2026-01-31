const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const app = express();
app.use(express.json());

const PORT = 3040;
const PYTHON_BACKEND_URL = 'http://localhost:8009/whatsapp/incoming';

console.log("Initializing WhatsApp Client...");

const client = new Client({
    authStrategy: new LocalAuth({ clientId: "client-one" }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--unhandled-rejections=strict']
    }
});

client.on('qr', (qr) => {
    console.log('QR RECEIVED - Scan with your phone:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp Client is ready!');
});

client.on('authenticated', () => {
    console.log('Authenticated successfully!');
});

client.on('message_create', async (msg) => {
    // Ignore status updates/broadcasts if needed
    if (msg.from === 'status@broadcast') return;

    // Log everything for debugging
    if (msg.fromMe) {
        console.log(`[Self] Sent to ${msg.to}: ${msg.body}`);
    } else {
        console.log(`[Incoming] From ${msg.from}: ${msg.body}`);
    }

    try {
        // Forward to Python Backend
        // If I send a message, associate it with the recipient's session (msg.to)
        // If someone sends me something, associate it with them (msg.from)
        let sessionKey = msg.fromMe ? msg.to : msg.from;

        await axios.post(PYTHON_BACKEND_URL, {
            message_id: msg.id._serialized,
            from: sessionKey,
            body: msg.body,
            timestamp: msg.timestamp,
            senderName: msg._data.notifyName || (msg.fromMe ? "Me" : "Unknown"),
            fromMe: msg.fromMe
        });
    } catch (error) {
        // console.error('Error forwarding message to Python:', error.message);
    }
});

client.initialize();

// API to set typing state
app.post('/whatsapp/typing', async (req, res) => {
    const { to, platform } = req.body;
    if (!to) return res.status(400).json({ error: "Missing 'to'" });

    try {
        if (platform === 'telegram') {
            if (global.telegramBot) {
                await global.telegramBot.sendChatAction(to, 'typing');
                return res.json({ success: true, platform: 'telegram' });
            }
            return res.status(400).json({ error: "Telegram bot not initialized" });
        }

        if (platform === 'slack') {
            // Slack typing is complex for bots, skipping for now.
            return res.json({ success: true, platform: 'slack' });
        }

        // Default to WhatsApp
        const chat = await client.getChatById(to);
        await chat.sendStateTyping();
        res.json({ success: true, platform: 'whatsapp' });
    } catch (error) {
        console.error(`Error setting typing state (${platform || 'whatsapp'}):`, error.message);
        res.status(500).json({ success: false });
    }
});

// API to stop typing state
app.post('/whatsapp/stop-typing', async (req, res) => {
    const { to, platform } = req.body;
    if (!to) return res.status(400).json({ error: "Missing 'to'" });

    try {
        if (platform === 'telegram') {
            // Telegram doesn't have a direct "stop typing", it expires automatically.
            return res.json({ success: true, platform: 'telegram' });
        }

        if (platform === 'slack') {
            return res.json({ success: true, platform: 'slack' });
        }

        // WhatsApp
        const chat = await client.getChatById(to);
        await chat.clearState();
        res.json({ success: true, platform: 'whatsapp' });
    } catch (error) {
        console.error(`Error stopping typing state (${platform || 'whatsapp'}):`, error.message);
        res.status(500).json({ success: false });
    }
});

// API to send messages (Unified for text and media)
app.post('/whatsapp/send', async (req, res) => {
    const { to, message, platform, is_media, url_or_path, type, caption } = req.body;

    if (!to || (!message && !is_media)) {
        return res.status(400).json({ error: "Missing 'to' or content" });
    }

    try {
        if (platform === 'telegram') {
            if (!global.telegramBot) throw new Error("Telegram bot not initialized");

            if (is_media) {
                if (type === 'image' || type === 'gif') {
                    await global.telegramBot.sendPhoto(to, url_or_path, { caption: caption });
                } else if (type === 'video') {
                    await global.telegramBot.sendVideo(to, url_or_path, { caption: caption });
                } else if (type === 'audio') {
                    await global.telegramBot.sendAudio(to, url_or_path, { caption: caption });
                } else {
                    await global.telegramBot.sendDocument(to, url_or_path, { caption: caption });
                }
            } else {
                await global.telegramBot.sendMessage(to, message);
            }
            return res.json({ success: true, platform: 'telegram' });
        }

        if (platform === 'slack') {
            if (!SLACK_BOT_TOKEN) throw new Error("SLACK_BOT_TOKEN not initialized");

            let text = message;
            if (is_media && url_or_path) {
                text = `${caption || ''}\n${url_or_path}`;
            }

            const response = await axios.post('https://slack.com/api/chat.postMessage', {
                channel: to,
                text: text
            }, {
                headers: { 'Authorization': `Bearer ${SLACK_BOT_TOKEN}` }
            });

            if (!response.data.ok) throw new Error(response.data.error);
            return res.json({ success: true, platform: 'slack' });
        }

        // --- WhatsApp Logic ---
        if (is_media) {
            let media;
            if (url_or_path.startsWith('http')) {
                media = await MessageMedia.fromUrl(url_or_path);
            } else {
                // Local file
                media = MessageMedia.fromFilePath(url_or_path);
            }
            const response = await client.sendMessage(to, media, { caption: caption });
            return res.json({ success: true, id: response.id._serialized, platform: 'whatsapp' });
        } else {
            const response = await client.sendMessage(to, message);
            return res.json({ success: true, id: response.id._serialized, platform: 'whatsapp' });
        }
    } catch (error) {
        console.error(`Error sending message/media (${platform || 'whatsapp'}):`, error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// --- Telegram Polling (Zero-Setup) ---
// We check for env var passed from run.py or fallback to reading config.json
const fs = require('fs');
const path = require('path');

let TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
let SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;

if (!TELEGRAM_TOKEN || !SLACK_BOT_TOKEN) {
    try {
        const configPath = path.join(__dirname, '..', 'config.json');
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            if (!TELEGRAM_TOKEN) TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN;
            if (!SLACK_BOT_TOKEN) SLACK_BOT_TOKEN = config.SLACK_BOT_TOKEN;
        }
    } catch (err) {
        console.error("Error reading config.json for tokens:", err.message);
    }
}

if (TELEGRAM_TOKEN) {
    console.log("Starting Telegram Bot (Polling Mode)...");
    const TelegramBot = require('node-telegram-bot-api');
    const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

    bot.on('message', async (msg) => {
        // Only ignore if no text
        if (!msg.text) return;

        const payload = {
            platform: 'telegram',
            message_id: msg.message_id.toString(),
            from: msg.chat.id.toString(), // Chat ID as session key
            body: msg.text,
            timestamp: msg.date,
            senderName: msg.from.first_name || "Telegram User",
            fromMe: false
        };

        console.log(`[Telegram] Incoming: ${msg.text}`);

        // Forward to Python
        try {
            await axios.post(PYTHON_BACKEND_URL, payload);
        } catch (error) {
            console.error('[Telegram] Forward Error:', error.message);
        }
    });

    // Store globally for reply handler
    global.telegramBot = bot;

} else {
    console.log("No TELEGRAM_BOT_TOKEN found in env. Skipping Telegram.");
}

// --- Slack Webhook (Events API) ---
app.post('/slack/events', async (req, res) => {
    const body = req.body;

    // Handle URL verification challenge
    if (body.type === 'url_verification') {
        return res.json({ challenge: body.challenge });
    }

    // Handle message events
    if (body.event && body.event.type === 'message' && !body.event.bot_id) {
        const payload = {
            platform: 'slack',
            message_id: body.event.ts,
            from: body.event.channel, // Channel ID as session key (or user if DM)
            body: body.event.text,
            timestamp: parseFloat(body.event.ts),
            senderName: body.event.user, // Usually a User ID, would need lookup for real name
            fromMe: false
        };

        console.log(`[Slack] Payload:`, payload);

        // Forward to Python
        try {
            await axios.post(PYTHON_BACKEND_URL, payload);
        } catch (error) {
            console.error('[Slack] Forward Error:', error.message);
        }
    }

    res.sendStatus(200);
});

const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`Unified Bridge (WhatsApp/Telegram/Slack) running on port ${PORT}`);
}).on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`\n[CRITICAL ERROR] Port ${PORT} is ALREADY IN USE.`);
        console.error(`Please kill any other running 'node index.js' or 'python run.py' processes first.\n`);
        process.exit(1);
    } else {
        console.error('Server error:', err);
    }
});
