# -*- coding: utf-8 -*-
"""
estrai.py — legge le pagine delle curiosita' dal sito e le mette in un JSON unico.
Sistema NUOVO e SEPARATO: non tocca nessun sistema dei clienti.
Made in Italy
"""
import json, os, re, sys, html, urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(QUI, "fonte")
USCITA = os.path.join(QUI, "fonte", "curiosita.json")

RAW = "https://raw.githubusercontent.com/blackstardigitalstudio/blackstardigitalstudio.github.io/main/losapevi/"


def pulisci(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return html.unescape(t).strip()


def campo(testo, pattern):
    m = re.search(pattern, testo, re.S)
    return pulisci(m.group(1)) if m else ""


def immagine(htm):
    """La foto che Matteo ha gia' scelto per ogni curiosita' sul sito."""
    m = re.search(r'<img class="hero" src="([^"]+)"', htm)
    if not m:
        m = re.search(r'property="og:image" content="([^"]+)"', htm)
    return html.unescape(m.group(1)) if m else ""


def leggi_curiosita(htm, slug):
    titolo = campo(htm, r'<h1>(.*?)</h1>')
    if not titolo:
        return None
    return {
        "slug": slug,
        "titolo": titolo,
        "categoria": campo(htm, r'<span class="chip">(.*?)</span>'),
        "lead": campo(htm, r'<p class="lead">(.*?)</p>'),
        "deep": campo(htm, r'<div class="deep">(.*?)</div>'),
        "url": "https://www.blackstardigitalstudio.com/curiosita/c/" + slug,
        "immagine": immagine(htm),
    }


def da_cartella(cartella):
    fuori = []
    for nome in sorted(os.listdir(cartella)):
        if not nome.endswith(".html"):
            continue
        with open(os.path.join(cartella, nome), encoding="utf-8") as f:
            c = leggi_curiosita(f.read(), nome[:-5])
        if c:
            fuori.append(c)
    return fuori


def da_rete():
    """Se non c'e' una copia locale, prende l'elenco dal sitemap online."""
    print("Nessuna copia locale: scarico dal sito...")
    with urllib.request.urlopen(RAW + "sitemap.xml", timeout=30) as r:
        sitemap = r.read().decode("utf-8", "ignore")
    slug = [s.rstrip("/").split("/")[-1].replace(".html", "")
            for s in re.findall(r"<loc>(.*?)</loc>", sitemap) if "/c/" in s]
    fuori = []
    for i, s in enumerate(slug, 1):
        try:
            with urllib.request.urlopen(RAW + "c/" + s + ".html", timeout=30) as r:
                c = leggi_curiosita(r.read().decode("utf-8", "ignore"), s)
            if c:
                fuori.append(c)
            print(f"  {i}/{len(slug)} {s[:50]}")
        except Exception as e:
            print(f"  ! salto {s}: {e}")
    return fuori


def main():
    locale = os.path.join(FONTE, "c")
    dati = da_cartella(locale) if os.path.isdir(locale) else da_rete()

    if not dati:
        print("Non ho trovato nessuna curiosita'. Controlla la cartella fonte/c oppure la rete.")
        sys.exit(1)

    os.makedirs(FONTE, exist_ok=True)
    with open(USCITA, "w", encoding="utf-8") as f:
        json.dump({"totale": len(dati), "curiosita": dati}, f, ensure_ascii=False, indent=2)

    print(f"\nOK: {len(dati)} curiosita' salvate in {USCITA}")
    categorie = {}
    for c in dati:
        categorie[c["categoria"]] = categorie.get(c["categoria"], 0) + 1
    for k, v in sorted(categorie.items(), key=lambda x: -x[1]):
        # la console di Windows non digerisce le emoji: le tolgo solo dalla stampa
        etichetta = k.encode("ascii", "ignore").decode().strip() or "(senza categoria)"
        print(f"  {v:3d}  {etichetta}")


if __name__ == "__main__":
    main()
