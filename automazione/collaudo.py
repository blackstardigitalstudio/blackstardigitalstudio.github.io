# -*- coding: utf-8 -*-
"""
collaudo.py — controlla un contenuto PRIMA che venga pubblicato.

Perche' esiste: in tre giorni sono usciti tre difetti diversi (copertina nera,
fondo senza foto, didascalia tagliata a meta' parola) e li ha trovati tutti
Matteo guardando il risultato pubblicato. Un difetto trovato dopo la
pubblicazione non si corregge piu': il post resta li'.

Questo file non impedisce di sbagliare: impedisce che lo sbaglio ESCA.
Se un contenuto non passa, viene messo da parte e si pubblica il successivo.

Uso:
    python collaudo.py                 controlla tutta la coda
    python collaudo.py --sposta        e mette gli scarti in "bocciati"
Made in Italy
"""
import os, re, subprocess, sys, tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
BOCCIATI = os.path.join(QUI, "bocciati")


def durata(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0


def fotogramma(video, n, ritaglio=None):
    """Tira fuori un fotogramma per guardarlo."""
    d = tempfile.mkdtemp()
    f = os.path.join(d, "f.png")
    vf = f"select=eq(n\\,{n})" + (f",crop={ritaglio}" if ritaglio else "")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video,
                    "-vf", vf, "-frames:v", "1", f], capture_output=True)
    return f if os.path.exists(f) else None


def controlla_video(percorso):
    """Torna la lista dei problemi. Vuota = il video va bene."""
    from PIL import Image, ImageStat
    problemi = []

    d = durata(percorso)
    if d < 6:
        problemi.append(f"dura solo {d:.1f}s")
    if d > 60:
        problemi.append(f"dura {d:.0f}s: troppo per un reel")

    # 1. la copertina non deve essere nera (Instagram usa il primo fotogramma)
    f = fotogramma(percorso, 0)
    if f:
        st = ImageStat.Stat(Image.open(f).convert("RGB"))
        if sum(st.mean) / 3 < 12:
            problemi.append("la copertina e' nera")

    # 2. lo sfondo deve avere la foto: guardo una striscia in basso dove non
    #    c'e' mai testo. Fondo piatto = variazione quasi zero.
    f = fotogramma(percorso, 15, "1080:260:0:1500")
    if f:
        st = ImageStat.Stat(Image.open(f).convert("RGB"))
        if sum(st.stddev) / 3 <= 6:
            problemi.append("manca la foto di sfondo")

    # 3. deve avere l'audio
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0", percorso],
                       capture_output=True, text=True)
    if "audio" not in r.stdout:
        problemi.append("non ha audio")

    return problemi


def controlla_testo(percorso):
    """Controlla la didascalia."""
    problemi = []
    t = open(percorso, encoding="utf-8").read().strip()

    if len(t) < 80:
        problemi.append("didascalia troppo corta")
    if len(t) > 2200:
        problemi.append("didascalia oltre il limite di Instagram")

    # il corpo (tolti gli hashtag) non deve finire a meta' frase
    corpo = t.split("#")[0].strip()
    corpo = corpo.replace("Se conosci qualcuno che non lo sa, mandagliela.", "").strip()
    if corpo and corpo[-1] not in ".!?…" and not corpo.endswith("..."):
        problemi.append(f"finisce a meta': \"...{corpo[-40:]}\"")

    # caratteri che i font non sanno disegnare
    strani = {ch for ch in t if ord(ch) > 0x2100 and ch not in "‘’“”–—…"}
    if strani:
        problemi.append(f"caratteri illeggibili: {''.join(list(strani)[:5])}")

    if "#" not in t:
        problemi.append("senza etichette")

    return problemi


def collauda(cartella, estensione, sposta=False):
    if not os.path.isdir(cartella):
        return 0, 0
    buoni = bocciati = 0
    for n in sorted(os.listdir(cartella)):
        if not n.endswith(estensione):
            continue
        percorso = os.path.join(cartella, n)
        testo = os.path.join(cartella, n[:-len(estensione)] + ".txt")

        problemi = []
        if estensione == ".mp4":
            problemi += controlla_video(percorso)
        if os.path.exists(testo):
            problemi += controlla_testo(testo)
        else:
            problemi.append("manca la didascalia")

        if problemi:
            bocciati += 1
            print(f"  BOCCIATO  {n[:56]}")
            for p in problemi:
                print(f"            - {p}")
            if sposta:
                os.makedirs(BOCCIATI, exist_ok=True)
                for f in (percorso, testo):
                    if os.path.exists(f):
                        os.replace(f, os.path.join(BOCCIATI, os.path.basename(f)))
        else:
            buoni += 1
    return buoni, bocciati


def main():
    sposta = "--sposta" in sys.argv
    print("REEL")
    br, mr = collauda(os.path.join(QUI, "pronti-reel"), ".mp4", sposta)
    print(f"  buoni: {br}   bocciati: {mr}\n")
    print("POST")
    bp, mp = collauda(os.path.join(QUI, "pronti"), ".png", sposta)
    print(f"  buoni: {bp}   bocciati: {mp}")

    if (mr + mp) and sposta:
        print(f"\nGli scarti sono in: {BOCCIATI}")
    sys.exit(1 if (mr + mp) else 0)


if __name__ == "__main__":
    main()
