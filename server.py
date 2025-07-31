from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests

# === CONFIG ===
API_BASE = "https://senhatsappv2.onrender.com"  # Ton API Node.js sur Render

app = FastAPI()

# === Fonction pour envoyer un message via ton API Node.js ===
def send_whatsapp_message(number: str, message: str) -> bool:
    """
    Envoie un message WhatsApp via l'API Node.js.
    """
    url = f"{API_BASE}/sendMessage"
    payload = {
        "number": number,
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get("success"):
            print("✅ Message envoyé avec succès !")
            return True
        else:
            print(f"❌ Erreur : {data.get('error', 'Échec d’envoi')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur de connexion à l'API : {e}")
        return False


@app.get("/")
def home():
    return {"status": "ok", "message": "Webhook actif ✅"}


# === Route Webhook pour recevoir les messages entrants ===
@app.post("/whatsapp")
async def receive_message(request: Request):
    data = await request.json()
    
    # Log du message
    print(f"\n📩 Nouveau message reçu à {datetime.now()}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # On récupère le numéro et le contenu du message
    sender = data.get("from")          # ex: "226XXXXXXXXX@c.us"
    message = data.get("body", "").strip()
    
    # Exemple de réponse automatique
    if message == ".ping":
        # On enlève le "@c.us" pour avoir le format international ex: +226XXXXXXX
        number = "+" + sender.replace("@c.us", "")
        send_whatsapp_message(number, "pong")
    
    return {"status": "received"}
