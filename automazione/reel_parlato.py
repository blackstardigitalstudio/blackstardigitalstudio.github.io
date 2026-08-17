# -*- coding: utf-8 -*-
"""
reel_parlato.py — il reel con la voce di Matteo sopra e la sua musica sotto.

Differenza dal reel muto: qui la durata non e' fissa, la decide la voce.
Il testo viene letto, si misura quanto dura, e il video si adatta.

Ordine dei suoni: la voce davanti, la musica dietro a volume basso.
Made in Italy
"""
import json, os, random, subprocess, sys, tempfile
from datetime import date

QUI = os.path.dirname(os.path.abspath(__file__))
VOCE = os.path.join(QUI, "voce")
PY_VOCE = os.path.join(VOCE, "venv-cb", "Scripts", "python.exe")
PARLA = os.path.join(VOCE, "parla.py")
FONTE = os.path.join(QUI, "fonte", "curiosita.json")
PRONTI = os.path.join(QUI, "pronti-reel")
MUSICA = os.path.join(QUI, "musica")
STORICO = os.path.join(QUI, "storico-reel.json")

sys.path.insert(0, QUI)
from genera_reel import fotogramma, chiusura, senza_emoji
from filtro import pulisci          # riuso i fotogrammi gia' fatti


def durata(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True)
    return float(r.stdout.strip())


def leggi(testo, uscita, categoria=None, lingua="it"):
    r = subprocess.run([PY_VOCE, PARLA, testo, uscita, categoria or "", lingua],
                       capture_output=True, text=True)
    if r.stdout.strip():
        print("      " + r.stdout.strip().splitlines()[-1])
    if r.returncode != 0 or not os.path.exists(uscita):
        raise RuntimeError("La voce non e' stata generata:\n" + (r.stderr or r.stdout)[-600:])
    return durata(uscita)


FIRMA = os.path.join(VOCE, "firma.wav")


