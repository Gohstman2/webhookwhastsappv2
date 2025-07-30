const express = require('express');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
app.use(bodyParser.json());

// Variables via process.env (Render)
// PORT obligatoire sur Render
const PORT = process.env.PORT;
if (!PORT) {
    console.error('Erreur : La variable d\'environnement PORT est requise');
    process.exit(1);
}
const WEBHOOK_URL = process.env.WEBHOOK_URL || null;

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true }
});

client.on('qr', qr => {
    console.log('[QR CODE]');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => console.log('✅ WhatsApp prêt'));
client.on('authenticated', () => console.log('🔐 Authentifié'));
client.on('auth_failure', () => console.log('❌ Échec authentification'));
client.on('disconnected', () => console.log('❌ Déconnecté'));

// Envoi webhook event
async function emitWebhookEvent(eventType, data) {
    if (!WEBHOOK_URL) return;
    try {
        await axios.post(WEBHOOK_URL, { event: eventType, data });
    } catch (e) {
        console.error('Erreur webhook:', e.message);
    }
}

client.on('message', async msg => {
    emitWebhookEvent('message_received', {
        from: msg.from,
        body: msg.body,
        type: msg.type,
        timestamp: msg.timestamp
    });

    if (msg.body.toLowerCase() === '!ping') {
        msg.reply('pong');
    }
});

client.initialize();

// Routes

app.get('/status', async (req, res) => {
    try {
        const me = await client.getMe();
        res.json({ connected: true, me });
    } catch {
        res.json({ connected: false });
    }
});

app.post('/messages/send', async (req, res) => {
    const { to, message } = req.body;
    if (!to || !message) return res.status(400).json({ error: 'to et message requis' });

    try {
        const sent = await client.sendMessage(to, message);
        res.json({ id: sent.id._serialized, ack: sent.ack });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/messages/media', async (req, res) => {
    const { to, base64, mimetype, filename, caption } = req.body;
    if (!to || !base64 || !mimetype) return res.status(400).json({ error: 'to, base64 et mimetype requis' });

    try {
        const media = new MessageMedia(mimetype, base64, filename);
        const sent = await client.sendMessage(to, media, { caption });
        res.json({ id: sent.id._serialized });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/groups/create', async (req, res) => {
    const { name, participants } = req.body;
    if (!name || !participants || !Array.isArray(participants)) {
        return res.status(400).json({ error: 'name et participants[] requis' });
    }
    try {
        const group = await client.createGroup(name, participants);
        res.json(group);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/groups/add', async (req, res) => {
    const { chatId, participants } = req.body;
    if (!chatId || !participants || !Array.isArray(participants)) {
        return res.status(400).json({ error: 'chatId et participants[] requis' });
    }
    try {
        const chat = await client.getChatById(chatId);
        await chat.addParticipants(participants);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/groups/remove', async (req, res) => {
    const { chatId, participants } = req.body;
    if (!chatId || !participants || !Array.isArray(participants)) {
        return res.status(400).json({ error: 'chatId et participants[] requis' });
    }
    try {
        const chat = await client.getChatById(chatId);
        await chat.removeParticipants(participants);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/contacts', async (req, res) => {
    try {
        const contacts = await client.getContacts();
        res.json(contacts);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/contacts/:id', async (req, res) => {
    try {
        const contact = await client.getContactById(req.params.id);
        res.json(contact);
    } catch {
        res.status(404).json({ error: 'Contact non trouvé' });
    }
});

app.post('/messages/reply', async (req, res) => {
    const { to, messageId, message } = req.body;
    if (!to || !messageId || !message) return res.status(400).json({ error: 'to, messageId et message requis' });

    try {
        const chat = await client.getChatById(to);
        const msgs = await chat.fetchMessages({ limit: 50 });
        const original = msgs.find(m => m.id._serialized === messageId);

        if (!original) return res.status(404).json({ error: 'Message original non trouvé' });

        await original.reply(message);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 Serveur WhatsApp API démarré sur le port ${PORT}`);
});
