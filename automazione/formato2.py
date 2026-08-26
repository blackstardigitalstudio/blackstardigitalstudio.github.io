# -*- coding: utf-8 -*-
"""
formato2.py — il formato "rivelazione": la risposta si nasconde e poi arriva.

Il difetto del formato vecchio non era l'aspetto: era che il titolo REGALA la
risposta nei primi due secondi. "I gatti hanno 32 muscoli per ogni orecchio":
letto, capito, scrollo. Non c'e' nessun motivo per restare.

Qui la parola chiave (il numero, di solito) e' coperta da un blocco arancione.
Il cervello vede il buco e vuole riempirlo — e per riempirlo deve restare.
Poi la parola arriva, grande, in giallo.

Tre tempi: DOMANDA (coperta) -> RISPOSTA (rivelata) -> SPIEGAZIONE.
Made in Italy
"""
import os, re, sys
from PIL import Image, ImageDraw

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
from genera_reel import (font, senza_emoji, spezza, sfondo_con_foto, da_accendere,
                         F_BOLD, F_NORMALE, F_SEMI, L, A, SFONDO, ACCENTO,
                         TESTO, TESTO_2, EVIDENZA, MARGINE, PROFILO)


def parola_chiave(titolo):
    """Quale parola coprire: il numero, se c'e'. E' sempre quella che
    regala la risposta."""
    for p in titolo.split():
        pulita = p.strip(".,;:!?\"'()")
        if any(ch.isdigit() for ch in pulita):
            return pulita
    for p in titolo.split():
        pulita = p.strip(".,;:!?\"'()")
        if da_accendere(p) and len(pulita) > 3:
            return pulita
    return None


def disegna(c, fase, percorso):
    """fase 0 = coperta · 1 = rivelata · 2 = con la spiegazione"""
    img = sfondo_con_foto(c, obbligatoria=True)
    d = ImageDraw.Draw(img)

    titolo = senza_emoji(c["titolo"])
    lead = senza_emoji(c["lead"])
    chiave = parola_chiave(titolo)
    utile = L - MARGINE * 2

    for dim in (98, 88, 78, 70, 62, 56):
        f_tit = font(F_BOLD, dim)
        righe = spezza(d, titolo, f_tit, utile)
        if len(righe) <= 4:
            break

    f_kick = font(F_BOLD, 46)
    f_lead = font(F_NORMALE, 40)
    f_pie = font(F_SEMI, 32)
    IL_T, IL_L = 14, 12

    righe_lead_tutte = spezza(d, lead, f_lead, utile - 20)[:4]
    righe_lead = righe_lead_tutte if fase == 2 else []

    h_tit = len(righe) * (f_tit.size + IL_T)
    h_lead = 36 + len(righe_lead_tutte) * (f_lead.size + IL_L)
    alto = A - (110 + h_tit + h_lead + 190)

    d.rectangle([0, alto, L, A], fill=(16, 13, 22))
    d.rectangle([0, alto, L, alto + 12], fill=ACCENTO)

    kick = "LO SAPEVI CHE ?"
    w = d.textlength(kick, font=f_kick)
    y_k = alto - 128
    d.rounded_rectangle([MARGINE - 32, y_k - 24, MARGINE + w + 32, y_k + f_kick.size + 24],
                        radius=99, fill=ACCENTO)
    d.text((MARGINE, y_k), kick, font=f_kick, fill=SFONDO)

    y = alto + 78
    for r in righe:
        x = MARGINE
        for parola in r.split(" "):
            pezzo = parola + " "
            largo = d.textlength(pezzo, font=f_tit)
            nuda = parola.strip(".,;:!?\"'()")

            if fase == 0 and chiave and nuda == chiave:
                # il buco: un blocco pieno al posto della risposta
                lp = d.textlength(parola, font=f_tit)
                d.rounded_rectangle([x - 6, y + 8, x + lp + 6, y + f_tit.size + 6],
                                    radius=14, fill=ACCENTO)
            else:
                colore = EVIDENZA if (chiave and nuda == chiave) else (
                    EVIDENZA if da_accendere(parola) else TESTO)
                d.text((x, y), pezzo, font=f_tit, fill=colore)
            x += largo
        y += f_tit.size + IL_T

    if righe_lead:
        y += 26
        d.rectangle([MARGINE, y, MARGINE + 90, y + 5], fill=ACCENTO)
        y += 28
        for r in righe_lead:
            x = MARGINE
            for parola in r.split(" "):
                pezzo = parola + " "
                d.text((x, y), pezzo, font=f_lead,
                       fill=EVIDENZA if da_accendere(parola) else TESTO_2)
                x += d.textlength(pezzo, font=f_lead)
            y += f_lead.size + IL_L

    cat = senza_emoji(c["categoria"]).upper()
    d.text((MARGINE, A - 96), cat, font=f_pie, fill=(120, 112, 100))
    w = d.textlength(PROFILO, font=f_pie)
    d.text((L - MARGINE - w, A - 96), PROFILO, font=f_pie, fill=ACCENTO)
    img.save(percorso, "PNG")


def da_leggere(c):
    """La voce fa la stessa cosa del video: prima la domanda, poi la pausa,
    poi la risposta."""
    t = senza_emoji(c["titolo"]).rstrip(".")
    chiave = parola_chiave(t)
    lead = senza_emoji(c["lead"])
    if chiave:
        senza = t.replace(chiave, "...")
        return f"Lo sapevi che {senza[0].lower()}{senza[1:]}? {chiave}. {lead}"
    return f"Lo sapevi che {t[0].lower()}{t[1:]}? {lead}"


if __name__ == "__main__":
    import json
    dati = json.load(open(os.path.join(QUI, "fonte", "curiosita.json"), encoding="utf-8"))["curiosita"]
    c = next(x for x in dati if "gatti-hanno-32" in x["slug"])
    print("COPERTA :", parola_chiave(senza_emoji(c["titolo"])))
    print("LA VOCE :", da_leggere(c)[:110])
    for i in range(3):
        disegna(c, i, os.path.join(QUI, f"formato2-{i}.png"))
    print("tre fotogrammi generati")
