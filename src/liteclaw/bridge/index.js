const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const app = express();
app.use(express.json());

const PORT = 3040;
const PYTHON_BACKEND_PORT = process.env.PYTHON_BACKEND_PORT || 8009;
const PYTHON_BACKEND_URL = `http://localhost:${PYTHON_BACKEND_PORT}/whatsapp/incoming`;

// --- Configuration & WORK_DIR setup ---
const fs = require('fs');
const path = require('path');

let WORK_DIR = process.env.WORK_DIR;
let TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
let SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;

// Try to load additional config from config.json (checks root and WORK_DIR)
function loadConfigs() {
    const searchPaths = [
        path.join(__dirname, '..', 'config.json'), // Relative to bridge dir
        process.cwd(), // Root where app started
    ];

    // Add default WORK_DIR based on OS if not set
    if (!WORK_DIR) {
        const platform = process.platform;
        if (platform === 'win32') WORK_DIR = 'C:\\liteclaw';
        else WORK_DIR = path.join(require('os').homedir(), 'liteclaw');
    }

    searchPaths.push(path.join(WORK_DIR, 'config.json'));

    for (const p of searchPaths) {
        try {
            const configPath = p.endsWith('config.json') ? p : path.join(p, 'config.json');
            if (fs.existsSync(configPath)) {
                const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
                if (!WORK_DIR) WORK_DIR = config.WORK_DIR;
                if (!TELEGRAM_TOKEN) TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN;
                if (!SLACK_BOT_TOKEN) SLACK_BOT_TOKEN = config.SLACK_BOT_TOKEN;
                console.log(`[Bridge] Loaded config from: ${configPath}`);
                break;
            }
        } catch (err) { /* ignore */ }
    }
}

loadConfigs();

// 1. Setup WhatsApp Session Path in WORK_DIR
const sessionDataPath = path.join(WORK_DIR, 'sessions', 'whatsapp');
if (!fs.existsSync(sessionDataPath)) {
    fs.mkdirSync(sessionDataPath, { recursive: true });
}

console.log(`[Bridge] WhatsApp Session Storage: ${sessionDataPath}`);

const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "client-one",
        dataPath: sessionDataPath // <--- Save session in WORK_DIR
    }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--unhandled-rejections=strict']
    }
});

client.on('qr', (qr) => {
    console.log('QR RECEIVED - Scan with your phone:');
    const isLarge = process.env.QR_LARGE === 'true';
    if (isLarge) console.log("[Info] Using Large QR mode for better compatibility.");
    qrcode.generate(qr, { small: !isLarge });

    // Fallback: Save to HTML file in WORK_DIR with auto-refresh
    try {
        const qrHtmlPath = path.join(WORK_DIR, 'qr.html');
        const htmlContent = `
        <html>
        <head>
            <title>LiteClaw WhatsApp Login</title>
            <meta http-equiv="refresh" content="30">
            <style>
                body { display:flex; justify-content:center; align-items:center; height:100vh; flex-direction:column; font-family:'Inter', sans-serif; background:#f4f7f6; color:#333; margin:0; }
                .card { background:white; padding:40px; border-radius:16px; box-shadow:0 10px 25px rgba(0,0,0,0.05); text-align:center; max-width:400px; }
                #qrcode { margin:20px auto; padding:10px; background:white; }
                h1 { font-weight:700; color:#075e54; margin-bottom:10px; }
                p { color:#666; line-height:1.5; }
                .status { margin-top:20px; font-size:0.8em; color:#999; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>LiteClaw Login</h1>
                <p>Scan the QR code below using WhatsApp on your phone.</p>
                <div id="qrcode"></div>
                <div class="status">New QR generated at: ${new Date().toLocaleTimeString()}</div>
                <p style="color:gray; font-size:0.8em; margin-top:20px;">This page refreshes automatically. Use dark mode terminal for alternative view.</p>
            </div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
            <script>
                new QRCode(document.getElementById("qrcode"), {
                    text: "${qr}",
                    width: 256,
                    height: 256,
                    colorDark : "#000000",
                    colorLight : "#ffffff",
                    correctLevel : QRCode.CorrectLevel.H
                });
                // Small script to check if session is ready by reloading
                setTimeout(() => { window.location.reload(); }, 15000); 
            </script>
        </body>
        </html>`;
        fs.writeFileSync(qrHtmlPath, htmlContent);
        console.log(`[Bridge] Live QR updated: ${qrHtmlPath}`);
    } catch (e) { /* ignore */ }
});