def monta_parlato(f1, f2, f3, voce_wav, musica, uscita, dur):
    """Tre tempi: il titolo, la spiegazione, la firma.
    La firma e' sempre la stessa su ogni reel — e' quella che rende i video
    una serie invece che contenuti sparsi."""
    # La firma parlata e' facoltativa: se il file non c'e', il video finisce
    # con la sola schermata e la musica che sfuma. Scelta di Matteo il
    # 14/08/2026 — si riattiva rimettendo voce/firma.wav, senza toccare altro.
    con_firma = os.path.exists(FIRMA)
    d_firma = durata(FIRMA) if con_firma else 2.4     # quanto resta la schermata
    pausa = 0.45 if con_firma else 0.3
    stacco = min(max(dur * 0.38, 2.5), max(dur - 2.0, 2.6))
    inizio_firma = 0.25 + dur + pausa
    tot = inizio_firma + d_firma + 0.6

    # Lo zoom deve PROSEGUIRE fra un fotogramma e l'altro, non ricominciare:
    # se il secondo riparte da 1.0 mentre il primo e' gia' ingrandito, durante
    # la dissolvenza si vede lo stesso testo in due misure sovrapposte e non si
    # legge piu' niente (segnalato da Matteo il 14/08/2026).
    passo = 0.0004
    zoom_max = 1.07
    z_stacco = min(1 + passo * stacco * 30, zoom_max)

    filtro = (
        f"[0:v]scale=1350:-1,zoompan=z='min(zoom+{passo},{zoom_max})':d={int((stacco+1)*30)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1[v0];"
        f"[1:v]scale=1350:-1,"
        f"zoompan=z='min(if(eq(on,0),{z_stacco:.4f},zoom+{passo}),{zoom_max})':"
        f"d={int((inizio_firma-stacco+1)*30)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1[v1];"
        f"[2:v]scale=1080:1920,setsar=1,fps=30[v2];"
        # dissolvenza corta: meno tempo di sovrapposizione, testo piu' pulito
        f"[v0][v1]xfade=transition=fade:duration=0.35:offset={stacco-0.18}[va];"
        f"[va][v2]xfade=transition=fade:duration=0.5:offset={inizio_firma-0.5}[vb];"
        # NIENTE dissolvenza in apertura: Instagram prende il primo fotogramma
        # come copertina, e con la dissolvenza la copertina viene NERA.
        # (Difetto trovato da Matteo il 14/08/2026 sui reel gia' pubblicati.)
        f"[vb]fade=t=out:st={tot-0.5}:d=0.5[v];"
    )

    if con_firma:
        i_musica = 5
        filtro += (
            f"[3:a]adelay=250|250[racconto];"
            f"[4:a]adelay={int(inizio_firma*1000)}|{int(inizio_firma*1000)}[sigla];"
            f"[racconto][sigla]amix=inputs=2:duration=longest:dropout_transition=0,"
            f"volume=2.0[parlato];"
        )
    else:
        i_musica = 4
        filtro += f"[3:a]adelay=250|250[parlato];"

    filtro += (
        # la musica sta dietro e non copre mai; sul finale sale un filo,
        # perche' li' resta sola con la schermata
        f"[{i_musica}:a]volume=0.15,afade=t=in:st=0:d=1,"
        f"afade=t=out:st={tot-1.4}:d=1.4[fondo];"
        f"[parlato][fondo]amix=inputs=2:duration=first:dropout_transition=0,"
        f"apad=whole_dur={tot}[a]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", str(stacco + 1), "-i", f1,
        "-loop", "1", "-t", str(inizio_firma - stacco + 1), "-i", f2,
        "-loop", "1", "-t", str(d_firma + 2), "-i", f3,
        "-i", voce_wav,
        *(["-i", FIRMA] if con_firma else []),
        "-stream_loop", "-1", "-i", musica,
        "-filter_complex", filtro,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-r", "30", "-t", str(tot),
        "-movflags", "+faststart", uscita,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg:\n" + (r.stderr or "")[-800:])


def da_leggere(c):
    """Cosa legge la voce: l'aggancio e poi la spiegazione. Corto: nei reel
    dopo 25 secondi si scrolla via."""
    t = senza_emoji(c["titolo"]).rstrip(".")
    lead = senza_emoji(c["lead"])
    if len(lead) > 230:
        lead = lead[:227].rsplit(" ", 1)[0] + "."
    return f"Lo sapevi che {t[0].lower()}{t[1:]}? {lead}"


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
    with open(FONTE, encoding="utf-8") as f:
        dati = pulisci(json.load(f)["curiosita"])
    s = json.load(open(STORICO, encoding="utf-8")) if os.path.exists(STORICO) else {"usate": [], "conta": 0}
    quanti = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(PRONTI, exist_ok=True)

    brani = [os.path.join(MUSICA, f) for f in sorted(os.listdir(MUSICA))] if os.path.isdir(MUSICA) else []

    for _ in range(quanti):
        liberi = [c for c in dati if c["slug"] not in s["usate"]] or list(dati)
        c = random.choice(liberi)
        s["usate"].append(c["slug"]); s["conta"] += 1
        nome = f"{date.today().isoformat()}-reel-{s['conta']:03d}-{c['slug'][:38]}"
        print(f"[{s['conta']:03d}] {c['titolo'][:56]}")

        with tempfile.TemporaryDirectory() as tmp:
            f1, f2 = os.path.join(tmp, "a.png"), os.path.join(tmp, "b.png")
            f3 = os.path.join(tmp, "c.png")
            wav = os.path.join(tmp, "voce.wav")
            fotogramma(c, False, f1)
            fotogramma(c, True, f2)
            chiusura(f3)
            print("      leggo il testo...")
            d = leggi(da_leggere(c), wav, c.get("categoria"))
            monta_parlato(f1, f2, f3, wav, random.choice(brani) if brani else None,
                          os.path.join(PRONTI, nome + ".mp4"), d)

        with open(os.path.join(PRONTI, nome + ".txt"), "w", encoding="utf-8") as f:
            f.write(didascalia_reel(c))

    json.dump(s, open(STORICO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nPronti in: {PRONTI}")


if __name__ == "__main__":
    main()
