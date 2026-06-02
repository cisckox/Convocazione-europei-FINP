import os
import hashlib
import requests
from bs4 import BeautifulSoup
from twilio.rest import Client

URL = os.environ["TARGET_URL"]
PREV_HASH_FILE = "last_hash.txt"

def get_page_text(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    # Prende tutto il testo visibile della pagina
    return soup.get_text(separator=" ", strip=True)

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
    text = get_page_text(URL)
    current_hash = hashlib.md5(text.encode()).hexdigest()

    # Leggi hash precedente (salvato come artifact nel workflow)
    prev_hash = ""
    if os.path.exists(PREV_HASH_FILE):
        with open(PREV_HASH_FILE) as f:
            prev_hash = f.read().strip()

    # Salva hash corrente
    with open(PREV_HASH_FILE, "w") as f:
        f.write(current_hash)

    if prev_hash and current_hash != prev_hash:
        print("CAMBIAMENTO RILEVATO!")
        send_whatsapp(
            f"🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
            f"La pagina dei convocati è stata aggiornata!\n\n"
            f"👉 Controlla qui: {URL}"
        )
    else:
        print("Nessun cambiamento.")

if __name__ == "__main__":
    main()
