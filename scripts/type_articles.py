"""Artículo de Wikipedia que explica cada tipo de relieve («¿Qué es un monte submarino?») → type_wd.json
en SEAFLOOR_WORK; build_features.py lo mete en seafloor_features.json como "tw": {clave: {idioma: título}}.
Las claves son las de la app (seafloor.js, SF_KEYS). Solo tipos con un artículo que explica exactamente
ese concepto; los ambiguos se quedan sin enlace (en Wikidata «saddle» es la silla de montar y «sill»
el filón de roca, por ejemplo)."""
import json, time
import requests
from wd_match import HERE, LANGS, sparql

TYPE_Q = {
    "seamount": "Q503269", "seamounts": "Q503269", "chain": "Q503269",   # Monte submarino
    "guyot": "Q151957",                                                   # Guyot
    "bank": "Q2897058",                                                   # Banco (geografía)
    "shoal": "Q28337",                                                    # Banco de arena / bajo
    "reef": "Q184358",                                                    # Arrecife
    "mudvolcano": "Q193457",                                              # Volcán de lodo
    "caldera": "Q159954",                                                 # Caldera volcánica
    "pingo": "Q613963",                                                   # Pingo
    "plateau": "Q1271224",                                                # Meseta oceánica
    "shelf": "Q134851",                                                   # Plataforma continental
    "slope": "Q1031696",                                                  # Talud continental
    "escarpment": "Q1174791",                                             # Escarpe
    "fz": "Q5477586",                                                     # Zona de fractura
    "trench": "Q119253",                                                  # Fosa oceánica
    "trough": "Q1068705",                                                 # Trough (geology)
    "basin": "Q1069932",                                                  # Cuenca oceánica
    "plain": "Q570554",                                                   # Llanura abisal
    "canyon": "Q963729", "canyons": "Q963729",                            # Cañón submarino
    "channel": "Q4054763",                                                # Abyssal channel
}


def main():
    qs = sorted(set(TYPE_Q.values()))
    langs = ", ".join(f'"{l}"' for l in LANGS)
    w = {q: {} for q in qs}
    for b in sparql(f"""SELECT ?i ?art ?wl WHERE {{ VALUES ?i {{ {" ".join("wd:" + q for q in qs)} }}
      ?art schema:about ?i ; schema:isPartOf ?site ; schema:inLanguage ?wl .
      FILTER(STRENDS(STR(?site), ".wikipedia.org/")) FILTER(?wl IN ({langs})) }}"""):
        w[b["i"]["value"].rsplit("/", 1)[1]][b["wl"]["value"]] = \
            requests.utils.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
    out = {k: w[q] for k, q in TYPE_Q.items() if w[q]}
    (HERE / "type_wd.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    for k, v in out.items():
        print(k, "|", v.get("es"), "|", v.get("en"), "|", len(v), "langs")


if __name__ == "__main__":
    main()
