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
let SLACK_APP_TOKEN = process.env.SLACK_APP_TOKEN;
let SLACK_SIGNING_SECRET = process.env.SLACK_SIGNING_SECRET;
let WHATSAPP_TYPE = process.env.WHATSAPP_TYPE;

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
                if (!SLACK_APP_TOKEN) SLACK_APP_TOKEN = config.SLACK_APP_TOKEN;
                if (!SLACK_SIGNING_SECRET) SLACK_SIGNING_SECRET = config.SLACK_SIGNING_SECRET;
                if (!WHATSAPP_TYPE) WHATSAPP_TYPE = config.WHATSAPP_TYPE;
                console.log(`[Bridge] Loaded config from: ${configPath}`);
                break;
            }
        } catch (err) { /* ignore */ }
    }
}

loadConfigs();

function sanitize(message) {
    if (!message) return "";
    return message
        .replace(/₹/g, 'Rs.')      // Rupee symbol -> Rs.
        .replace(/€/g, 'EUR')       // Euro
        .replace(/£/g, 'GBP')       // Pound
        .replace(/¥/g, 'JPY')       // Yen
        .replace(/\u00A0/g, ' ')    // Non-breaking space
        .replace(/[\u2018\u2019]/g, "'")  // Smart quotes
        .replace(/[\u201C\u201D]/g, '"')  // Smart double quotes
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, ''); // Control chars
}

let client = null;

