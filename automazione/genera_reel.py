# -*- coding: utf-8 -*-
"""
genera_reel.py — trasforma una curiosita' in un video verticale per i Reel.

Come e' fatto: due fermo-immagine (prima il titolo, poi titolo + spiegazione)
uniti da una dissolvenza, con un lento avvicinamento della camera. Niente effetti
da videomaker alle prime armi: il movimento serve solo a tenere fermo il pollice.

Non pubblica niente: mette il file pronto in "pronti-reel".
Made in Italy
"""
import json, os, random, re, subprocess, sys, tempfile
from datetime import date
from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(QUI, "fonte", "curiosita.json")
PRONTI = os.path.join(QUI, "pronti-reel")
STORICO = os.path.join(QUI, "storico-reel.json")

L, A = 1080, 1920                 # verticale 9:16, il formato dei Reel
DURATA = 11                       # secondi
SFONDO = (22, 19, 31)
ACCENTO = (232, 145, 63)
TESTO = (245, 240, 230)
TESTO_2 = (167, 158, 140)
MARGINE = 96

FONT_DIR = r"C:\Windows\Fonts"
F_BOLD = os.path.join(FONT_DIR, "segoeuib.ttf")
F_NORMALE = os.path.join(FONT_DIR, "segoeui.ttf")
F_SEMI = os.path.join(FONT_DIR, "seguisb.ttf")

PROFILO = "@matteoblackstark"


def font(p, dim):
    try:
        return ImageFont.truetype(p, dim)
    except OSError:
        return ImageFont.load_default(dim)


def senza_emoji(t):
    """Tiene solo i caratteri che i font di sistema sanno disegnare.
    Senza questo, rune, greco, cirillico ed emoji finiscono nell'immagine
    come quadratini vuoti (le rune vichinghe di Bluetooth, per dirne una)."""
    tenuti = []
    for ch in t:
        if ord(ch) < 0x0250 or ch in "\u20ac\u2018\u2019\u201c\u201d\u2013\u2014\u2026":
            tenuti.append(ch)
    ripulito = "".join(tenuti)
    ripulito = re.sub(r"\s+([,.;:!?])", r"\1", ripulito)   # spazi rimasti prima della punteggiatura
    ripulito = re.sub(r"\s+e\s*([.,])", r"\1", ripulito)   # "le rune  e ." -> "le rune."
    ripulito = re.sub(r"\s{2,}", " ", ripulito)
    return ripulito.strip()


def spezza(d, testo, f, larghezza_px):
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


EVIDENZA = (255, 200, 87)          # giallo caldo, parente dell'arancione della targa

# Parole che accendiamo: i numeri (l'occhio ci va sempre) e quelle che
# reggono la sorpresa. L'occhio ha bisogno di un punto dove atterrare:
# su un titolo tutto dello stesso colore deve leggere tutto o niente.
FORTI = {
    "mai", "primo", "prima", "unico", "unica", "solo", "sola", "tutti", "tutto",
    "piu", "più", "meno", "nessuno", "sempre", "record", "gigante", "enorme",
    "segreto", "vero", "falso", "morto", "vivo", "gratis", "milioni", "miliardi",
    "secoli", "anni", "giorni", "ore", "volte",
}


def da_accendere(parola):
    pulita = "".join(ch for ch in parola if ch.isalnum() or ch in "'").lower()
    if not pulita:
        return False
    if any(ch.isdigit() for ch in pulita):        # 23, 1993, 70%
        return True
    if parola.isupper() and len(parola) > 1:      # UN solo quadro
        return True
    return pulita in FORTI


def righe_centrate(d, righe, f, y, colore, interlinea, accendi=False):
    for r in righe:
        w = d.textlength(r, font=f)
        x = (L - w) / 2
        if not accendi:
            d.text((x, y), r, font=f, fill=colore)
        else:
            for parola in r.split(" "):
                pezzo = parola + " "
                colore_parola = EVIDENZA if da_accendere(parola) else colore
                d.text((x, y), pezzo, font=f, fill=colore_parola)
                x += d.textlength(pezzo, font=f)
        y += f.size + interlinea
    return y


FOTO = os.path.join(QUI, "foto")


def scarica_foto(c):
    """La foto che Matteo ha gia' scelto per quella curiosita' sul sito.
    Si scarica una volta e resta in cache: la seconda volta e' istantanea."""
    url = c.get("immagine")
    if not url:
        return None
    os.makedirs(FOTO, exist_ok=True)
    percorso = os.path.join(FOTO, c["slug"][:60] + ".jpg")
    if not os.path.exists(percorso):
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r, open(percorso, "wb") as f:
                f.write(r.read())
        except Exception:
            return None
    return percorso if os.path.exists(percorso) else None


