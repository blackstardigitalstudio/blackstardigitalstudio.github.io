# -*- coding: utf-8 -*-
"""
genera.py — prepara il contenuto del giorno: immagine PNG + didascalia.
Non pubblica niente: si limita a mettere il file pronto nella cartella "pronti".
Sistema NUOVO e SEPARATO: non tocca nessun sistema dei clienti.
Made in Italy
"""
import json, os, random, sys, textwrap
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from filtro import pulisci

QUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(QUI, "fonte", "curiosita.json")
PRONTI = os.path.join(QUI, "pronti")
STORICO = os.path.join(QUI, "storico.json")

# --- aspetto -----------------------------------------------------------------
L, A = 1080, 1350                 # formato 4:5, il piu' alto che Instagram accetta
SFONDO      = (22, 19, 31)
ACCENTO     = (232, 145, 63)
TESTO       = (245, 240, 230)
TESTO_2     = (167, 158, 140)
MARGINE     = 90

FONT_DIR = r"C:\Windows\Fonts"
F_BOLD    = os.path.join(FONT_DIR, "segoeuib.ttf")
F_NORMALE = os.path.join(FONT_DIR, "segoeui.ttf")
F_SEMI    = os.path.join(FONT_DIR, "seguisb.ttf")

PROFILO = "@matteoblackstark"
APP_URL = "https://www.blackstardigitalstudio.com/app"


def font(percorso, dim):
    try:
        return ImageFont.truetype(percorso, dim)
    except OSError:
        return ImageFont.load_default(dim)


def senza_emoji(t):
    """Le emoji non si disegnano con i font di sistema: via dall'immagine."""
    return "".join(c for c in t if ord(c) < 0x2190).strip()


def storico():
    if os.path.exists(STORICO):
        with open(STORICO, encoding="utf-8") as f:
            return json.load(f)
    return {"usate": [], "conta": 0}


def salva_storico(s):
    with open(STORICO, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def scegli(dati, s):
    liberi = [c for c in dati if c["slug"] not in s["usate"]]
    if not liberi:                      # finite: si ricomincia, mescolate
        s["usate"] = []
        liberi = list(dati)
    return random.choice(liberi)


def spezza(d, testo, f, larghezza_px):
    """Manda a capo misurando i pixel veri, non contando i caratteri."""
    parole, righe, riga = testo.split(), [], ""
    for p in parole:
        prova = (riga + " " + p).strip()
        if d.textlength(prova, font=f) <= larghezza_px or not riga:
            riga = prova
        else:
            righe.append(riga)
            riga = p
    if riga:
        righe.append(riga)
    return righe


def disegna_righe(d, righe, f, y, colore, interlinea):
    for r in righe:
        w = d.textlength(r, font=f)
        d.text(((L - w) / 2, y), r, font=f, fill=colore)
        y += f.size + interlinea
    return y


def crea_immagine(c, percorso):
    img = Image.new("RGB", (L, A), SFONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, L, 10], fill=ACCENTO)          # barra d'accento in alto

    titolo = senza_emoji(c["titolo"])
    lead = senza_emoji(c["lead"])
    utile = L - MARGINE * 2                            # larghezza di lavoro

    # Il titolo e' quello che deve fermare il pollice: parte grande e scende
    # solo quanto basta per stare in cinque righe.
    for dim in (86, 78, 70, 62, 56, 50):
        f_tit = font(F_BOLD, dim)
        righe_tit = spezza(d, titolo, f_tit, utile)
        if len(righe_tit) <= 5:
            break

    f_kick = font(F_SEMI, 30)
    f_lead = font(F_NORMALE, 36)
    f_pie = font(F_SEMI, 28)

    IL_TIT, IL_LEAD = 14, 12
    righe_lead = spezza(d, lead, f_lead, utile - 60)[:4] if lead else []
    if lead and len(spezza(d, lead, f_lead, utile - 60)) > 4:
        righe_lead[-1] = righe_lead[-1].rstrip(" ,.;") + "..."

    # Altezze vere, per centrare davvero il blocco fra testata e piede
    h_kick = f_kick.size + 46
    h_tit = len(righe_tit) * (f_tit.size + IL_TIT)
    h_lead = (34 + 30 + len(righe_lead) * (f_lead.size + IL_LEAD)) if righe_lead else 0
    h_tot = h_kick + h_tit + h_lead

    ALTO, BASSO = 150, 200                             # aria in testa e sopra il piede
    y = ALTO + max(0, ((A - ALTO - BASSO) - h_tot) / 2)

    kick = "LO  SAPEVI  CHE..."
    w = d.textlength(kick, font=f_kick)
    d.text(((L - w) / 2, y), kick, font=f_kick, fill=ACCENTO)
    y += h_kick

    y = disegna_righe(d, righe_tit, f_tit, y, TESTO, IL_TIT)

    if righe_lead:
        y += 34
        d.line([(L / 2 - 44, y), (L / 2 + 44, y)], fill=ACCENTO, width=3)
        y += 30
        disegna_righe(d, righe_lead, f_lead, y, TESTO_2, IL_LEAD)

    # piede: categoria a sinistra, profilo a destra
    cat = senza_emoji(c["categoria"]).upper()
    d.line([(MARGINE, A - 136), (L - MARGINE, A - 136)], fill=(46, 41, 58), width=2)
    d.text((MARGINE, A - 104), cat, font=f_pie, fill=TESTO_2)
    w = d.textlength(PROFILO, font=f_pie)
    d.text((L - MARGINE - w, A - 104), PROFILO, font=f_pie, fill=ACCENTO)

    img.save(percorso, "PNG", optimize=True)