client.on('ready', () => {
    console.log('WhatsApp Client is ready!');
    // Update HTML to success state before deletion
    try {
        const qrHtmlPath = path.join(WORK_DIR, 'qr.html');
        const successContent = `
        <html>
        <body style="display:flex; justify-content:center; align-items:center; height:100vh; flex-direction:column; font-family:sans-serif; background:#e8f5e9;">
            <div style="background:white; padding:40px; border-radius:16px; text-align:center; box-shadow:0 10px 25px rgba(0,0,0,0.05);">
                <h1 style="color:#2e7d32;">✅ Authenticated!</h1>
                <p>LiteClaw is now connected to your WhatsApp.</p>
                <p style="color:gray;">You can close this window now.</p>
            </div>
            <script>setTimeout(() => { window.close(); }, 5000);</script>
        </body>
        </html>`;
        fs.writeFileSync(qrHtmlPath, successContent);

        // Delete after a delay so the user sees the success message
        setTimeout(() => {
            if (fs.existsSync(qrHtmlPath)) fs.unlinkSync(qrHtmlPath);
        }, 10000);
    } catch (e) { /* ignore */ }
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
        const senderName = msg._data.notifyName || "Unknown";
        console.log(`[Incoming] From ${senderName} (${msg.from}): ${msg.body}`);
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
        // Check if client is ready before attempting to send
        if (!client || !client.info) {
            throw new Error("WhatsApp client not ready yet. Please wait for initialization.");
        }

        // Sanitize message to avoid Puppeteer evaluation issues
        // The "t: t" error is often caused by special characters in the browser context
        let sanitizedMessage = message;
        if (message) {
            // Replace potentially problematic characters with safe alternatives
            sanitizedMessage = message
                .replace(/₹/g, 'Rs.')      // Rupee symbol -> Rs.
                .replace(/€/g, 'EUR')       // Euro
                .replace(/£/g, 'GBP')       // Pound
                .replace(/¥/g, 'JPY')       // Yen
                .replace(/\u00A0/g, ' ')    // Non-breaking space
                .replace(/[\u2018\u2019]/g, "'")  // Smart quotes
                .replace(/[\u201C\u201D]/g, '"')  // Smart double quotes
                .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, ''); // Control chars
        }

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
            const response = await client.sendMessage(to, sanitizedMessage);
            return res.json({ success: true, id: response.id._serialized, platform: 'whatsapp' });
        }
    } catch (error) {
        console.error(`Error sending message/media (${platform || 'whatsapp'}):`, error);
        // Return full error details for better debugging
        res.status(500).json({
            success: false,
            error: error.message || error.toString(),
            errorType: error.name,
            errorStack: error.stack
        });
    }
});

// --- Telegram Polling (Zero-Setup) ---
// Note: TELEGRAM_TOKEN and SLACK_BOT_TOKEN are already loaded during bridge startup

if (TELEGRAM_TOKEN) {
    console.log("Starting Telegram Bot (Polling Mode)...");
    const TelegramBot = require('node-telegram-bot-api');

    // Configure polling with error handling options
    const bot = new TelegramBot(TELEGRAM_TOKEN, {
        polling: {
            interval: 300,
            autoStart: true,
            params: {
                timeout: 10
            }
        }
    });

    // Handle polling errors gracefully (ECONNRESET, network issues)
    bot.on('polling_error', (error) => {
        // Only log non-fatal errors to avoid spam
        if (error.code === 'EFATAL') {
            console.log('[Telegram] Polling connection reset, will auto-reconnect...');
        } else {
            console.error('[Telegram] Polling error:', error.code, error.message);
        }
    });

    bot.on('error', (error) => {
        console.error('[Telegram] Bot error:', error.message);
    });

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
