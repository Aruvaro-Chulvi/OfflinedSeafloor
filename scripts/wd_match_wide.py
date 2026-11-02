"""Segundo pase del cruce con Wikidata (tras wd_match.py): todos los relieves submarinos de
Wikidata con coordenadas (subclases de «undersea landform», Q55182671) se emparejan con el
nomenclátor GEBCO por el núcleo del nombre (sin la palabra del tipo, en cualquiera de los 10
idiomas o en el título del artículo) y la cercanía. Los emparejados del primer pase se quedan.
Entrada/salida: wd.json en SEAFLOOR_WORK (se guarda una copia wd_pass1.json la primera vez)."""
import json, re, time, unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import requests
from shapely.geometry import Point

from wd_match import HERE, LANGS, load, sparql

CACHE = HERE / "wd_wide_cand.json"
INFO_CACHE = HERE / "wd_wide_info.json"

# Palabras del tipo y de enlace (inglés y las lenguas con alfabeto latino); se quitan del nombre
TYPE_WORDS = set("""
seamount seamounts chain group province guyot guyots tablemount knoll knolls hill hills bank banks shoal shoals bars
ground reef reefs peak cap mound mounds cone mud volcano caldera calderas pingos ridge ridges sand dome rise spur finger
promontory lobe plateau borderland terrace shelf slope continental apron escarpment scarp discordance fracture zone
system trench deep deeps hole trough rift basin seabight re entrant abyssal plain canyon canyons valley valleys sea
channel seachannel levee fan gap passage pass saddle sill undersea submarine underwater mid ocean oceanic feature
monte montes submarino submarinos submarina submarinas cadena montículo monticulo colina colinas banco bajo arrecife pico
cono volcan lodo dorsal dorsales elevacion espolon meseta terraza plataforma talud escarpe zona fractura fosa abismo
hoya depresion cuenca llanura abisal canon canones valle canal abanico paso collado umbral provincia relieve guyote
mont monts marin marins sous chaine butte colline collines banc haut fond recif pic monticule volcan boue caldeira
dorsale elevation eperon plateau terrasse plate forme talus escarpement fosse abysse trou auge bassin plaine abyssale
chenal eventail col seuil
monte monti sottomarino sottomarini sottomarina catena collinetta secca scogliera picco monticello vulcano fango rialzo
sperone piattaforma scarpata frattura fossa abisso buca depressione bacino piana abissale valle canale conoide passaggio
sella soglia
tiefseeberg tiefseeberge tiefseebergkette kuppe unterseeischer unterseeische unterseeisches hugel untiefe riff gipfel
kegel schlammvulkan rucken schwelle sporn terrasse schelf hang steilhang bruchzone tiefseegraben graben tief loch trog
becken tiefseeebene tal tiefseerinne tiefseefacher durchlass sattel provinz
cadeia baixio recife vulcao lama elevacao esporao planalto terraco talude escarpa fratura fosso bacia planicie abissal
canhao canhoes vale leque passagem sela soleira provincia relevo
the of and de del la las los el du des le les di della dei delle do da dos das von der die das am an im in al d l
""".split())


# Familias de tipo: un relieve solo se empareja con un ítem de la misma familia
# (si no, «Florida Valley» acabaría en «Florida Reef»)
FAMILIES = {
    "mount": "seamount seamounts guyot guyots tablemount knoll knolls hill hills bank banks shoal shoals bars ground reef reefs "
             "peak cap mound mounds cone volcano caldera calderas pingos monte montes guyote montículo monticulo colina colinas "
             "banco bajo arrecife pico cono volcan mont monts butte colline collines banc recif pic monticule caldeira monti "
             "collinetta secca scogliera picco monticello vulcano tiefseeberg tiefseeberge kuppe hugel untiefe riff gipfel kegel "
             "baixio recife vulcao",
    "ridge": "ridge ridges rise spur finger promontory lobe dorsal dorsales elevacion espolon dorsale elevation eperon rialzo "
             "sperone rucken schwelle sporn elevacao esporao",
    "plateau": "plateau plateaus borderland terrace meseta terraza terrasse terrazza planalto terraco",
    "shelf": "shelf plataforma schelf piattaforma",
    "slope": "slope apron escarpment scarp discordance talud escarpe talus escarpement scarpata hang steilhang talude escarpa",
    "fz": "fracture fractura frattura bruchzone fratura",
    "trench": "trench trough deep deeps hole rift fosa abismo hoya fosse abysse trou auge fossa abisso buca tiefseegraben graben "
              "tief loch trog fosso",
    "basin": "basin plain seabight cuenca llanura bassin plaine bacino piana becken tiefseeebene bacia planicie",
    "channel": "canyon canyons valley valleys channel seachannel gap passage pass canon canones valle canal paso chenal col "
               "valle canale passaggio tal tiefseerinne durchlass canhao canhoes vale passagem",
    "fan": "fan abanico eventail conoide tiefseefacher leque",
    "sill": "sill saddle umbral collado seuil soglia sella sattel soleira sela",
}
FAMILY_OF = {w: fam for fam, ws in FAMILIES.items() for w in ws.split()}