ETICHETTE = {
    "Storia": ["storia", "curiositastoriche"], "Scienza": ["scienza", "curiositascientifiche"],
    "Natura": ["natura"], "Spazio": ["spazio", "astronomia"], "Tecnologia": ["tecnologia"],
    "Cucina": ["cucina", "food"], "Psicologia": ["psicologia"], "Animali": ["animali"],
    "Arte": ["arte"], "Musica": ["musica"], "Cinema": ["cinema"], "Sport": ["sport"],
}


def didascalia(c, con_invito):
    cat = senza_emoji(c["categoria"])
    deep = c["deep"]
    if len(deep) > 420:
        deep = deep[:417].rsplit(" ", 1)[0] + "..."

    parti = [c["titolo"], "", c["lead"], "", deep]

    if con_invito:
        parti += ["", "—",
                  "Ne ho raccolte piu' di cento cosi', in un'app che ho fatto io. "
                  "E' gratis, senza pubblicita' e non ti chiede di registrarti. "
                  f"Il link e' nel profilo. ({APP_URL})"]

    tag = ["curiosita", "losapeviche", "imparasuinstagram"] + ETICHETTE.get(cat, [cat.lower()])
    parti += ["", " ".join("#" + t for t in tag)]
    return "\n".join(parti)


def main():
    if not os.path.exists(FONTE):
        print("Manca fonte/curiosita.json: lancia prima estrai.py")
        sys.exit(1)

    with open(FONTE, encoding="utf-8") as f:
        dati = pulisci(json.load(f)["curiosita"])

    quanti = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(PRONTI, exist_ok=True)
    s = storico()

    for _ in range(quanti):
        c = scegli(dati, s)
        s["usate"].append(c["slug"])
        s["conta"] += 1
        # regola dell'1 su 5: quattro contenuti regalano e basta, il quinto racconta l'app
        invito = (s["conta"] % 5 == 0)

        nome = f"{date.today().isoformat()}-{s['conta']:03d}-{c['slug'][:44]}"
        png = os.path.join(PRONTI, nome + ".png")
        txt = os.path.join(PRONTI, nome + ".txt")

        crea_immagine(c, png)
        with open(txt, "w", encoding="utf-8") as f:
            f.write(didascalia(c, invito))

        print(f"[{s['conta']:03d}] {'CON INVITO  ' if invito else '            '}{nome}.png")

    salva_storico(s)
    print(f"\nPronti in: {PRONTI}")


if __name__ == "__main__":
    main()
