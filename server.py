from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests

# === CONFIG ===
API_BASE = "https://senhatsappv2.onrender.com"
OPENROUTER_API_KEY = "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"

app = FastAPI()


# === Fonction pour envoyer un message WhatsApp ===
def send_whatsapp_message(number: str, message: str) -> bool:
    url = f"{API_BASE}/sendMessage"
    payload = {
        "number": number,
        "message": message
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()
        if data.get("success"):
            print(f"✅ Message envoyé à {number}")
            return True
        else:
            print(f"❌ Erreur WhatsApp : {data.get('error', 'Échec inconnu')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur de connexion WhatsApp : {e}")
        return False


# === Fonction pour envoyer des boutons WhatsApp ===
def send_whatsapp_buttons(number: str, text: str, buttons: list, title: str = "", footer: str = "") -> bool:
    url = f"{API_BASE}/sendButtons"
    payload = {
        "number": number,
        "text": text,
        "title": title,
        "footer": footer,
        "buttons": buttons
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()
        if data.get("success"):
            print(f"✅ Boutons envoyés à {number}")
            return True
        else:
            print(f"❌ Erreur envoi boutons : {data.get('error', 'Échec inconnu')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur connexion Node.js (boutons) : {e}")
        return False


# === Fonction pour obtenir une réponse IA ===
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

    for attempt in range(2):
        try:
            print(f"🔹 Tentative {attempt+1} pour contacter OpenRouter...")
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            print("\n=== Réponse OpenRouter ===")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip() or "Réponse vide de l'IA."
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout atteint (60s) - tentative {attempt+1}")
            if attempt == 0:
                print("↻ Nouvelle tentative...")
                continue
            return "Désolé, le serveur IA met trop de temps à répondre."
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erreur réseau OpenRouter : {e}")
            return "Désolé, je rencontre un problème réseau pour répondre."

    return "Désolé, problème technique côté serveur IA."


# === Routes simples ===
@app.get("/")
def home():
    return {"status": "ok", "message": "Webhook actif ✅"}

@app.get("/status")
def status():
    return "Activer ✅"


# === Webhook WhatsApp ===
@app.post("/whatsapp")
async def receive_message(request: Request):
    data = await request.json()

    print(f"\n📩 Nouveau message reçu à {datetime.now()}")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    sender = data.get("from")
    message = data.get("body", "").strip()

    if not sender or not message:
        print("⚠️ Message ignoré : pas de sender ou body")
        return {"status": "ignored"}

    number = "+" + sender.replace("@c.us", "")

    # Commandes
    msg_lc = message.lower()

    if msg_lc == ".ping":
        send_whatsapp_message(number, "pong ✅")
        return {"status": "pong"}

    if msg_lc == "salut":
        send_whatsapp_message(number, "Oui salut ! Que puis-je faire pour vous ?")
        return {"status": "pong"}

    if msg_lc == ".depot":
        # Envoie d’un bouton "Faire un dépôt"
        send_whatsapp_buttons(
            number,
            text="Souhaitez-vous créer un dépôt maintenant ?",
            title="Assistant WhatsApp",
            footer="Appuyez sur le bouton ci-dessous",
            buttons=[
                {"body": "Faire un dépôt"}
            ]
        )
        return {"status": "bouton depot envoyé"}

    # Sinon, réponse IA
    ai_reply = get_ai_response(message)
    send_whatsapp_message(number, ai_reply)

    return {"status": "received", "reply": ai_reply}