def families(s):
    return {FAMILY_OF[w] for w in norm(s) if w in FAMILY_OF}


def norm(s):
    s = re.sub(r"\(.*?\)", " ", s or "")
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return [w for w in re.split(r"[^a-z0-9]+", s) if w]


def core(s):
    return " ".join(w for w in norm(s) if w not in TYPE_WORDS)


def similar(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if min(len(a), len(b)) < 4:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def fetch_candidates():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    rows = sparql("""SELECT ?i ?c WHERE { ?i wdt:P31/wdt:P279* wd:Q55182671 ; wdt:P625 ?c . }""")
    cand = defaultdict(lambda: {"pts": [], "names": []})
    for b in rows:
        m = b["c"]["value"]
        if not m.startswith("Point("):
            continue
        lon, lat = map(float, m[6:-1].split())
        cand[b["i"]["value"].rsplit("/", 1)[1]]["pts"].append((lon, lat))
    qs = sorted(cand)
    print("candidates", len(qs), flush=True)
    langs = ", ".join(f'"{l}"' for l in LANGS)
    for i in range(0, len(qs), 300):
        vals = " ".join(f"wd:{q}" for q in qs[i:i + 300])
        res = sparql(f"""SELECT ?i ?n WHERE {{ VALUES ?i {{ {vals} }}
          {{ ?i rdfs:label ?n FILTER(LANG(?n) IN ({langs})) }} UNION {{ ?i skos:altLabel ?n FILTER(LANG(?n) = "en") }}
          UNION {{ ?a schema:about ?i ; schema:isPartOf ?site ; schema:name ?n ; schema:inLanguage ?wl .
                   FILTER(STRENDS(STR(?site), ".wikipedia.org/")) FILTER(?wl IN ({langs})) }} }}""")
        for b in res:
            cand[b["i"]["value"].rsplit("/", 1)[1]]["names"].append(b["n"]["value"])
        print("names", i + 300, "/", len(qs), flush=True)
        time.sleep(1)
    out = {q: v for q, v in cand.items()}
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def fetch_info(qs):
    info = json.loads(INFO_CACHE.read_text(encoding="utf-8")) if INFO_CACHE.exists() else {}
    todo = [q for q in qs if q not in info]
    langs = ", ".join(f'"{l}"' for l in LANGS)
    for i in range(0, len(todo), 200):
        vals = " ".join(f"wd:{q}" for q in todo[i:i + 200])
        for q in todo[i:i + 200]:
            info.setdefault(q, {"l": {}, "w": {}})
        res = sparql(f"""SELECT ?i ?lab ?art ?wl WHERE {{ VALUES ?i {{ {vals} }}
          {{ ?i rdfs:label ?lab FILTER(LANG(?lab) IN ({langs})) }}
          UNION
          {{ ?art schema:about ?i ; schema:isPartOf ?site ; schema:inLanguage ?wl .
             FILTER(STRENDS(STR(?site), ".wikipedia.org/")) FILTER(?wl IN ({langs})) }} }}""")
        for b in res:
            d = info[b["i"]["value"].rsplit("/", 1)[1]]
            if "lab" in b:
                d["l"][b["lab"]["xml:lang"]] = b["lab"]["value"]
            if "art" in b:
                t = requests.utils.unquote(b["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
                d["w"][b["wl"]["value"]] = t
        print("info", i + 200, "/", len(todo), flush=True)
        time.sleep(1)
    INFO_CACHE.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    return info


# Revisados a mano: el ítem es otra cosa (la isla, la cuenca entera…)
BLOCK = {"Parece Vela Hill Province", "Guinea Abyssal Plain"}
# Revisados a mano: el mismo relieve, aunque el ítem sea de otra clase o tenga otro nombre
# (Wikidata da «Hawaiian Ridge» como alias de la cadena Hawái-Emperador)
MANUAL = {"Hawaiian Ridge": "Q632794"}


def flat(s):
    s = unicodedata.normalize("NFD", (s or "").lower().replace("–", "-").replace("—", "-"))
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def gdist(g, lon, lat):
    return min(g.distance(Point(lon, lat)), g.distance(Point(lon - 360, lat)), g.distance(Point(lon + 360, lat)))


def main():
    pass1_path = HERE / "wd_pass1.json"
    if not pass1_path.exists():
        pass1_path.write_text((HERE / "wd.json").read_text(encoding="utf-8"), encoding="utf-8")
    pass1 = json.loads(pass1_path.read_text(encoding="utf-8"))
    feats = load()
    cand = fetch_candidates()
    used = {v["q"] for v in pass1.values()}

    # Índice por celdas de 5° para no comparar cada relieve con los 15.000 candidatos
    cell = defaultdict(list)
    for q, c in cand.items():
        if q in used:
            continue
        cores = {core(n) for n in c["names"]} - {""}
        typed = {" ".join(norm(n)) for n in c["names"]}
        fams = set().union(*(families(n) for n in c["names"]))
        if not cores:
            continue
        for lon, lat in c["pts"]:
            cell[(int((lon + 180) // 5), int((lat + 90) // 5))].append((q, lon, lat, cores, typed, fams))

    hits = defaultdict(list)          # fid -> [(score, dist, q)]
    for fid, f in feats.items():
        if str(fid) in pass1 or f"{f['name']} {f['type']}" in BLOCK:
            continue
        fc = core(f["name"])
        if not fc:
            continue
        ftyped = " ".join(norm(f"{f['name']} {f['type']}"))
        ffam = families(f["type"])
        thr = 2.5 if f["ext"] > 1 else 1.0
        cx, cy = int((f["lon"] + 180) // 5), int((f["lat"] + 90) // 5)
        seen = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q, lon, lat, cores, typed, fams in cell.get(((cx + dx) % 72, cy + dy), []):
                    if q in seen:
                        continue
                    s = max(similar(fc, c) for c in cores)
                    if s < 0.88:
                        continue
                    d = gdist(f["g"], lon, lat)
                    if d > (thr if s == 1.0 else thr * 0.6):
                        continue
                    # Tipo de otra familia: no. Sin tipo reconocible: solo con el nombre idéntico y muy cerca
                    if fams and ffam and not (fams & ffam):
                        continue
                    if (not fams or not ffam) and (s < 1.0 or d > 0.5):
                        continue
                    seen.add(q)
                    # Mismo nombre y además el mismo tipo en inglés: casi seguro
                    hits[fid].append((s + (0.5 if ftyped in typed else 0), -d, q))
    match = {}
    for fid, hs in hits.items():
        hs.sort(reverse=True)
        # Dos candidatos igual de buenos: no se sabe cuál es
        if len(hs) > 1 and hs[0][0] == hs[1][0] and abs(hs[0][1] - hs[1][1]) < 0.05:
            continue
        match[fid] = (hs[0][2], hs[0][0], hs[0][1])
    # Un Q para varios relieves: se queda el de mejor puntuación si es el único; si no, ninguno
    by_q = defaultdict(list)
    for fid, (q, s, nd) in match.items():
        by_q[q].append((s, nd, fid))
    final = {}
    for q, lst in by_q.items():
        lst.sort(reverse=True)
        if len(lst) == 1 or lst[0][:2] != lst[1][:2] and lst[0][0] > lst[1][0]:
            final[lst[0][2]] = q
    print("new matches", len(final))
    # Tercer pase: el nombre completo idéntico («NAME TYPE» = etiqueta o alias, sin espacios ni guiones),
    # único a los dos lados, hasta 25°: el punto de Wikidata de las grandes dorsales y cuencas suele caer
    # en un extremo, lejos de la línea de GEBCO (Lomonósov, Aleutianas, Dorsal Centroíndica…)
    taken = used | set(final.values())
    by_label = defaultdict(set)
    for q, c in cand.items():
        if q not in taken:
            for nm in c["names"]:
                by_label[flat(nm)].add(q)
    gebco_names = defaultdict(int)
    for f in feats.values():
        gebco_names[flat(f"{f['name']} {f['type']}")] += 1
    exact = {}
    for fid, f in feats.items():
        key = flat(f"{f['name']} {f['type']}")
        if str(fid) in pass1 or fid in final or gebco_names[key] != 1 or len(by_label.get(key, ())) != 1:
            continue
        q = next(iter(by_label[key]))
        if min(gdist(f["g"], lon, lat) for lon, lat in cand[q]["pts"]) <= 25:
            exact[fid] = q
    cnt = defaultdict(int)
    for q in exact.values():
        cnt[q] += 1
    exact = {fid: q for fid, q in exact.items() if cnt[q] == 1}
    print("exact-name matches", len(exact))
    final.update(exact)
    # A mano: ítems que no son de la clase «undersea landform» o con otro nombre en Wikidata
    for fid, f in feats.items():
        q = MANUAL.get(f"{f['name']} {f['type']}")
        if q and str(fid) not in pass1 and q not in set(final.values()):
            final[fid] = q
    info = fetch_info(sorted(set(final.values())))
    out = dict(pass1)
    for fid, q in final.items():
        out[str(fid)] = {"q": q, **info.get(q, {"l": {}, "w": {}})}
    (HERE / "wd.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    from collections import Counter
    c = Counter(l for v in out.values() for l in v.get("w", {}))
    print("matched total", len(out), "with article", sum(1 for v in out.values() if v.get("w")), dict(c))
    # Muestra para revisar a mano
    for fid, q in list(final.items()):
        f = feats[fid]
        print(f"  {f['name']} {f['type']} -> {q} {info.get(q, {}).get('l', {}).get('en') or info.get(q, {}).get('l', {}).get('es')}")


if __name__ == "__main__":
    main()
