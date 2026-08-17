# -*- coding: utf-8 -*-
"""
scorta_reel.py — prepara in un colpo solo una scorta di reel parlati.

Differenza da reel_parlato.py: qui il modello della voce si carica UNA volta
sola invece che a ogni video. Su dieci reel sono cinque minuti risparmiati.

Serve per riempire la coda prima di un'assenza: il computer prepara, il cloud
pubblica un reel al giorno anche se qui non c'e' nessuno.

Uso:  venv-cb\\Scripts\\python.exe scorta_reel.py 12
Made in Italy
"""
import json, os, random, sys, tempfile, time
from datetime import date

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, "voce"))

from genera_reel import fotogramma, chiusura, senza_emoji
from reel_parlato import monta_parlato, da_leggere, durata
from filtro import pulisci

import torchaudio
from parla import impostazioni, carica, genera

FONTE = os.path.join(QUI, "fonte", "curiosita.json")
PRONTI = os.path.join(QUI, "pronti-reel")
MUSICA = os.path.join(QUI, "musica")
STORICO = os.path.join(QUI, "storico-reel.json")


def didascalia_reel(c):
    """Il testo che accompagna il reel.

    Esce SEMPRE per intero. Prima tagliavo, e le didascalie finivano a meta'
    parola ("...emettevano un fischio, segnal"). Poi ho misurato: la curiosita'
    piu' lunga e' 1307 caratteri contro i 2200 che Instagram accetta.
    Il taglio non serviva a niente: serviva solo a rompere le frasi.
    (Trovato da Matteo il 17/08/2026 guardando il post pubblicato.)
    """
    from genera_reel import senza_emoji
    # NESSUN taglio: la curiosita' piu' lunga dell'archivio e' 1307 caratteri
    # e Instagram ne accetta 2200. Tagliare non serviva a niente, e il taglio
    # e' proprio cio' che mandava online le notizie a meta' frase.
    deep = c["deep"]
    cat = senza_emoji(c["categoria"]).lower()
    return "\n".join([
        c["titolo"], "", c["lead"], "", deep, "",
        "Se conosci qualcuno che non lo sa, mandagliela.", "",
        f"#curiosita #losapeviche #{cat}",
    ])


def main():
    quanti = int(sys.argv[1]) if len(sys.argv) > 1 else 6

    with open(FONTE, encoding="utf-8") as f:
        dati = pulisci(json.load(f)["curiosita"])
    s = json.load(open(STORICO, encoding="utf-8")) if os.path.exists(STORICO) else {"usate": [], "conta": 0}
    os.makedirs(PRONTI, exist_ok=True)
    brani = [os.path.join(MUSICA, f) for f in sorted(os.listdir(MUSICA))] if os.path.isdir(MUSICA) else []

    print("Carico il modello della voce (una volta sola)...")
    modello, disp = carica()
    print(f"Pronto su {disp.upper()}. Preparo {quanti} reel.\n")

    inizio = time.time()
    for i in range(quanti):
        liberi = [c for c in dati if c["slug"] not in s["usate"]]
        if not liberi:
            s["usate"] = []
            liberi = list(dati)
        c = random.choice(liberi)
        s["usate"].append(c["slug"]); s["conta"] += 1

        v = impostazioni(c.get("categoria"))
        nome = f"{date.today().isoformat()}-reel-{s['conta']:03d}-{c['slug'][:38]}"
        print(f"[{i+1}/{quanti}] {c['titolo'][:52]}  (voce: {v['nome']})")

        try:
            with tempfile.TemporaryDirectory() as tmp:
                f1, f2 = os.path.join(tmp, "a.png"), os.path.join(tmp, "b.png")
                f3 = os.path.join(tmp, "c.png")
                wav = os.path.join(tmp, "voce.wav")
                fotogramma(c, False, f1)
                fotogramma(c, True, f2)
                chiusura(f3)
                d = genera(modello, da_leggere(c), wav, v)
                monta_parlato(f1, f2, f3, wav, random.choice(brani) if brani else None,
                              os.path.join(PRONTI, nome + ".mp4"), d)

            with open(os.path.join(PRONTI, nome + ".txt"), "w", encoding="utf-8") as f:
                f.write(didascalia_reel(c))
            print(f"        {d:.1f}s  ok")
        except Exception as e:
            print(f"        saltato: {str(e)[:120]}")
            continue

        json.dump(s, open(STORICO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    fatti = len([f for f in os.listdir(PRONTI) if f.endswith(".mp4")])
    print(f"\nFinito in {(time.time()-inizio)/60:.1f} minuti. In coda ci sono {fatti} reel.")


if __name__ == "__main__":
    main()
