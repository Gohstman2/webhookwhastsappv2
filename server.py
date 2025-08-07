from fastapi import FastAPI, Request
from datetime import datetime
import json
import requests
import re
import uuid
from urllib.parse import urlencode



# === CONFIG ===
API_BASE = "https://senhatsappv3.onrender.com"
OPENROUTER_API_KEY = "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"
mesClients = []
adminNumber = "+22654641531"

app = FastAPI()


def extraire_numero_apres_phrase(texte: str) -> str | None:
    pattern = r"Whatsapp du client\s*:\s*(\+?\d+)"
    match = re.search(pattern, texte, re.IGNORECASE)
    if match:
        return match.group(1)
    return None



def get_unique_id(text):
    match = re.search(r"uniqueID\s*:\s*([^\s]+)", text)
    if match:
        return match.group(1)  # La valeur trouvée
    return None

# Exemple d'utilisation
texte = "Voici le code uniqueID : 8f14d3b0 à utiliser."
unique_id = get_unique_id(texte)

print(unique_id)  # Résultat : 8f14d3b0

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
@app.post("/traiter_depot")
async def traiter_depot(request: Request):
    """
    Valide ou rejette une demande de dépôt.
    Body attendu :
      {
        "number": "+22670123456",
        "idtrans": "abc123ef",
        "etat": "valider" ou "rejeter",
        "cause": "Raison du rejet" (facultatif, requis si rejet)
      }
    """
    data = await request.json()
    number = data.get("number")
    idtrans = data.get("idtrans")
    etat = data.get("etat", "").lower()
    cause = data.get("cause", "").strip()
    
    if not number or not idtrans or etat not in ["valider", "rejeter"]:
        raise HTTPException(status_code=400, detail="Champs number, idtrans et etat (valider/rejeter) sont requis")

    if etat == "rejeter" and not cause:
        raise HTTPException(status_code=400, detail="Le champ 'cause' est requis pour un rejet")

    for client in mesClients:
        if client["number"] == number:
            for depot in client.get("depots", []):
                if depot["idtrans"] == idtrans:
                    depot["statut"] = etat
                    if etat == "valider":
                        send_whatsapp_message(
                            number,
                            f"✅ Votre dépôt de {depot['montant']} FCFA sur {client['bookmaker']} a été validé. Merci pour votre confiance."
                        )
                        client["etape"] = "clientPret"
                    else:
                        # On stocke aussi la cause dans le dépôt
                        send_whatsapp_message(
                            number,
                            f"❌ Votre demande de dépôt a été rejetée.\n📌 Raison : \n\nSi vous pensez qu'il s'agit d'une erreur, contactez notre support."
                        )
                    return {"status": "ok", "message": f"Dépôt {etat} avec succès."}

    raise HTTPException(status_code=404, detail="Client ou dépôt introuvable")


