const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

require('dotenv').config();

const app = express();
app.use(bodyParser.json());

const PORT = process.env.WEBHOOK_PORT || 4000;
const WHATSAPP_API_URL = process.env.WHATSAPP_API_URL || 'http://localhost:3000/messages/send';

console.log(`🟢 Webhook actif sur http://localhost:${PORT}/webhook`);

app.post('/webhook', async (req, res) => {
    const { event, data } = req.body;

    console.log('📥 Webhook reçu :', event);

    // Traitement selon le type d'événement
    switch (event) {
        case 'message_received':
            await handleIncomingMessage(data);
            break;

        default:
            console.log('❓ Événement non traité :', event);
            break;
    }

    res.sendStatus(200);
});

async function handleIncomingMessage(data) {
    const { from, body } = data;

    console.log(`📨 Message de ${from} : ${body}`);

    // Exemple de logique : réponse automatique
    if (body.toLowerCase() === 'bonjour') {
        await reply(from, 'Salut ! Comment puis-je t’aider ?');
    }

    if (body.toLowerCase() === 'aide') {
        await reply(from, 'Voici les commandes disponibles : bonjour, aide, info');
    }

    if (body.toLowerCase() === 'info') {
        await reply(from, 'Bot WhatsApp connecté avec whatsapp-web.js 🟢');
    }
}

async function reply(to, message) {
    try {
        const res = await axios.post(WHATSAPP_API_URL, {
            to,
            message
        });
        console.log(`✅ Réponse envoyée à ${to}`);
    } catch (err) {
        console.error('❌ Erreur en envoyant la réponse :', err.message);
    }
}

app.listen(PORT, () => {
    console.log(`🚀 Serveur webhook en écoute sur http://localhost:${PORT}`);
});
