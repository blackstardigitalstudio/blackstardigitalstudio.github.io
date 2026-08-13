# -*- coding: utf-8 -*-
"""
pubblica.py — prende il prossimo contenuto pronto e lo pubblica su Instagram.

Come funziona:
  1. carica l'immagine nel repo GitHub (diventa un indirizzo pubblico)
  2. chiede a Instagram di preparare il post
  3. lo pubblica
  4. sposta il file in "pubblicati" e lo segna nel registro

Sistema NUOVO e SEPARATO: credenziali proprie, nessun sistema dei clienti coinvolto.
Prima di pubblicare davvero, provalo con:  python pubblica.py --prova
Made in Italy
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
PRONTI = os.path.join(QUI, "pronti")
FATTI = os.path.join(QUI, "pubblicati")
REGISTRO = os.path.join(QUI, "registro-pubblicazioni.json")
ENV = os.path.join(QUI, ".env")

REPO = "blackstardigitalstudio/blackstardigitalstudio.github.io"
CARTELLA_MEDIA = "media"
# API Instagram nuova (Instagram Login): non passa piu' da Facebook
API = "https://graph.instagram.com/v21.0"


# --- utilita' ----------------------------------------------------------------

def leggi_env():
    """Prende le credenziali dal file .env (sul computer di Matteo)
    oppure dalle variabili d'ambiente (quando gira da solo su GitHub)."""
    dati = {}
    if os.path.exists(ENV):
        with open(ENV, encoding="utf-8") as f:
            for riga in f:
                riga = riga.strip()
                if riga and not riga.startswith("#") and "=" in riga:
                    k, v = riga.split("=", 1)
                    dati[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("IG_USER_ID", "IG_TOKEN", "IG_USERNAME"):
        if os.environ.get(k):
            dati[k] = os.environ[k]
    return dati


def sul_cloud():
    return os.environ.get("GITHUB_ACTIONS") == "true"


def chiama(url, dati=None):
    corpo = urllib.parse.urlencode(dati).encode() if dati else None
    req = urllib.request.Request(url, data=corpo, method="POST" if dati else "GET")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Instagram ha risposto {e.code}: {msg}")


def prossimo():
    if not os.path.isdir(PRONTI):
        return None
    png = sorted(f for f in os.listdir(PRONTI) if f.endswith(".png"))
    for p in png:
        t = os.path.join(PRONTI, p[:-4] + ".txt")
        if os.path.exists(t):
            return os.path.join(PRONTI, p), t
    return None


def registra(voce):
    storico = []
    if os.path.exists(REGISTRO):
        with open(REGISTRO, encoding="utf-8") as f:
            storico = json.load(f)
    storico.append(voce)
    with open(REGISTRO, "w", encoding="utf-8") as f:
        json.dump(storico, f, ensure_ascii=False, indent=2)


# --- passi -------------------------------------------------------------------

def carica_su_github(png):
    """Mette l'immagine nel repo e restituisce l'indirizzo pubblico.
    Usa il gh gia' autenticato: nessun token in piu' da gestire."""
    nome = os.path.basename(png)
    percorso = f"{CARTELLA_MEDIA}/{nome}"
    with open(png, "rb") as f:
        import base64
        contenuto = base64.b64encode(f.read()).decode()

    # Windows non accetta comandi lunghissimi: il contenuto passa da un file, non dalla riga di comando
    corpo = os.path.join(QUI, "_invio.json")
    with open(corpo, "w", encoding="utf-8") as f:
        json.dump({"message": f"media: {nome}", "content": contenuto}, f)

    r = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{percorso}", "-X", "PUT", "--input", corpo],
        capture_output=True, text=True)
    try:
        os.remove(corpo)
    except OSError:
        pass
    if r.returncode != 0 and "already exists" not in (r.stderr or ""):
        raise RuntimeError(f"Non sono riuscito a caricare l'immagine su GitHub:\n{r.stderr}")

    return f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(percorso)}"


def pubblica_su_instagram(user_id, token, url_img, didascalia):
    passo1 = chiama(f"{API}/{user_id}/media",
                    {"image_url": url_img, "caption": didascalia, "access_token": token})
    contenitore = passo1.get("id")
    if not contenitore:
        raise RuntimeError(f"Instagram non ha creato il post: {passo1}")

    # Instagram vuole qualche secondo per scaricare l'immagine
    for _ in range(12):
        stato = chiama(f"{API}/{contenitore}?fields=status_code&access_token={token}")
        if stato.get("status_code") == "FINISHED":
            break
        if stato.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram ha scartato l'immagine: {stato}")
        time.sleep(5)

    passo2 = chiama(f"{API}/{user_id}/media_publish",
                    {"creation_id": contenitore, "access_token": token})
    return passo2.get("id")


