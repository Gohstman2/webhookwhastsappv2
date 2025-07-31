const express = require('express');
const { Client } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

let qrCodeBase64 = null;
let authenticated = false;
let client;

// 🌍 Ton serveur Python distant
const REMOTE_SESSION_URL = 'https://sendfiles.pythonanywhere.com/api';

// 📥 Récupérer session distante
async function fetchSessionFromRemote() {
  try {
    const res = await fetch(`${REMOTE_SESSION_URL}/getSession`);
    if (!res.ok) throw new Error('Session non trouvée');
    const session = await res.json();
    return session;
  } catch (error) {
    console.warn('⚠️ Aucune session trouvée sur le serveur distant');
    return null;
  }
}

// 🚀 Démarrer le client WhatsApp
async function initClient() {
  const session = await fetchSessionFromRemote();

  client = new Client({
    session,
    puppeteer: { headless: true, args: ['--no-sandbox'] },
  });

  client.on('qr', async (qr) => {
    console.log('📲 QR généré');
    qrCodeBase64 = await QRCode.toDataURL(qr);
    authenticated = false;
  });

  client.on('authenticated', async (session) => {
    console.log('✅ Authentifié');
    authenticated = true;
    qrCodeBase64 = null;

    try {
      await fetch(`${REMOTE_SESSION_URL}/saveSession`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(session),
      });
      console.log('☁️ Session sauvegardée sur le serveur distant');
    } catch (err) {
      console.error('❌ Erreur lors de la sauvegarde distante', err.message);
    }
  });

  client.on('auth_failure', (msg) => {
    console.error('❌ Authentification échouée :', msg);
    authenticated = false;
  });

  client.on('ready', () => {
    console.log('🤖 Client prêt');
    authenticated = true;
    qrCodeBase64 = null;
  });

  client.initialize();
}

initClient();

// === ROUTES ===

app.get('/auth', (req, res) => {
  if (authenticated) {
    return res.json({ status: 'authenticated' });
  } else if (qrCodeBase64) {
    return res.json({ status: 'scan me', qr: qrCodeBase64 });
  } else {
    return res.json({ status: 'waiting for qr...' });
  }
});

app.get('/checkAuth', (req, res) => {
  res.json({ status: authenticated ? 'authenticated' : 'not authenticated' });
});

app.post('/sendMessage', async (req, res) => {
  const { number, message } = req.body;

  if (!authenticated) {
    return res.status(401).json({ error: 'Client non authentifié' });
  }

  if (!number || !message) {
    return res.status(400).json({ error: 'Numéro et message requis' });
  }

  const formatted = number.replace('+', '') + '@c.us';

  try {
    await client.sendMessage(formatted, message);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(port, () => {
  console.log(`🚀 Serveur WhatsApp en ligne sur http://localhost:${port}`);
});
