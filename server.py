from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests
import re

# === CONFIG ===
API_BASE = "https://senhatsappv2.onrender.com"
OPENROUTER_API_KEY = "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"
mesClients = []


app = FastAPI()



#fonction pour extraire le ID
def extraire_id_utilisateur(message: str) -> int | None:
    """
    Extrait le premier ID utilisateur (une séquence de 6 à 12 chiffres) depuis un message.
    """
    # Normalise le message (minuscules, remplace les séparateurs classiques)
    message = message.lower().replace('\xa0', ' ')

    # Recherche une suite de chiffres assez longue (ID probable)
    match = re.findall(r'\b\d{6,12}\b', message)

    if match:
        return int(match[0])  # Retourne le premier ID trouvé
    return None

# ma fonction pour extraire un montant dans un message

def extraire_montant(message: str) -> int | None:
    """
    Extrait un montant en FCFA depuis un message texte.
    Gère les formats : 1000, 1 000, 1.000, 5 000 F, 1000fcfa, etc.
    Ignore les montants hors plage (par défaut entre 500 et 200000).
    """
    # Nettoyer le message : enlever les espaces non standard et normaliser
    message = message.lower().replace('\xa0', ' ').replace('fcfa', '').replace('f', '').replace('fr', '')
    message = message.replace('cfa', '').replace('fcf', '')
    
    # Trouver tous les nombres potentiels
    candidats = re.findall(r'\d[\d\s.,]*\d|\d+', message)

    for brut in candidats:
        # Enlever les espaces, points, virgules pour normaliser le nombre
        propre = re.sub(r'[^\d]', '', brut)
        try:
            montant = int(propre)
            if 500 <= montant <= 200000:
                return montant
        except ValueError:
            continue

    return None


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
        send_whatsapp_message(number, "pong ✅ v1.2")
        return {"status": "pong"}

    if msg_lc == "salut":
        send_whatsapp_message(number, "Oui salut ! Que puis-je faire pour vous ?")
        return {"status": "pong"}

    #veification pour agent depot retrait
    if msg_lc :
        if not mesClients:
            send_whatsapp_message(number, "Salut Bienvenue chez Rapide Cash\n Je suis un assistant virtuelle dite moi vous voulez : \n 1-UN DEPOT \n 2-UN RETRAIT \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
            mesClients.append({
    "number": number,
    "nom": "",
    "tache": "acceuil",
    "etape" : "",
    "data": []
})
    
            return {"status": "pong"}

    # Création d’un dictionnaire clé = numéro
    clients_dict = {client['number']: client for client in mesClients}

# Vérification
    if number in clients_dict:
        findClient = True
    else:
        findClient = False

    if not findClient :
        send_whatsapp_message(number, "Salut Bienvenue chez Rapide Cash\n Je suis un assiatant virtuelle dite moi vous voulez : \n 1-UN DEPOT \n 2-UN RETRAIT \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
        mesClients.append({
    "number": number,
    "nom": "",
    "tache": "acceuil",
    "etape" : "",
    "data": []
})
        


        
        
    
    for client in mesClients :
            if number == client['number'] :
                if client['tache'] == "acceuil" :
                    if msg_lc == "menu" :
                        client['tache'] = "acceuil"
                        client['etape'] = ""
                        client['data'] = []
                        send_whatsapp_message(number, "Salut Bienvenue chez Rapide Cash\n Je suis un assiatant virtuelle dite moi vous voulez : \n 1-UN DEPOT \n 2-UN RETRAIT \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
                        return {"status": "pong"}
                        
                    if msg_lc == "1" :
                        send_whatsapp_message(number, "Ok, Sur quelle bookmaker voulez vous deposez : \n 1- 1XBET  2-MELBET \n 3-BETWINNER  4-LINEBET \n 5-1WIN  6-WINWIN \n    7-888STARZ \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
                        client['tache'] = "depot"
                        client['etape'] = "bookmaker"
                        return {"status": "pong"}
                    else : 
                        send_whatsapp_message(number, "J'ai pas compris votre choix \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
                        return {"status": "pong"}
                if client['tache'] == "depot" :
                    if client['etape'] == "bookmaker" :
                        if msg_lc == "1" :
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "2":
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "3" :
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "4":
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "5":
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "7":
                            send_whatsapp_message(number, "Super ! *Combien voulez vous deposer sur votre compte ?* \n *envoyer uniquement le montant entre : 500 et 200 000 ; Exemple : 1000*")
                            client['tache'] = "depot"
                            client['etape'] = "montant"
                            return {"status": "pong"}
                        elif msg_lc == "stop":
                            send_whatsapp_message(number, "*Votre demande de depot a ete annuler*")
                            client['tache'] = "acceuil" 
                            client['etape'] = ""
                            client['data'] = []
                            send_whatsapp_message(number, "Vous voulez faire : \n 1-UN DEPOT \n 2-UN RETRAIT \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
                            return {"status": "pong"}
                        else :
                            send_whatsapp_message(number, "J'ai pas compris votre message , Si vous souhaitez tout annuler envoyer moi *stop*")
                            return {"status": "pong"}
                    if client['etape'] == "montant" :
                        montant = extraire_montant(msg_lc)
                        if montant :
                            send_whatsapp_message(number, f"Ok vous voulez un depot de {montant} Francs CFA \n Maintenant donner moi le ID de votre compte \n *S'il vous plait n'envoyer pas de capture*")
                            client['tache'] = "depot"
                            client['etape'] = "id"
                            return {"status": "pong"}
                        else :
                            send_whatsapp_message(number, "*Montant invalide* \n Envoyer moi le montant que vous souhaitez recharger, Exemple : 1000 ")
                            return {"status": "pong"}
                    if client['etape'] == "id" :
                        id = extraire_id_utilisateur(msg_lc)
                        if id:
                            send_whatsapp_message(number, f"Ok ! votre id est *{id}* \n Maintenant vous utiliser quelle reseaux pour le paiement \n 1-Orange Money \n 2-Moov Money \n 3-Telecel Money")
                            client['tache'] = "depot"
                            client['etape'] = "reseaux"
                            return {"status": "pong"}
                        elif msg_lc == "stop":
                            send_whatsapp_message(number, "*Votre demande de depot a ete annuler*")
                            client['tache'] = "acceuil" 
                            client['etape'] = ""
                            client['data'] = []
                            send_whatsapp_message(number, "Vous voulez faire : \n 1-UN DEPOT \n 2-UN RETRAIT \n *S'il vous plait envoyer uniquement le numero correspondant a votre choix*")
                            return {"status": "pong"}
                        else :
                            send_whatsapp_message(number, "*Je ne trouve pas votre id \n Envoyer moi uniquement le ID de votre compte,pas de capture \n *Exemple:897665403*")
                            return {"status": "pong"}
                    if client['etape'] == "reseaux" :
                        if msg_lc == "1" :
                            send_whatsapp_message(number, "Envoyer nous le montant en tapant : \n *144*2*1*04264642*1000#  Nom : *BOKOUM ISSIAKA* \n Valider avec votre SIM ORANGE BF puis envoyer moi le numero avec leauel vous avez fait le transfert")
                            return {"status": "pong"}
                        elif msg_lc == "2" :
                            send_whatsapp_message(number, "Envoyer nous le montant en tapant : \n *555*2*1*63290016*1000# Nom : *ISSIAKO BUSINESS* \n Valider avec votre SIM MOOV BF puis envoyer moi le numero avec leauel vous avez fait le transfert")
                            return {"status": "pong"}
                        elif msg_lc == "3" :
                            send_whatsapp_message(number, "Envoyer nous le montant en tapant : \n *808*2*1*58902040*1000# \n Valider avec votre SIM TELECEL BF puis envoyer moi le numero avec leauel vous avez fait le transfert")
                            return {"status": "pong"}
                        else :
                            send_whatsapp_message(number, "J'ai pas compris votre choix , Si vous souhaitez tout annuler envoyer moi *stop*")
                            
                            
                        
                                                  
                        
