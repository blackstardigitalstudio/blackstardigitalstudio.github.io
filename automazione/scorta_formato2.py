# -*- coding: utf-8 -*-
"""
scorta_formato2.py — genera i reel col formato "rivelazione".

Tre tempi invece di due: la risposta coperta, la risposta che arriva,
la spiegazione. Il video dura un po' di piu' perche' l'attesa e' il punto.

Uso:  venv-cb\Scripts\python.exe scorta_formato2.py 5
Made in Italy
"""
import json, os, random, subprocess, sys, tempfile, time
from datetime import date

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
sys.path.insert(0, os.path.join(QUI, "voce"))

from formato2 import disegna, da_leggere, parola_chiave
from genera_reel import chiusura, senza_emoji
from reel_parlato import durata
from filtro import pulisci
from parla import impostazioni, carica, genera

FONTE = os.path.join(QUI, "fonte", "curiosita.json")
PRONTI = os.path.join(QUI, "pronti-reel")
MUSICA = os.path.join(QUI, "musica")
STORICO = os.path.join(QUI, "storico-reel.json")


def monta(f0, f1, f2, f3, voce, musica, uscita, dur):
    """Quattro tempi. Il primo (la domanda coperta) resta piu' a lungo:
    e' li' che si decide se la persona resta o scrolla."""
    t_domanda = min(max(dur * 0.30, 2.8), 4.5)     # quanto resta coperta
    t_risposta = 1.4                                # il momento della rivelazione
    fine_testo = 0.25 + dur
    coda = 2.4
    tot = fine_testo + 0.3 + coda

    Z, ZM = 0.0004, 1.07
    z1 = min(1 + Z * t_domanda * 30, ZM)
    z2 = min(1 + Z * (t_domanda + t_risposta) * 30, ZM)

    def pan(inp, dsec, zin):
        return (f"[{inp}:v]scale=1350:-1,"
                f"zoompan=z='min(if(eq(on,0),{zin:.4f},zoom+{Z}),{ZM})':d={int(dsec*30)}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1")

    filtro = (
        f"{pan(0, t_domanda + 1, 1.0)}[v0];"
        f"{pan(1, t_risposta + 1, z1)}[v1];"
        f"{pan(2, fine_testo - t_domanda - t_risposta + 1, z2)}[v2];"
        f"[3:v]scale=1080:1920,setsar=1,fps=30[v3];"
        # la rivelazione e' uno STACCO NETTO, non una dissolvenza: deve sorprendere
        f"[v0][v1]xfade=transition=fade:duration=0.12:offset={t_domanda-0.06}[a1];"
        f"[a1][v2]xfade=transition=fade:duration=0.35:offset={t_domanda+t_risposta-0.18}[a2];"
        f"[a2][v3]xfade=transition=fade:duration=0.5:offset={fine_testo-0.2}[a3];"
        f"[a3]fade=t=out:st={tot-0.5}:d=0.5[v];"
        f"[4:a]adelay=250|250[parlato];"
        f"[5:a]volume=0.15,afade=t=in:st=0:d=1,afade=t=out:st={tot-1.4}:d=1.4[fondo];"
        f"[parlato][fondo]amix=inputs=2:duration=first:dropout_transition=0,"
        f"apad=whole_dur={tot}[a]"
    )

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-loop", "1", "-t", str(t_domanda + 1), "-i", f0,
           "-loop", "1", "-t", str(t_risposta + 1), "-i", f1,
           "-loop", "1", "-t", str(fine_testo - t_domanda - t_risposta + 1), "-i", f2,
           "-loop", "1", "-t", str(coda + 1), "-i", f3,
           "-i", voce,
           "-stream_loop", "-1", "-i", musica,
           "-filter_complex", filtro,
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-r", "30", "-t", str(tot),
           "-movflags", "+faststart", uscita]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg:\n" + (r.stderr or "")[-700:])


def didascalia(c):
    cat = senza_emoji(c["categoria"]).lower()
    return "\n".join([c["titolo"], "", c["lead"], "", c["deep"], "",
                      "E tu lo sapevi? Scrivimelo qui sotto.", "",
                      "Se conosci qualcuno che non lo sa, mandagliela.", "",
                      f"#curiosita #losapeviche #{cat}"])


def main():
    quanti = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    dati = pulisci(json.load(open(FONTE, encoding="utf-8"))["curiosita"])
    # solo quelle dove c'e' qualcosa da coprire: senza il buco il formato non ha senso
    dati = [c for c in dati if parola_chiave(senza_emoji(c["titolo"]))]
    print(f"Curiosita' adatte al formato: {len(dati)}")

    s = json.load(open(STORICO, encoding="utf-8")) if os.path.exists(STORICO) else {"usate": [], "conta": 0}
    brani = [os.path.join(MUSICA, f) for f in sorted(os.listdir(MUSICA))]
    modello, disp = carica()
    print(f"Voce su {disp.upper()}\n")

    fatti = 0
    for i in range(quanti):
        liberi = [c for c in dati if c["slug"] not in s["usate"]] or list(dati)
        c = random.choice(liberi)
        s["usate"].append(c["slug"]); s["conta"] += 1
        v = impostazioni(c.get("categoria"))
        # "AAA" davanti al nome: cosi' finiscono in cima alla coda ed escono per primi
        nome = f"AAA-{date.today().isoformat()}-nuovo-{s['conta']:03d}-{c['slug'][:30]}"
        print(f"[{i+1}/{quanti}] {c['titolo'][:50]}  (copre: {parola_chiave(senza_emoji(c['titolo']))})")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                f = [os.path.join(tmp, f"{n}.png") for n in "0123"]
                wav = os.path.join(tmp, "v.wav")
                for k in range(3):
                    disegna(c, k, f[k])
                chiusura(f[3])
                d = genera(modello, da_leggere(c), wav, v)
                monta(f[0], f[1], f[2], f[3], wav, random.choice(brani),
                      os.path.join(PRONTI, nome + ".mp4"), d)
            open(os.path.join(PRONTI, nome + ".txt"), "w", encoding="utf-8").write(didascalia(c))
            print(f"        {d:.1f}s  ok")
            fatti += 1
        except Exception as e:
            print(f"        saltato: {str(e)[:100]}")
        json.dump(s, open(STORICO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nFatti {fatti} reel col formato nuovo. Escono per primi.")


if __name__ == "__main__":
    main()
