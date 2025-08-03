from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests
import re
import uuid
import easyocr
from PIL import Image
import base64
import io

# === CONFIG ===
API_BASE = "https://senhatsappv2.onrender.com"
OPENROUTER_API_KEY = "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"
mesClients = []

app = FastAPI()


def ocr_depuis_media(media: dict) -> str:
    """
    Lit le texte d'une image WhatsApp reçue via media.
    
    :param media: dict contenant "data" (base64), "mimetype"
    :return: texte extrait
    """
    base64_data = media["data"]
    image_bytes = base64.b64decode(base64_data)
    image = Image.open(io.BytesIO(image_bytes))

    reader = easyocr.Reader(['fr', 'en'])  # langue : français et anglais
    result = reader.readtext(np.array(image), detail=0)

    return "\n".join(result)

#fonction pour envoyer un media
def envoyer_media_whatsapp(media: dict, numero: str) -> bool:
    """
    Envoie un média WhatsApp en base64 à un numéro via l'API /sendMedia.
    
    :param media: Dictionnaire contenant 'data', 'mimetype', et 'filename'
    :param numero: Numéro WhatsApp (ex: +22670123456)
    :return: True si succès, False sinon
    """
    if not media or "data" not in media or "mimetype" not in media:
        print("⚠️ Média invalide ou incomplet")
        return False

    url = f"{API_BASE}/sendMedia"
    payload = {
        "number": numero,
        "media": {
            "data": media["data"],  # base64
            "mimetype": media["mimetype"],
            "filename": media.get("filename", "fichier")  # nom par défaut
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()
        if result.get("success"):
            print(f"✅ Média envoyé à {numero}")
            return True
        else:
            print(f"❌ Erreur API : {result.get('error', 'Échec inconnu')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur de connexion API : {e}")
        return False
        #une deuxieme version de ma fonction pour envoyer des media + texte achrocher(caption)
def envoyer_media_whatsappV2(media: dict, numero: str, caption: str = "") -> bool:
    """
    Envoie un média à un numéro WhatsApp avec un texte (caption) accroché.
    
    :param media: dict contenant les clés 'data', 'mimetype', 'filename'
    :param numero: Numéro WhatsApp (ex: +22670123456)
    :param caption: Texte à attacher au média
    :return: True si succès, False sinon
    """
    url = f"{API_BASE}/sendMediaV2"

    payload = {
        "number": numero,
        "media": {
            "data": media["data"],
            "mimetype": media["mimetype"],
            "filename": media.get("filename", "media")
        },
        "caption": caption  # Texte accroché
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()
        if result.get("success"):
            print(f"✅ Média envoyé à {numero}")
            return True
        else:
            print(f"❌ Erreur API : {result.get('error', 'Échec inconnu')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur de connexion API : {e}")
        return False


# === UTILITAIRES ===
def extraire_numero_local(message: str) -> str | None:
    message = re.sub(r'[^\d]', '', message)
    if message.startswith("00226"):
        message = message[5:]
    elif message.startswith("226"):
        message = message[3:]
    elif message.startswith("00"):
        message = message[2:]
    match = re.search(r'\d{8}$', message)
    if match:
        return match.group(0)
    return None

def extraire_id_utilisateur(message: str) -> int | None:
    message = message.lower().replace('\xa0', ' ')
    match = re.findall(r'\b\d{6,12}\b', message)
    if match:
        return int(match[0])
    return None

def extraire_montant(message: str) -> int | None:
    message = message.lower().replace('\xa0', ' ').replace('fcfa', '').replace('f', '').replace('fr', '')
    message = message.replace('cfa', '').replace('fcf', '')
    candidats = re.findall(r'\d[\d\s.,]*\d|\d+', message)
    for brut in candidats:
        propre = re.sub(r'[^\d]', '', brut)
        try:
            montant = int(propre)
            if 500 <= montant <= 200000:
                return montant
        except ValueError:
            continue
    return None

# === WHATSAPP COMMUNICATION ===
def send_whatsapp_message(number: str, message: str) -> bool:
    url = f"{API_BASE}/sendMessage"
    payload = {"number": number, "message": message}
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

# === INTELLIGENCE ARTIFICIELLE ===
def get_ai_response(message: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": message}]
    }
    for attempt in range(2):
        try:
            print(f"🔹 Tentative {attempt+1} pour contacter OpenRouter...")
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip() or "Réponse vide de l'IA."
        except requests.exceptions.Timeout:
            if attempt == 0:
                continue
            return "Désolé, le serveur IA met trop de temps à répondre."
        except requests.exceptions.RequestException as e:
            return "Désolé, je rencontre un problème réseau pour répondre."
    return "Désolé, problème technique côté serveur IA."

# === ROUTES SIMPLES ===
@app.get("/")
def home():
    return {"status": "ok", "message": "Webhook actif ✅"}

@app.get("/status")
def status():
    return "Activer ✅"

# === WEBHOOK PRINCIPAL ===
@app.post("/whatsapp")
async def receive_message(request: Request):
    data = await request.json()
    sender = data.get("from")
    message = data.get("body", "").strip()
    media = data.get("media")
    
    

    number = "+" + sender.replace("@c.us", "")
    msg_lc = message.lower()
    
    if msg_lc == ".ping":
        send_whatsapp_message(number, "pong ✅ v2.1")
        return {"status": "pong"}
    
    if msg_lc == "salut":
        send_whatsapp_message(number, "Oui salut ! Que puis-je faire pour vous ?")
        return {"status": "pong"}

    # Initialisation du client
    clients_dict = {client['number']: client for client in mesClients}
    if number not in clients_dict:
        send_whatsapp_message(number, "Salut et bienvenue chez Rapide Cash.\nJe suis un assistant virtuel.\n1 - UN DÉPÔT\n2 - UN RETRAIT\n*Veuillez envoyer uniquement le numéro correspondant à votre choix.*")
        mesClients.append({
            "number": number,
            "nom": "",
            "tache": "acceuil",
            "etape": "",
            "data": [],
            "depots": [],
            "tacheId": ""
        })
        return {"status": "pong"}

    for client in mesClients:
        if number != client["number"]:
            continue

        if client["tache"] == "acceuil":
            if msg_lc == "menu":
                client.update({"tache": "acceuil", "etape": "", "data": [], "depots": []})
                send_whatsapp_message(number, "Menu:\n1 - UN DÉPÔT\n2 - UN RETRAIT")
                return {"status": "pong"}

            if msg_lc == "1":
                send_whatsapp_message(number, "Sur quel bookmaker voulez-vous déposer ?\n1- 1XBET\n2- MELBET\n3- BETWINNER\n4- LINEBET\n5- 1WIN\n6- WINWIN\n7- 888STARZ")
                client["tache"] = "depot"
                client["etape"] = "bookmaker"
                return {"status": "pong"}
            else:
                send_whatsapp_message(number, "Choix non compris. Veuillez envoyer uniquement un chiffre.")
                return {"status": "pong"}

        if client["tache"] == "depot":
            if client["etape"] == "bookmaker":
                if msg_lc in ["1", "2", "3", "4", "5", "6", "7"]:
                    send_whatsapp_message(number, "Super ! Combien voulez-vous déposer ? (Ex: 1000)")
                    client["etape"] = "montant"
                    return {"status": "pong"}
                if msg_lc == "stop":
                    client.update({"tache": "acceuil", "etape": "", "data": []})
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    return {"status": "pong"}
                send_whatsapp_message(number, "Choix non compris. Tapez 'stop' pour annuler.")
                return {"status": "pong"}

            if client["etape"] == "montant":
                montant = extraire_montant(msg_lc)
                if montant:
                    unique_id = str(uuid.uuid4())[:8]
                    depot_data = {
                        "montant": montant,
                        "idtrans": unique_id,
                        "idBookmaker": "",
                        "bookmaker": "",
                        "numero": "",
                        "reseaux": "",
                        "statut": "en cours"
                    }
                    client["depots"].append(depot_data)
                    client["etape"] = "id"
                    client["tacheId"] = unique_id
                    send_whatsapp_message(number, f"Vous voulez déposer {montant} FCFA. Quel est l'ID de votre compte ?")
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                else:
                    send_whatsapp_message(number, "Montant invalide. Veuillez envoyer un nombre entre 500 et 200000.")
                    return {"status": "pong"}

            if client["etape"] == "id":
                ident = extraire_id_utilisateur(msg_lc)
                if ident:
                    client["etape"] = "reseaux"
                    dernier_depot = client["depots"][-1] if client["depots"] else None
                    dernier_depot["idBookmaker"] = ident
                    send_whatsapp_message(number, f"Votre ID est {dernier_depot["idBookmaker"]}. Choisissez un réseau :\n1 - Orange Money\n2 - Moov Money\n3 - Telecel Money")
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    client.update({"tache": "acceuil", "etape": "", "data": []})
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    return {"status": "pong"}
                else:
                    send_whatsapp_message(number, "ID invalide. Envoyez uniquement les chiffres.")
                    return {"status": "pong"}

            if client["etape"] == "reseaux":
                dernier_depot = client["depots"][-1] if client["depots"] else None
                reseaux_messages = {
                    "1": f"Envoyez via Orange : *144*2*1*04264642*{dernier_depot['montant']}#\nNom : BOKOUM ISSIAKA",
                    "2": f"Envoyez via Moov : *555*2*1*63290016*{dernier_depot['montant']}#\nNom : ISSIAKO BUSINESS",
                    "3": f"Envoyez via Telecel : *808*2*1*58902040*{dernier_depot['montant']}#\nNom : BOKOUM ISSIAKA"
                }
                if msg_lc in reseaux_messages:
                    dernier_depot = client["depots"][-1] if client["depots"] else None
                    client["etape"] = "numero"
                    dernier_depot["reseaux"] = "reseaux"
                    send_whatsapp_message(number, reseaux_messages[msg_lc] + "\nEnsuite, envoyez le numéro utilisé pour la transaction.")
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    client.update({"tache": "acceuil", "etape": "", "data": []})
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    return {"status": "pong"}
                else:
                    send_whatsapp_message(number, "Choix non compris. Tapez 'stop' pour annuler.")
                    return {"status": "pong"}

            if client["etape"] == "numero":
                numero = extraire_numero_local(msg_lc)
                dernier_depot = client["depots"][-1] if client["depots"] else None
                dernier_depot["numero"] = numero
                if numero:
                    dernier_depot = client["depots"][-1] if client["depots"] else None
                    dernier_depot["numero"] = numero
                    send_whatsapp_message(number, f"Vous avez utilisé le numéro {dernier_depot["numero"]}. Merci de nous envoyer une capture d'écran de confirmation de la transaction.")
                    client["etape"] = "capture"
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    client.update({"tache": "acceuil", "etape": "", "data": []})
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    return {"status": "pong"}
                else:
                    send_whatsapp_message(number, "Numéro invalide. Envoyez uniquement les chiffres.")
                    return {"status": "pong"}
            if client["etape"] == "capture":
                if media :
                    send_whatsapp_message(number, f"Votre demande de depot a bien ete prix en compte , merci de nous contacter si votre compte n'est pas credite dans 5minutes")
                    client["etape"] = "attente"
                    texteTrans = ocr_depuis_media(media)
                    envoyer_media_whatsappV2(media,"+22654641531",f"*Une Nouvelle demande de depot*\n {texteTrans}")
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    return {"status": "pong"}
                else : 
                    send_whatsapp_message(number, "Veuillez nous envoyer une capture d'ecran de votre message de transaction")
                    return {"status": "pong"}
                    

    return {"status": "traité"}
