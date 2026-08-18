# -*- coding: utf-8 -*-
"""
genera_reel.py — trasforma una curiosita' in un video verticale per i Reel.

Come e' fatto: due fermo-immagine (prima il titolo, poi titolo + spiegazione)
uniti da una dissolvenza, con un lento avvicinamento della camera. Niente effetti
da videomaker alle prime armi: il movimento serve solo a tenere fermo il pollice.

Non pubblica niente: mette il file pronto in "pronti-reel".
Made in Italy
"""
import json, os, random, re, subprocess, sys, tempfile, time
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


def scarica_foto(c, tentativi=3):
    """La foto che Matteo ha gia' scelto per quella curiosita' sul sito.
    Si scarica una volta e resta in cache: la seconda volta e' istantanea.

    Ci prova piu' volte prima di arrendersi: se la rete fa i capricci un attimo,
    prima il video usciva col fondo nero e nessuno se ne accorgeva. Adesso,
    se proprio non ce la fa, chi chiama lo viene a sapere e salta la curiosita'.
    """
    url = c.get("immagine")
    if not url:
        return None
    os.makedirs(FOTO, exist_ok=True)
    percorso = os.path.join(FOTO, c["slug"][:60] + ".jpg")

    if os.path.exists(percorso) and os.path.getsize(percorso) > 8000:
        return percorso

    import urllib.request
    for n in range(tentativi):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                dati = r.read()
            if len(dati) < 8000:          # troppo piccola: non e' una foto vera
                raise ValueError("immagine troppo piccola")
            with open(percorso, "wb") as f:
                f.write(dati)
            return percorso
        except Exception as e:
            if n == tentativi - 1:
                print(f"      foto non scaricata dopo {tentativi} tentativi: {str(e)[:60]}")
            else:
                time.sleep(2 + n * 2)
    return None


def sfondo_con_foto(c, larghezza=None, altezza=None, obbligatoria=False):
    """Foto a tutto schermo + velo scuro. Senza il velo il testo sparisce
    dentro l'immagine; col velo la foto si vede ma il testo comanda.
    Le misure si possono passare: i reel sono 1080x1920, i post 1080x1350."""
    L_, A_ = larghezza or L, altezza or A
    base = Image.new("RGB", (L_, A_), SFONDO)
    percorso = scarica_foto(c)
    if not percorso:
        if obbligatoria:
            # Meglio saltare la curiosita' che sfornare un video col fondo nero:
            # e' successo il 15/08/2026 e i video sono usciti cosi' senza avvisare.
            raise RuntimeError("foto non disponibile")
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

    # Velo LEGGERO (16%) e quasi niente sfocatura: scelta di Matteo il
    # 17/08/2026 dopo aver visto la scala. Prima era al 70% e le immagini
    # sparivano nel feed — scure e uniformi in mezzo a foto luminose.
    # Il testo resta leggibile perche' sta sulla fascia scura in basso,
    # non sopra la foto.
    base = base.filter(ImageFilter.GaussianBlur(radius=2))
    velo = Image.new("RGBA", (L_, A_), (13, 11, 19, 40))
    return Image.alpha_composite(base.convert("RGBA"), velo).convert("RGB")


def fotogramma(c, con_spiegazione, percorso):
    """Stile TARGA (scelto da Matteo il 17/08/2026).

    La foto si vede davvero: velo al 16%, quasi niente sfocatura. Il testo
    NON sta sopra la foto — sta su una fascia scura in basso, cosi' resta
    leggibile comunque. Sopra la fascia, la targa arancione piena: nel feed,
    in mezzo a foto luminose, quel blocco di colore e' il colpo d'occhio.

    La fascia ha altezza FISSA (calcolata sul titolo + spiegazione) anche
    quando la spiegazione non c'e': cosi' nella dissolvenza fra i due
    fotogrammi il titolo non si sposta, appare solo il testo in piu'.
    """
    img = sfondo_con_foto(c, obbligatoria=True)
    d = ImageDraw.Draw(img)

    titolo = senza_emoji(c["titolo"])
    lead = senza_emoji(c["lead"])
    utile = L - MARGINE * 2

    # il titolo parte grande e scende solo quanto serve per stare in 4 righe
    for dim in (98, 88, 78, 70, 62, 56):
        f_tit = font(F_BOLD, dim)
        righe_tit = spezza(d, titolo, f_tit, utile)
        if len(righe_tit) <= 4:
            break

    f_kick = font(F_BOLD, 46)
    f_lead = font(F_NORMALE, 40)
    f_pie = font(F_SEMI, 32)
    IL_T, IL_L = 14, 12

    righe_lead_tutte = spezza(d, lead, f_lead, utile - 20)[:4]
    righe_lead = righe_lead_tutte if con_spiegazione else []

    # altezza della fascia: sempre quella del caso pieno, cosi' i due
    # fotogrammi combaciano e nella dissolvenza niente salta
    h_tit = len(righe_tit) * (f_tit.size + IL_T)
    h_lead = 36 + len(righe_lead_tutte) * (f_lead.size + IL_L)
    alto_fascia = A - (110 + h_tit + h_lead + 190)

    d.rectangle([0, alto_fascia, L, A], fill=(16, 13, 22))
    d.rectangle([0, alto_fascia, L, alto_fascia + 12], fill=ACCENTO)

    # la targa della serie, appoggiata sopra la fascia
    kick = "LO SAPEVI CHE ?"
    w = d.textlength(kick, font=f_kick)
    y_kick = alto_fascia - 128
    d.rounded_rectangle([MARGINE - 32, y_kick - 24, MARGINE + w + 32, y_kick + f_kick.size + 24],
                        radius=99, fill=ACCENTO)
    d.text((MARGINE, y_kick), kick, font=f_kick, fill=SFONDO)

    # testo dentro la fascia, allineato a sinistra: niente simmetria centrale
    y = alto_fascia + 78
    for r in righe_tit:
        x = MARGINE
        for parola in r.split(" "):
            pezzo = parola + " "
            d.text((x, y), pezzo, font=f_tit,
                   fill=EVIDENZA if da_accendere(parola) else TESTO)
            x += d.textlength(pezzo, font=f_tit)
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

        cat = senza_emoji(c["categoria"]).lower()
        with open(os.path.join(PRONTI, nome + ".txt"), "w", encoding="utf-8") as f:
            f.write("\n".join([
                c["titolo"], "", c["lead"], "", c["deep"], "",
                "Se conosci qualcuno che non lo sa, mandagliela.", "",
                f"#curiosita #losapeviche #{cat} #imparasuinstagram"]))
        print(f"[{s['conta']:03d}] {nome}.mp4")

    with open(STORICO, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"\nPronti in: {PRONTI}")


if __name__ == "__main__":
    main()
