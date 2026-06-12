import os
import hashlib
import requests
import io
from bs4 import BeautifulSoup
from twilio.rest import Client
import pypdf

URL = "https://www.finp.it/i-convocati"
COGNOME = "ceffalia"
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")

def get_stored_hash():
    """Legge l'hash precedente dal Secret GitHub"""
    try:
        # Usiamo una variabile d'ambiente passata dal workflow
        return os.environ.get("PREV_HASH", "")
    except:
        return ""

def update_stored_hash(new_hash):
    """Aggiorna l'hash salvato tramite API GitHub"""
    try:
        import base64
        from nacl import encoding, public

        # Recupera la public key del repo per cifrare il secret
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        key_resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
            headers=headers
        )
        key_data = key_resp.json()
        public_key = public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key)
        encrypted = base64.b64encode(sealed_box.encrypt(new_hash.encode("utf-8"))).decode("utf-8")

        requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/PREV_HASH",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": key_data["key_id"]}
        )
        print(f"Hash aggiornato: {new_hash}")
    except Exception as e:
        print(f"Errore aggiornamento hash: {e}")

def get_page_links(soup):
    links = []
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.finp.it" + href
            links.append(href)
    return links

def read_pdf_text(pdf_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(pdf_url, headers=headers, timeout=15)
        reader = pypdf.PdfReader(io.BytesIO(r.content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Errore lettura PDF {pdf_url}: {e}")
        return ""

def get_content():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(URL, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    main = soup.find("main") or soup.find("article") or soup.find("div", class_="container")
    page_text = (main or soup).get_text(separator=" ", strip=True)

    pdf_links = get_page_links(soup)
    pdf_text = ""
    for link in pdf_links:
        print(f"Leggo PDF: {link}")
        pdf_text += read_pdf_text(link)

    full_text = page_text + " " + pdf_text
    has_athletes = any(k in full_text.lower() for k in ["criterio", "selezione", "kocaeli"]) and len(pdf_links) > 0
    figlio_convocato = COGNOME.lower() in full_text.lower()

    return full_text, has_athletes, figlio_convocato

def send_whatsapp(message):
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    client.messages.create(
        body=message,
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["TWILIO_WHATSAPP_TO"]
    )

def main():
    full_text, has_athletes, figlio_convocato = get_content()
    current_hash = hashlib.md5(full_text.encode()).hexdigest()
    prev_hash = get_stored_hash()

    print(f"Hash precedente: {prev_hash}")
    print(f"Hash corrente:   {current_hash}")

    if prev_hash == current_hash:
        print("Nessun cambiamento.")
        return

    # C'è un cambiamento — aggiorna l'hash e manda notifica
    update_stored_hash(current_hash)

    if figlio_convocato:
        send_whatsapp(
            "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
            "🎉 TUO FIGLIO CEFFALIA È STATO CONVOCATO!\n\n"
            "👉 https://www.finp.it/i-convocati"
        )
    elif has_athletes:
        send_whatsapp(
            "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
            "✅ CONVOCATI AGGIORNATI!\n\n"
            "👉 Controlla se c'è tuo figlio:\nhttps://www.finp.it/i-convocati"
        )
    else:
        send_whatsapp(
            "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
            "⚠️ La pagina è stata aggiornata.\n"
            "👉 https://www.finp.it/i-convocati"
        )
    print("CAMBIAMENTO RILEVATO - notifica inviata!")

if __name__ == "__main__":
    main()
