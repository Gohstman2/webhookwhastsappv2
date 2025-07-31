from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests

# === CONFIG ===
API_BASE = "https://senhatsappv2.onrender.com"  # Ton API Node.js pour WhatsApp
OPENROUTER_API_KEY = "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"

app = FastAPI()

# === Fonction pour envoyer un message WhatsApp via ton API Node.js ===
def send_whatsapp_message(number: str, message: str) -> bool:
    url = f"{API_BASE}/sendMessage"
    payload = {
        "number": number,
        "message": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        if data.get("success"):
            print(f"✅ Message envoyé à {number}")
            return True
        else:
            print(f"❌ Erreur envoi WhatsApp : {data.get('error', 'Échec inconnu')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur de connexion à l'API WhatsApp : {e}")
        return False


# === Fonction pour interroger l'IA via OpenRouter ===
def get_ai_response(message: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {"role": "user", "content": message}
        ]
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()

        # 🔹 Debug : Afficher la réponse brute
        print("\n=== Réponse API OpenRouter ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Extraction du texte de réponse
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return answer.strip() or "Réponse vide de l'IA."
    
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur réseau OpenRouter : {e}")
        return "Désolé, je rencontre un problème pour répondre (réseau)."
    except json.JSONDecodeError:
        print("⚠️ Erreur JSON de l'API OpenRouter.")
        return "Désolé, problème de lecture de la réponse de l'IA."
    except Exception as e:
        print(f"⚠️ Erreur inconnue OpenRouter : {e}")
        return "Désolé, je rencontre un problème pour répondre."


# === Route par défaut pour tester que le webhook tourne ===
@app.get("/")
def home():
    return {"status": "ok", "message": "Webhook actif ✅"}


# === Nouvelle route GET qui retourne du texte avec code 200 ===
@app.get("/status")
def status():
    return "Activer ✅"


# === Route Webhook pour recevoir les messages entrants ===
@app.post("/whatsapp")
async def receive_message(request: Request):
    data = await request.json()
    
    print(f"\n📩 Nouveau message reçu à {datetime.now()}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    sender = data.get("from")          # ex: "226XXXXXXXXX@c.us"
    message = data.get("body", "").strip()
    
    if not sender or not message:
        return {"status": "ignored"}
    
    number = "+" + sender.replace("@c.us", "")
    
    # 🔹 Gestion des commandes simples
    if message.lower() == ".ping":
        send_whatsapp_message(number, "pong ✅")
    else:
        # 🔹 Réponse automatique via IA
        ai_reply = get_ai_response(message)
        send_whatsapp_message(number, ai_reply)
    
    return {"status": "received"}
