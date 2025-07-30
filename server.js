const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
app.use(bodyParser.json());

// PORT obligatoire sur Render
const PORT = process.env.PORT;
if (!PORT) {
    console.error('Erreur : La variable d\'environnement PORT est requise');
    process.exit(1);
}

// Exemple : si tu veux répondre via une API (optionnel)
const WHATSAPP_API_URL = process.env.WHATSAPP_API_URL || null;

console.log(`🚀 Webhook serveur démarré sur le port ${PORT}`);

app.post('/webhook', async (req, res) => {
    const { event, data } = req.body;
    console.log(`📥 Événement reçu : ${event}`, data);

    switch (event) {
        case 'message_received':
            await handleMessageReceived(data);
            break;
        default:
            console.log('⚠️ Événement non géré :', event);
    }

    res.sendStatus(200);
});

async function handleMessageReceived(data) {
    const { from, body } = data;
    console.log(`💬 Message de ${from}: ${body}`);

    // Exemple : réponse automatique à certains messages
    if (!WHATSAPP_API_URL) return;

    try {
        if (body.toLowerCase() === 'bonjour') {
            await sendReply(from, 'Salut ! Comment puis-je t’aider ?');
        } else if (body.toLowerCase() === 'aide') {
            await sendReply(from, 'Commandes disponibles : bonjour, aide, info');
        } else if (body.toLowerCase() === 'info') {
            await sendReply(from, 'Bot WhatsApp via whatsapp-web.js');
        }
    } catch (err) {
        console.error('Erreur en envoyant la réponse:', err.message);
    }
}

async function sendReply(to, message) {
    if (!WHATSAPP_API_URL) return;
    await axios.post(WHATSAPP_API_URL, {
        to,
        message
    });
    console.log(`✅ Réponse envoyée à ${to}`);
}

app.listen(PORT, () => {
    console.log(`🚀 Webhook serveur à l'écoute sur le port ${PORT}`);
});