def sfondo_con_foto(c, larghezza=None, altezza=None):
    """Foto a tutto schermo + velo scuro. Senza il velo il testo sparisce
    dentro l'immagine; col velo la foto si vede ma il testo comanda.
    Le misure si possono passare: i reel sono 1080x1920, i post 1080x1350."""
    L_, A_ = larghezza or L, altezza or A
    base = Image.new("RGB", (L_, A_), SFONDO)
    percorso = scarica_foto(c)
    if not percorso:
        return base
    try:
        foto = Image.open(percorso).convert("RGB")
    except Exception:
        return base

    # riempie tutto senza deformare (ritaglia il di piu')
    scala = max(L_ / foto.width, A_ / foto.height)
    foto = foto.resize((int(foto.width * scala) + 1, int(foto.height * scala) + 1),
                       Image.LANCZOS)
    sx = (foto.width - L_) // 2
    sy = int((foto.height - A_) * 0.35)         # taglia piu' dal basso: i soggetti stanno in alto
    base.paste(foto.crop((sx, sy, sx + L_, sy + A_)), (0, 0))

    # Sfocatura + velo uniforme. Tre motivi, tutti pratici:
    #  - il testo resta la cosa piu' nitida dello schermo, quindi comanda lui
    #  - niente fasce nette di velo, che si vedevano come strisce
    #  - le foto del sito sono generiche (per Riina c'erano delle bolle d'olio):
    #    sfocate diventano atmosfera e colore, e la stonatura non si nota
    base = base.filter(ImageFilter.GaussianBlur(radius=14))
    velo = Image.new("RGBA", (L_, A_), (13, 11, 19, 178))
    return Image.alpha_composite(base.convert("RGBA"), velo).convert("RGB")


def fotogramma(c, con_spiegazione, percorso):
    img = sfondo_con_foto(c)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, L, 12], fill=ACCENTO)

    titolo = senza_emoji(c["titolo"])
    lead = senza_emoji(c["lead"])
    utile = L - MARGINE * 2

    for dim in (104, 94, 84, 74, 66, 58):
        f_tit = font(F_BOLD, dim)
        righe_tit = spezza(d, titolo, f_tit, utile)
        if len(righe_tit) <= 5:
            break

    f_kick = font(F_BOLD, 58)          # la targa si legge anche in miniatura
    f_lead = font(F_NORMALE, 42)
    f_pie = font(F_SEMI, 32)

    IL_T, IL_L = 16, 14
    righe_lead = spezza(d, lead, f_lead, utile - 40)[:5] if (lead and con_spiegazione) else []
    h_tit = len(righe_tit) * (f_tit.size + IL_T)
    h_lead = (44 + 36 + len(righe_lead) * (f_lead.size + IL_L)) if righe_lead else 0

    # TRE FASCE, ognuna con un compito solo:
    #   alto   -> la targa della serie: deve leggersi anche quando il reel e'
    #             largo 150 pixel nella griglia del profilo
    #   centro -> la curiosita': e' il contenuto, comanda lei
    #   basso  -> categoria e nome
    # Stando in fasce diverse, targa e titolo non si rubano la scena a vicenda.
    kick = "LO  SAPEVI  CHE ?"
    w = d.textlength(kick, font=f_kick)
    px, py = 46, 26
    y_kick = 205
    x0 = (L - w) / 2 - px
    d.rounded_rectangle([x0, y_kick - py, x0 + w + px * 2, y_kick + f_kick.size + py],
                        radius=99, fill=ACCENTO)
    d.text(((L - w) / 2, y_kick), kick, font=f_kick, fill=SFONDO)

    # Il blocco del testo resta ancorato allo stesso punto in entrambi i
    # fotogrammi: nella dissolvenza il titolo non salta, appare solo la spiegazione.
    y = 600

    y = righe_centrate(d, righe_tit, f_tit, y, TESTO, IL_T, accendi=True)

    if righe_lead:
        y += 44
        d.line([(L / 2 - 50, y), (L / 2 + 50, y)], fill=ACCENTO, width=4)
        y += 36
        righe_centrate(d, righe_lead, f_lead, y, TESTO_2, IL_L, accendi=True)

    cat = senza_emoji(c["categoria"]).upper()
    d.line([(MARGINE, A - 190), (L - MARGINE, A - 190)], fill=(46, 41, 58), width=2)
    d.text((MARGINE, A - 150), cat, font=f_pie, fill=TESTO_2)
    w = d.textlength(PROFILO, font=f_pie)
    d.text((L - MARGINE - w, A - 150), PROFILO, font=f_pie, fill=ACCENTO)

    img.save(percorso, "PNG")


MUSICA = os.path.join(QUI, "musica")


