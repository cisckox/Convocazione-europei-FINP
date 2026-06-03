import os
import hashlib
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client

URL = "https://www.finp.it/i-convocati"
PREV_HASH_FILE = "last_hash.txt"

def get_content():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(URL, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="container")
    if main:
        text = main.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)
    
    keywords = ["convocato", "atleta", "classe", "staffetta", "nuoto"]
    has_athletes = any(k in text.lower() for k in keywords)

    cognome = "ceffalia"
    figlio_convocato = cognome.lower() in text.lower()
    
    return text, has_athletes, figlio_convocato

def send_whatsapp(message):
    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"]
    )
    client.messages.create(
        body=message,
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["TWILIO_WHATSAPP_TO"]
    )

def main():
    text, has_athletes, figlio_convocato = get_content()
    current_hash = hashlib.md5(text.encode()).hexdigest()

    prev_hash = ""
    if os.path.exists(PREV_HASH_FILE):
        with open(PREV_HASH_FILE) as f:
            prev_hash = f.read().strip()

    with open(PREV_HASH_FILE, "w") as f:
        f.write(current_hash)

    if prev_hash and current_hash != prev_hash:
        if figlio_convocato:
            msg = (
                "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
                "🎉 ANDREA CEFFALIA È STATO CONVOCATO!\n\n"
                "👉 Vai a vedere:\nhttps://www.finp.it/i-convocati"
            )
        elif has_athletes:
            msg = (
                "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
                "✅ I CONVOCATI SONO STATI PUBBLICATI!\n\n"
                "👉 Vai a vedere:\nhttps://www.finp.it/i-convocati"
            )
