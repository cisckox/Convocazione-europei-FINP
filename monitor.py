import os
import hashlib
import requests
import io
from bs4 import BeautifulSoup
from twilio.rest import Client
import pypdf

URL = "https://www.finp.it/i-convocati"
PREV_HASH_FILE = "last_hash.txt"
COGNOME = "ceffalia"

def get_page_links(soup):
    """Trova tutti i link a PDF nella pagina"""
    links = []
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.finp.it" + href
            links.append(href)
    return links

def read_pdf_text(pdf_url):
    """Scarica e legge il testo di un PDF"""
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

    # Testo della pagina (solo contenuto principale)
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="container")
    page_text = (main or soup).get_text(separator=" ", strip=True)

    # Leggi tutti i PDF presenti nella pagina
    pdf_links = get_page_links(soup)
    pdf_text = ""
    for link in pdf_links:
        print(f"Leggo PDF: {link}")
        pdf_text += read_pdf_text(link)

    full_text = page_text + " " + pdf_text

    # Controlla se ci sono convocati
    keywords = ["convocato", "atleta", "criterio", "selezione", "kocaeli"]
    has_athletes = any(k in full_text.lower() for k in keywords) and len(pdf_links) > 0

    # Cerca il cognome nel testo della pagina E nei PDF
    figlio_convocato = COGNOME.lower() in full_text.lower()

    return full_text, has_athletes, figlio_convocato, pdf_links

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
    full_text, has_athletes, figlio_convocato, pdf_links = get_content()
    current_hash = hashlib.md5(full_text.encode()).hexdigest()

    prev_hash = ""
    if os.path.exists(PREV_HASH_FILE):
        with open(PREV_HASH_FILE) as f:
            prev_hash = f.read().strip()

    with open(PREV_HASH_FILE, "w") as f:
        f.write(current_hash)

    # Notifica immediata se trova il cognome (indipendentemente dai cambiamenti)
    if figlio_convocato:
        print("FIGLIO CONVOCATO!")
        send_whatsapp(
            "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
            "🎉 TUO FIGLIO CEFFALIA È STATO CONVOCATO!\n\n"
            "👉 Vai subito qui:\nhttps://www.finp.it/i-convocati"
        )
    elif prev_hash and current_hash != prev_hash:
        if has_athletes:
            send_whatsapp(
                "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
                "✅ I CONVOCATI SONO STATI PUBBLICATI!\n\n"
                "👉 Controlla se c'è tuo figlio:\nhttps://www.finp.it/i-convocati"
            )
        else:
            send_whatsapp(
                "🏊 NAZIONALE PARALIMPICA NUOTO\n\n"
                "⚠️ La pagina convocati è stata aggiornata.\n"
                "👉 https://www.finp.it/i-convocati"
            )
        print("CAMBIAMENTO RILEVATO!")
    else:
        print("Nessun cambiamento.")

if __name__ == "__main__":
    main()