def chiusura(percorso):
    """La schermata finale, identica su ogni reel: e' quella che resta in mente.
    Il nome grande, e sotto la promessa che domani ce n'e' un'altra."""
    img = Image.new("RGB", (L, A), SFONDO)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, L, 12], fill=ACCENTO)

    f_kick = font(F_BOLD, 38)
    f_nome = font(F_BOLD, 72)
    f_sotto = font(F_NORMALE, 40)

    y = A * 0.34
    kick = "LO  SAPEVI  CHE ?"
    w = d.textlength(kick, font=f_kick)
    px, py = 30, 16
    x0 = (L - w) / 2 - px
    d.rounded_rectangle([x0, y - py, x0 + w + px * 2, y + f_kick.size + py],
                        radius=99, fill=ACCENTO)
    d.text(((L - w) / 2, y), kick, font=f_kick, fill=SFONDO)
    y += f_kick.size + 130

    nome = "@matteoblackstark"
    w = d.textlength(nome, font=f_nome)
    d.text(((L - w) / 2, y), nome, font=f_nome, fill=TESTO)
    y += f_nome.size + 46

    d.line([(L / 2 - 50, y), (L / 2 + 50, y)], fill=ACCENTO, width=4)
    y += 46

    for riga in ("Una curiosità al giorno.", "Tutti i giorni."):
        w = d.textlength(riga, font=f_sotto)
        d.text(((L - w) / 2, y), riga, font=f_sotto, fill=TESTO_2)
        y += f_sotto.size + 14

    img.save(percorso, "PNG")


def scegli_musica():
    """Usa la musica di Matteo (TeknoSteps): e' sua, quindi nessun problema di diritti,
    e ogni giorno il suo suono torna. Se la cartella e' vuota, il video resta muto."""
    if not os.path.isdir(MUSICA):
        return None
    brani = [f for f in sorted(os.listdir(MUSICA)) if f.endswith((".m4a", ".mp3", ".wav"))]
    return os.path.join(MUSICA, random.choice(brani)) if brani else None


def monta(f1, f2, uscita, musica=None):
    """Due fermo-immagine + dissolvenza + lento avvicinamento.
    Sotto va la musica (se c'e'), altrimenti una traccia muta: Instagram
    vuole comunque un audio dentro il file."""
    meta = DURATA / 2
    filtro = (
        f"[0:v]scale=1350:-1,zoompan=z='min(zoom+0.0006,1.10)':d={int(meta*30)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={L}x{A}:fps=30,setsar=1[v0];"
        f"[1:v]scale=1350:-1,zoompan=z='min(zoom+0.0006,1.10)':d={int((DURATA-meta+1)*30)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={L}x{A}:fps=30,setsar=1[v1];"
        f"[v0][v1]xfade=transition=fade:duration=0.8:offset={meta-0.4}[vv];"
        f"[vv]fade=t=in:st=0:d=0.5,fade=t=out:st={DURATA-0.6}:d=0.6[v]"
    )
    audio = (["-stream_loop", "-1", "-i", musica] if musica
             else ["-f", "lavfi", "-t", str(DURATA), "-i", "anullsrc=r=44100:cl=stereo"])

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", str(meta + 1), "-i", f1,
        "-loop", "1", "-t", str(DURATA - meta + 1), "-i", f2,
        *audio,
        "-filter_complex", filtro,
        "-map", "[v]", "-map", "2:a", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-r", "30", "-t", str(DURATA),
        "-movflags", "+faststart", uscita,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg non ce l'ha fatta:\n" + (r.stderr or "")[-800:])


def storico():
    if os.path.exists(STORICO):
        with open(STORICO, encoding="utf-8") as f:
            return json.load(f)
    return {"usate": [], "conta": 0}


def main():
    with open(FONTE, encoding="utf-8") as f:
        dati = json.load(f)["curiosita"]

    quanti = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    os.makedirs(PRONTI, exist_ok=True)
    s = storico()

    for _ in range(quanti):
        liberi = [c for c in dati if c["slug"] not in s["usate"]] or list(dati)
        if not liberi:
            s["usate"] = []
            liberi = list(dati)
        c = random.choice(liberi)
        s["usate"].append(c["slug"])
        s["conta"] += 1

        nome = f"{date.today().isoformat()}-reel-{s['conta']:03d}-{c['slug'][:40]}"
        with tempfile.TemporaryDirectory() as tmp:
            f1 = os.path.join(tmp, "a.png")
            f2 = os.path.join(tmp, "b.png")
            fotogramma(c, False, f1)
            fotogramma(c, True, f2)
            brano = scegli_musica()
            monta(f1, f2, os.path.join(PRONTI, nome + ".mp4"), brano)
            if brano:
                print(f"      musica: {os.path.basename(brano)}")

        deep = c["deep"]
        if len(deep) > 420:
            deep = deep[:417].rsplit(" ", 1)[0] + "..."
        cat = senza_emoji(c["categoria"]).lower()
        with open(os.path.join(PRONTI, nome + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join([c["titolo"], "", c["lead"], "", deep, "",
                               f"#curiosita #losapeviche #{cat} #imparasuinstagram"]))
        print(f"[{s['conta']:03d}] {nome}.mp4")

    with open(STORICO, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"\nPronti in: {PRONTI}")


if __name__ == "__main__":
    main()