if (WHATSAPP_TYPE === 'node_bridge' || (!TELEGRAM_TOKEN && !SLACK_BOT_TOKEN)) {
    console.log(`[Bridge] Initializing WhatsApp Client (Type: ${WHATSAPP_TYPE || 'default'})...`);

    // 1. Setup WhatsApp Session Path in WORK_DIR
    const sessionDataPath = path.join(WORK_DIR, 'sessions', 'whatsapp');
    if (!fs.existsSync(sessionDataPath)) {
        fs.mkdirSync(sessionDataPath, { recursive: true });
    }

    client = new Client({
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
                    <h1>🦞 LiteClaw Login</h1>
                    <p>Scan the QR code with WhatsApp to connect.</p>
                    <div id="qrcode"></div>
                    <div class="status">Waiting for connection...</div>
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
} else {
    console.log("[Bridge] WhatsApp is DISABLED (WHATSAPP_TYPE not set or Telegram/Slack is active).");
}

// API to set typing state
app.post('/whatsapp/typing', async (req, res) => {
    const { to, platform } = req.body;
    if (!to) return res.status(400).json({ error: "Missing 'to'" });

    try {
        if (platform === 'telegram') {
            const { bot, chatId } = resolveTelegramTarget(to);
            if (bot) {
                await bot.sendChatAction(chatId, 'typing');
                return res.json({ success: true, platform: 'telegram' });
            }
            return res.status(400).json({ error: "Telegram bot not initialized" });
        }

        if (platform === 'slack') {
            // Slack typing is complex for bots, skipping for now.
            return res.json({ success: true, platform: 'slack' });
        }

        // WhatsApp
        if (!client) {
            throw new Error("WhatsApp client not initialized");
        }
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
        if (!client) {
            return res.status(400).json({ error: "WhatsApp client not initialized" });
        }
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
            const { bot, chatId } = resolveTelegramTarget(to);
            if (!bot) throw new Error("Telegram bot not initialized");

            if (is_media) {
                // For local files, we must use fs.createReadStream to ensure reliable delivery
                let mediaSource = url_or_path;
                if (fs.existsSync(url_or_path)) {
                    mediaSource = fs.createReadStream(url_or_path);
                }

                if (type === 'image') {
                    await bot.sendPhoto(chatId, mediaSource, { caption: caption });
                } else if (type === 'gif') {
                    // GIFs are best sent as animations in Telegram
                    await bot.sendAnimation(chatId, mediaSource, { caption: caption });
                } else if (type === 'video') {
                    await bot.sendVideo(chatId, mediaSource, { caption: caption });
                } else if (type === 'audio') {
                    await bot.sendAudio(chatId, mediaSource, { caption: caption });
                } else {
                    await bot.sendDocument(chatId, mediaSource, { caption: caption });
                }
            } else {
                await bot.sendMessage(chatId, sanitize(message));
            }
            return res.json({ success: true, platform: 'telegram' });
        }
        if (platform === 'slack') {
            if (!SLACK_BOT_TOKEN) throw new Error("SLACK_BOT_TOKEN not initialized");

            let text = message;
            if (is_media && url_or_path) {
                text = `${caption || ''}\n${url_or_path}`;
            }

            // Use Bolt app client if available, fallback to axios
            if (global.slackApp) {
                const result = await global.slackApp.client.chat.postMessage({
                    channel: to,
                    text: text
                });
                if (!result.ok) throw new Error(result.error);
                return res.json({ success: true, platform: 'slack' });
            } else {
                const response = await axios.post('https://slack.com/api/chat.postMessage', {
                    channel: to,
                    text: text
                }, {
                    headers: { 'Authorization': `Bearer ${SLACK_BOT_TOKEN}` }
                });

                if (!response.data.ok) throw new Error(response.data.error);
                return res.json({ success: true, platform: 'slack' });
            }
        }

        // --- WhatsApp Logic ---
        if (!client || !client.info) {
            throw new Error("WhatsApp client not ready yet. Please wait for initialization.");
        }

        // Sanitization handled by helper
        let sanitizedMessage = sanitize(message);

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

// --- Telegram Polling (Unified Multi-Bot Support) ---

let telegramTokens = [];
if (process.env.TELEGRAM_BOT_TOKEN) telegramTokens.push(process.env.TELEGRAM_BOT_TOKEN);
if (process.env.TELEGRAM_BOT_TOKENS) {
    const extraTokens = process.env.TELEGRAM_BOT_TOKENS.split(',').map(t => t.trim()).filter(t => t);
    telegramTokens = [...telegramTokens, ...extraTokens];
}
// Remove duplicates
telegramTokens = [...new Set(telegramTokens)];

global.telegramBots = new Map(); // username -> bot instance
global.defaultTelegramBot = null; // fallback

if (telegramTokens.length > 0) {
    console.log(`[Telegram] Found ${telegramTokens.length} bot token(s). Initializing...`);
    const TelegramBot = require('node-telegram-bot-api');

    telegramTokens.forEach(token => {
        try {
            const bot = new TelegramBot(token, {
                polling: {
                    interval: 300,
                    autoStart: true,
                    params: { timeout: 10 }
                }
            });

            // Get bot info to identify it
            bot.getMe().then(me => {
                const username = me.username;
                console.log(`[Telegram] ✅ Bot started: @${username}`);
                global.telegramBots.set(username, bot);

                // Set first one as default
                if (!global.defaultTelegramBot) global.defaultTelegramBot = bot;

                setupTelegramListeners(bot, username);
            }).catch(err => {
                console.error(`[Telegram] Failed to init bot with token ending ...${token.slice(-5)}: ${err.message}`);
            });

        } catch (e) {
            console.error(`[Telegram] Setup error: ${e.message}`);
        }
    });
} else {
    console.log("No TELEGRAM_BOT_TOKEN(s) found in env. Skipping Telegram.");
}

function setupTelegramListeners(bot, botUsername) {
    // Handle polling errors gracefully
    bot.on('polling_error', (error) => {
        if (error.code !== 'EFATAL') {
            // console.error(`[Telegram:@${botUsername}] Polling error: ${error.code}`);
        }
    });

    bot.on('message', async (msg) => {
        if (!msg.text) return;

        // Structure session ID as "botUsername:chatId" to isolate sessions
        // We use the first one as default/legacy if needed, but for multi-bot 
        // strictly prefer the prefixed version to avoid collision.
        const sessionKey = `${botUsername}:${msg.chat.id}`;

        const payload = {
            platform: 'telegram',
            message_id: msg.message_id.toString(),
            from: sessionKey,
            body: msg.text,
            timestamp: msg.date,
            senderName: msg.from.first_name || "Telegram User",
            fromMe: false
        };

        const senderName = msg.from.first_name || "Telegram User";
        console.log(`[Incoming] From ${senderName} (${sessionKey}): ${msg.text}`);

        try {
            await axios.post(PYTHON_BACKEND_URL, payload);
        } catch (error) {
            console.error(`[Telegram] Forward Error: ${error.message}`);
        }
    });
}

// Helper to resolve bot and chat ID from "username:chatId" string
function resolveTelegramTarget(to) {
    if (to.includes(':')) {
        const parts = to.split(':');
        // Check if the first part is a known bot username
        // Part 0 might be username, Part 1 might be chat ID
        // Caution: Colon is rare in normal chat IDs but standard in our new format
        const username = parts[0];
        const chatId = parts.slice(1).join(':'); // Re-join rest in case of weirdness

        if (global.telegramBots.has(username)) {
            return { bot: global.telegramBots.get(username), chatId: chatId };
        }
    }

    // Fallback: If no prefix or unknown prefix, use default bot
    // This maintains backward compatibility if 'to' is just a number
    return { bot: global.defaultTelegramBot, chatId: to };
}



// --- Slack Socket Mode (Bolt.js) ---
if (SLACK_BOT_TOKEN && SLACK_APP_TOKEN) {
    const { App } = require('@slack/bolt');

    console.log("Starting Slack App (Socket Mode)...");
    const slackApp = new App({
        token: SLACK_BOT_TOKEN,
        appToken: SLACK_APP_TOKEN,
        signingSecret: SLACK_SIGNING_SECRET,
        socketMode: true,
    });

    // Simple cache for Slack user info to reduce API calls
    const slackUserCache = new Map();

    async function getSlackUserName(userId) {
        if (slackUserCache.has(userId)) return slackUserCache.get(userId);
        try {
            const result = await global.slackApp.client.users.info({ user: userId });
            if (result.ok && result.user) {
                const name = result.user.real_name || result.user.name;
                slackUserCache.set(userId, name);
                // Clear cache after 1 hour
                setTimeout(() => slackUserCache.delete(userId), 3600000);
                return name;
            }
        } catch (e) {
            console.error('[Slack] Error fetching user info:', e.message);
        }
        return userId; // Fallback to ID
    }

    // Helper function to forward messages to Python backend
    async function forwardToLiteClaw(channel, text, userId, ts, eventType) {
        if (!text) return; // Skip events without text (like edits or just emoji reactions sometimes)

        // Clean the message text - remove the bot mention if present
        let cleanText = text.replace(/<@[A-Z0-9]+>/g, '').trim();

        if (!cleanText) {
            console.log(`[Slack] Empty message after cleaning mentions, skipping.`);
            return;
        }

        const realName = await getSlackUserName(userId);

        const payload = {
            platform: 'slack',
            message_id: ts,
            from: channel, // Channel ID as session key
            body: cleanText,
            timestamp: parseFloat(ts),
            senderName: realName,
            fromMe: false
        };

        console.log(`[Incoming] From ${realName} (${channel}): ${cleanText}`);

        // Acknowledge to Slack immediately (Async)
        axios.post(PYTHON_BACKEND_URL, payload).then(() => {
            console.log(`[Slack] Response sent to LiteClaw Backend successfully.`);
        }).catch(error => {
            console.error('[Slack] Backend Forward Error:', error.message);
        });
    }

    // Capture everything for debugging
    slackApp.message(async ({ message }) => {
        // Handle DMs (im) and Group DMs (mpim)
        if (message.channel_type === 'im' || message.channel_type === 'mpim') {
            if (message.bot_id || message.subtype === 'bot_message') return;
            // console.log(`[Slack DEBUG] DM received: ${message.text}`);
            await forwardToLiteClaw(message.channel, message.text, message.user, message.ts, 'DM');
        }
    });

    // Handle Mentions specifically
    slackApp.event('app_mention', async ({ event }) => {
        // console.log(`[Slack DEBUG] Mention event caught: ${event.text}`);
        await forwardToLiteClaw(event.channel, event.text, event.user, event.ts, 'Mention');
    });

    (async () => {
        try {
            console.log(`[Slack] Attempting to connect to Slack Socket Mode...`);
            console.log(`[Slack] Bot Token: ${SLACK_BOT_TOKEN ? 'Present' : 'MISSING'}`);
            console.log(`[Slack] App Token: ${SLACK_APP_TOKEN ? 'Present' : 'MISSING'}`);
            console.log(`[Slack] Signing Secret: ${SLACK_SIGNING_SECRET ? 'Present' : 'MISSING'}`);

            await slackApp.start();
            console.log("Slack App (Socket Mode) is running!");
            console.log("  - @mention the bot in channels to interact.");
            console.log("  - DM the bot directly for private conversations.");
            global.slackApp = slackApp;
        } catch (err) {
            console.error("[Slack] Failed to start Bolt app. Error details:");
            console.error(err);
        }
    })();
} else {
    console.log("No SLACK_BOT_TOKEN or SLACK_APP_TOKEN found. Skipping Slack Socket Mode.");
    // Fallback Events API handler if tokens aren't provided for Socket Mode
    app.post('/slack/events', async (req, res) => {
        const body = req.body;
        if (body.type === 'url_verification') {
            return res.json({ challenge: body.challenge });
        }
        res.sendStatus(200);
    });
}

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