def verifica(user_id, token):
    return chiama(f"{API}/me?fields=username,account_type,followers_count,media_count"
                  f"&access_token={token}")


def rinnova_se_serve(env):
    """I token Instagram scadono dopo 60 giorni. Ogni volta che sono passati
    piu' di 30 giorni dall'ultimo rinnovo, ne chiediamo uno nuovo e riscriviamo
    il file. Cosi' il sistema non si ferma mai da solo."""
    ultimo = env.get("IG_TOKEN_DATA", "")
    oggi = time.strftime("%Y-%m-%d")
    if ultimo:
        giorni = (time.mktime(time.strptime(oggi, "%Y-%m-%d"))
                  - time.mktime(time.strptime(ultimo, "%Y-%m-%d"))) / 86400
        if giorni < 30:
            return env

    try:
        d = chiama(f"https://graph.instagram.com/refresh_access_token"
                   f"?grant_type=ig_refresh_token&access_token={env['IG_TOKEN']}")
        nuovo = d.get("access_token")
        if not nuovo:
            print("Non sono riuscito a rinnovare il token, vado avanti con quello vecchio.")
            return env
        env["IG_TOKEN"] = nuovo
        env["IG_TOKEN_DATA"] = oggi

        if sul_cloud():
            # su GitHub il token vive in cassaforte (Secrets), non in un file
            r = subprocess.run(["gh", "secret", "set", "IG_TOKEN", "--body", nuovo],
                               capture_output=True, text=True)
            if r.returncode == 0:
                print("Token rinnovato e salvato nella cassaforte di GitHub.")
            else:
                print("ATTENZIONE: token rinnovato ma NON salvato. "
                      "Serve il segreto GH_PAT per aggiornarlo. Dettaglio: " + (r.stderr or "")[:200])
            return env

        with open(ENV, "w", encoding="utf-8") as f:
            f.write("# Credenziali del sistema di pubblicazione di Matteo. NON condividere questo file.\n")
            for k in ("IG_USER_ID", "IG_TOKEN", "IG_USERNAME", "IG_API", "IG_TOKEN_DATA"):
                if env.get(k):
                    f.write(f"{k}={env[k]}\n")
        print(f"Token rinnovato (scade fra 60 giorni, il prossimo rinnovo e' automatico).")
    except Exception as e:
        print(f"Rinnovo del token non riuscito ({e}). Vado avanti con quello attuale.")
    return env


# --- avvio -------------------------------------------------------------------

def main():
    prova = "--prova" in sys.argv
    env = leggi_env()
    user_id, token = env.get("IG_USER_ID"), env.get("IG_TOKEN")

    if not user_id or not token:
        print("Manca il file .env con IG_USER_ID e IG_TOKEN.")
        print("Leggi COME-ATTIVARE.md: sono 4 clic, si fanno una volta sola.")
        sys.exit(1)

    env = rinnova_se_serve(env)
    token = env.get("IG_TOKEN")

    try:
        chi = verifica(user_id, token)
    except Exception as e:
        print(f"Le credenziali non funzionano.\n{e}")
        sys.exit(1)

    print(f"Collegato a @{chi.get('username')} — {chi.get('followers_count', '?')} follower, "
          f"{chi.get('media_count', '?')} post")

    p = prossimo()
    if not p:
        print("Non c'e' niente di pronto da pubblicare. Lancia prima genera.py")
        sys.exit(0)

    png, txt = p
    with open(txt, encoding="utf-8") as f:
        didascalia = f.read().strip()

    print(f"\nProssimo: {os.path.basename(png)}")
    print("-" * 60)
    print(didascalia[:300] + ("..." if len(didascalia) > 300 else ""))
    print("-" * 60)

    if prova:
        print("\nPROVA: le credenziali vanno e il contenuto e' pronto. Non ho pubblicato niente.")
        return

    url_img = carica_su_github(png)
    print(f"Immagine online: {url_img}")

    post_id = pubblica_su_instagram(user_id, token, url_img, didascalia)
    print(f"PUBBLICATO — id post: {post_id}")

    os.makedirs(FATTI, exist_ok=True)
    for f_ in (png, txt):
        os.replace(f_, os.path.join(FATTI, os.path.basename(f_)))

    registra({"quando": time.strftime("%Y-%m-%d %H:%M"), "file": os.path.basename(png),
              "post_id": post_id, "immagine": url_img})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERRORE: {e}")
        sys.exit(1)
