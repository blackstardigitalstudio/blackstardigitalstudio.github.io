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
    r"porno\w*|pornografic\w*|erotic\w*|prostitu\w*|bordell\w*|"
    r"orgasm\w*|masturbaz\w*|ampless\w*|"
    r"suicid\w*|impiccat\w*|autolesion\w*|anoressi\w*|"
    r"cocain\w*|eroina|oppiacei|stupefacent\w*|"
    r"stupr\w*|violenza sessuale|pedofil\w*|"
    r"decapitat\w*|squartat\w*|sventrat\w*"
    r")\b",
    re.IGNORECASE,
)

# Temi che si possono pubblicare ma meritano una lettura umana prima.
DA_GUARDARE = re.compile(
    r"\b(nazist\w*|hitler|olocaust\w*|genocid\w*|'ndranghet\w*|cosa nostra|"
    r"camorr\w*|attentat\w*|strage|terroris\w*)\b",
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


def pulisci(elenco, silenzioso=False):
    """Toglie dalla lista quelle da non pubblicare in automatico."""
    buone, fuori = [], []
    for c in elenco:
        (fuori if delicata(c) else buone).append(c)
    if fuori and not silenzioso:
        print(f"      ({len(fuori)} messe da parte: non adatte alla pubblicazione automatica)")
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
