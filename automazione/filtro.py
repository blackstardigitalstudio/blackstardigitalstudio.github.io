# -*- coding: utf-8 -*-
"""
filtro.py — tiene fuori dalla pubblicazione automatica le curiosita' che
possono far limitare il profilo su Instagram.

Perche' serve: i post escono da soli, anche mentre Matteo e' in vacanza.
Un contenuto segnalato non fa danni solo a se stesso — abbassa la portata
di TUTTO il profilo, e nessuno se ne accorge finche' non e' tardi.

Non e' censura del contenuto: le curiosita' restano nell'archivio e sul sito,
dove le regole sono diverse. Semplicemente non finiscono nella coda automatica.

Made in Italy
"""
import re

# Solo cio' che le regole di Meta trattano davvero come delicato.
# Parole intere (\b), per non prendere "farmaco" dentro "arma".
DELICATO = re.compile(
    r"\b("
    r"porno\w*|erotic\w*|prostitu\w*|bordell\w*|"
    r"orgasm\w*|masturb\w*|ampless\w*|coit\w*|genital\w*|"
    r"suicid\w*|impicc\w*|autolesion\w*|anoress\w*|bulimi\w*|"
    r"cocain\w*|eroina|oppiace\w*|stupefacent\w*|hashish|marijuana|"
    r"stupr\w*|violenza sessuale|pedofil\w*|molest\w*|"
    r"decapit\w*|squartat\w*|sventrat\w*|mutilaz\w*"
    r")\b",
    re.IGNORECASE,
)

# Temi che si possono pubblicare ma meritano una lettura umana prima.
#
# NOTA (14/08/2026, dopo un'obiezione di Matteo, che aveva ragione):
# la storia della mafia NON sta qui dentro. Instagram vieta la GLORIFICAZIONE
# delle organizzazioni criminali, non il racconto storico: l'arresto di Riina
# e i pentiti sono lo Stato che vince, non il contrario. E' un tema con un
# pubblico vasto e appassionato, e le curiosita' sono gia' scritte.
# Quello che resta escluso e' altro: la 'ndrangheta esce per via della cocaina
# (le droghe sono un divieto esplicito di Meta), non perche' parla di mafia.
DA_GUARDARE = re.compile(
    r"\b(nazist\w*|hitler|olocaust\w*|genocid\w*|"
    r"cannibal\w*|patibolo|ghigliottin\w*)\b",
    re.IGNORECASE,
)


def testo_intero(c):
    return " ".join([c.get("titolo", ""), c.get("lead", ""), c.get("deep", "")])


def delicata(c):
    """True = fuori dalla coda automatica."""
    return bool(DELICATO.search(testo_intero(c)))


def da_controllare(c):
    """True = si puo' pubblicare, ma meglio se un umano ci da' un'occhiata."""
    return bool(DA_GUARDARE.search(testo_intero(c)))


def pulisci(elenco, silenzioso=False, prudente=True):
    """Toglie dalla lista quelle da non pubblicare in automatico.

    prudente=True (predefinito) toglie anche quelle da leggere con attenzione:
    quando pubblica una macchina e non c'e' nessuno a controllare, il dubbio
    si risolve sempre lasciando fuori. Restano comunque oltre cento contenuti."""
    buone, fuori, incerte = [], [], []
    for c in elenco:
        if delicata(c):
            fuori.append(c)
        elif prudente and da_controllare(c):
            incerte.append(c)
        else:
            buone.append(c)
    if not silenzioso and (fuori or incerte):
        print(f"      ({len(fuori)} escluse, {len(incerte)} rimandate a un controllo umano)")
    return buone


if __name__ == "__main__":
    import json, os
    QUI = os.path.dirname(os.path.abspath(__file__))
    dati = json.load(open(os.path.join(QUI, "fonte", "curiosita.json"), encoding="utf-8"))["curiosita"]

    fuori = [c for c in dati if delicata(c)]
    occhio = [c for c in dati if da_controllare(c) and not delicata(c)]

    print(f"Archivio: {len(dati)} curiosita'\n")
    print(f"FUORI dalla coda automatica: {len(fuori)}")
    for c in fuori:
        print("   -", c["titolo"])
    print(f"\nSI PUBBLICANO, ma vale la pena leggerle: {len(occhio)}")
    for c in occhio:
        print("   -", c["titolo"])
    print(f"\nBuone senza riserve: {len(dati) - len(fuori) - len(occhio)}")