# === WEBHOOK PRINCIPAL ===
@app.post("/whatsapp")
async def receive_message(request: Request):
    data = await request.json()
    sender = data.get("from")
    message = data.get("body", "").strip()
    media = data.get("media")
    context = data.get("context")
    
    

    number = "+" + sender.replace("@c.us", "")
    msg_lc = message.lower()
    
    if msg_lc == ".ping":
        send_whatsapp_message(number, "pong ✅ v2.5")
        return {"status": "pong"}


    
    if msg_lc == "salut":
        send_whatsapp_message(number, "Oui salut ! Que puis-je faire pour vous ?")
        return {"status": "pong"}

    # Initialisation du client
    clients_dict = {client['number']: client for client in mesClients}
    if number not in clients_dict and number != adminNumber:
        send_whatsapp_message(number, "Salut et bienvenue chez Rapide Cash.\nJe suis un assistant virtuel.\n1 - UN DÉPÔT\n2 - UN RETRAIT\n*Veuillez envoyer uniquement le numéro correspondant à votre choix.*")
        mesClients.append({
            "number": number,
            "nom": "",
            "tache": "acceuil",
            "etape": "",
            "data": [],
            "depots": [],
            "tacheId": "",
            "bookmaker" :""
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
                    if msg_lc == "1":
                        client["bookmaker"] ="1Xbet"
                    elif msg_lc == "2":
                        client["bookmaker"] ="Melbet"
                    elif msg_lc == "3":
                        client["bookmaker"] ="Betwenner"
                    elif msg_lc == "4" :
                        client["bookmaker"] ="Linebet"
                    elif msg_lc == "5":
                        client["bookmaker"] ="1Win"
                    elif msg_lc == "6":
                        client["bookmaker"] ="Winwin"
                    else :
                        client["bookmaker"] ="888Starz"
                    
                        
                    send_whatsapp_message(number, f"Super ! Combien voulez-vous déposer sur {client['bookmaker']} ? (Ex: 1000)")
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
                    send_whatsapp_message(number, f"Vous voulez déposer {montant} FCFA sur {client['bookmaker']}  . Envoyer moi le ID de votre compte {client['bookmaker']}")
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
                    send_whatsapp_message(number, f"Votre ID est {dernier_depot['idBookmaker']}. Choisissez un réseau :\n1 - Orange Money\n2 - Moov Money\n3 - Telecel Money")
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
                    "1": f"Envoyez {dernier_depot['montant']} FCFA via Orange au numero 04264642: *144*2*1*04264642*{dernier_depot['montant']}#\nNom : BOKOUM ISSIAKA",
                    "2": f"Envoyez {dernier_depot['montant']} FCFA via Moov au numero 63290016: *555*2*1*63290016*{dernier_depot['montant']}#\nNom : ISSIAKO BUSINESS",
                    "3": f"Envoyez {dernier_depot['montant']} FCFA via Telecel : *808*2*1*58902040*{dernier_depot['montant']}#\nNom : BOKOUM ISSIAKA"
                }
                if msg_lc in reseaux_messages:
                    dernier_depot = client["depots"][-1] if client["depots"] else None
                    client["etape"] = "numero"
                    if msg_lc == "1":
                        dernier_depot["reseaux"] = "Orange"
                    elif msg_lc == "2" :
                        dernier_depot["reseaux"] = "Moov"
                    else :
                        dernier_depot["reseaux"] = "Telecel"
                    send_whatsapp_message(number, reseaux_messages[msg_lc] + f"\n Et envoyez moi votre numero {dernier_depot['reseaux']} Money que vous que vous avez utiliser.")
                    return {"status": "pong"}
                elif msg_lc == "stop":
                    
                    client.update({"tache": "acceuil", "etape": ""})
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
                    dernier_depot = client["depots"][-1] if client["depots"] else None
                    send_whatsapp_message(number, f"Votre demande de depot a bien ete prix en compte , merci de nous contacter si votre compte n'est pas credite dans 5minutes")
                    client["etape"] = "attente"
                    PAGE_VALIDATION = "https://bkmservices.netlify.app/transactions_status"
                    # Données nécessaires
                    number = client["number"]
                    idtrans = dernier_depot["idtrans"]
                    serveur = "https://webhookwhastsappv2-1.onrender.com/traiter_depot"

                    # Construire l'URL avec les paramètres encodés
                    

                    params = urlencode({
                    "number": number,
                    "idtrans": idtrans,
                    "serveur": serveur
                        })
                    url_validation = f"{PAGE_VALIDATION}?{params}"

                    
                    # Construire le message WhatsApp
                    message = (
                    "*📥 Nouvelle demande de dépôt*\n"
                    f"🆔 uniqueID : {dernier_depot['idtrans']}\n"
                    f"🔸 *Bookmaker* : {client['bookmaker']}\n"
                    f"🆔 *ID* : {dernier_depot['idBookmaker']}\n"
                    f"💰 *Montant* : {dernier_depot['montant']} FCFA\n"
                    f"📞 *Numéro {dernier_depot['reseaux']}* : {dernier_depot['numero']}\n\n"
                    f"📞 *Whatsapp du client* : {number}"
                    )

                    # Envoyer le média avec le message
                    envoyer_media_whatsappV2(media,"+22654641531",message)
                    send_whatsapp_message("+22654641531", f"{dernier_depot['idBookmaker']}") 

                    return {"status": "pong"}
                elif msg_lc == "stop":
                    send_whatsapp_message(number, "Votre demande de dépôt a été annulée. Retour au menu principal.")
                    send_whatsapp_message(number, "Choisissez :\n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    return {"status": "pong"}
                else : 
                    send_whatsapp_message(number, "Veuillez nous envoyer une capture d'ecran de votre message de transaction")
                    return {"status": "pong"}
            if client["etape"] == "attente":
                if media:
                    send_whatsapp_message(number, f"Vous avez une demande de {client['tache']} \n Merci de patientez nous vous notifierons une fois terminer.\nSi votre demande prend trop de temps contactez nous : \nOrange : +22654641531\nMoov : +22663290016")
                    return {"status": "pong"}
                elif msg_lc =="Stop" :
                    send_whatsapp_message(number, f"Vous ne pouvez plus annuler cette demande {client['tache']} \n Patienter que le systheme, approuve ou rejette avant de faire une nouvelle demande\nSi votre demande prend trop de temps contactez nous : \nOrange : +22654641531\nMoov : +22663290016")
                    return {"status": "pong"}
                else:
                    send_whatsapp_message(number, f"Vous avez une demande de {client['tache']} \n Merci de patientez nous vous notifierons une fois terminer.\nSi votre demande prend trop de temps contactez nous : \nOrange : +22654641531\nMoov : +22663290016")
                    return {"status": "pong"} 
            if client["etape"] == "clientPret":
                if msg_lc :
                    send_whatsapp_message(number, "Salut, Choisissez une operation : \n 1-DEPOT \n 2-Retrait \nEnvoyez uniquement le numero correspondant a votre choix")
                    client["tache"] = "acceuil"
                    return {"status": "pong"}
            
    
                
    if number == adminNumber :
        if context :
            contextMsg = context.get("body", "")
            if msg_lc == "valider":
                idtrans = get_unique_id(contextMsg)
                whatsappNumber = extraire_numero_apres_phrase(contextMsg)
                for client in mesClients:
                    if client["number"] == whatsappNumber:
                        for depot in client.get("depots", []):
                            if depot["idtrans"] == idtrans:
                                depot["statut"] = "Valider"
                                send_whatsapp_message(whatsappNumber, "Votre compte a ete crediter")
                                send_whatsapp_message(number, f"Vous avez valider cette demande : {idtrans}")
                                client["etape"] = "clientPret"
                                return {"status": "pong"}
                        send_whatsapp_message(number, f"Je ne trouve plus la demande de depot veuillez m'envoyer le uniqueID de la demande")
                        return {"status": "pong"}
            else :
                send_whatsapp_message(number, f"J'ai pas compris compris votre message envoyerz moi \n Valider : si le depot est valider \n Rejeter : si la demande est rejeter")
                return {"status": "pong"}
                
        else:
            send_whatsapp_message(number, "Vous devez repondre e un messge en le glissant de vers la droite pour que je puisse vous comprendre")
            return {"status": "pong"}
                
                
                    

    return {"status": "traité"}
