# -*- coding: utf-8 -*-
"""
Konfiguráció: kerületek, kategória- és konyha-kulcsszavak, referenciapontok.
Ezeket a fejlesztő szabadon bővítheti / módosíthatja, nincs bennük AI-hívás,
tisztán kódba írt szótárak.
"""

# ---------------------------------------------------------------------------
# Célkerületek: {menicka.cz slug: megjelenített név}
# ---------------------------------------------------------------------------
DISTRICTS = {
    "praha-1": "Praha 1",
    "praha-3": "Praha 3",
    "praha-7": "Praha 7",
    "praha-8": "Praha 8",
}

BASE_URL = "https://www.menicka.cz/{slug}.html"

# ---------------------------------------------------------------------------
# Referenciapontok a távolságszámításhoz (Haversine)
# Megjegyzés: a koordináták közelítő értékek utcaszintű pontossággal.
# Pontosításhoz nézd meg Google Maps-en (jobb klikk -> koordináták másolása)
# és írd felül az alábbi értékeket.
# ---------------------------------------------------------------------------
REFERENCE_POINTS = {
    "A": {
        "label": "Pont A – Strojnická 7, Praha 7-Holešovice",
        "address": "Strojnická 1430/7, 170 00 Praha 7-Holešovice",
        "lat": 50.1016,
        "lng": 14.4345,
    },
    "B": {
        "label": "Pont B – Rohanské nábř. 661, Karlín",
        "address": "Rohanské nábř. 661, 186 00 Praha 8-Karlín",
        "lat": 50.0942,
        "lng": 14.4530,
    },
}

# Átlagos gyalogsebesség (km/h) a becsült gyaloglási időhöz
WALK_SPEED_KMH = 5.0

# ---------------------------------------------------------------------------
# KATEGÓRIA kulcsszavak (étel kategorizálás)
# A kulcsszavak kisbetűsek és ékezet nélküliek (a matching normalizálva fut).
# Ha egy sorra több kategória is illik, a lista sorrendje dönt (felülről lefelé).
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "leves": [
        "polevka", "vyvar", "krem", "kaldoun", "gazpacho", "kulajda",
    ],
    "saláta": [
        "salat", "insalata",
    ],
    "desszert": [
        "dort", "palacinka", "brownies", "posset", "kolac", "zmrzlina", "strudl",
    ],
    "ital": [
        "pivo", "limonada", "juice", "vino", "kola", "colu", "cola",
        "0,3l", "0,2l", "0,5l", "0,4l", "0.3l", "0.2l", "0.5l", "0.4l",
    ],
}
DEFAULT_CATEGORY = "főétel"
# A kategória-ellenőrzés sorrendje (fontos, mert pl. egy "gulášová polévka"
# elsőként a levesbe essen, ne a főételbe)
CATEGORY_ORDER = ["leves", "saláta", "desszert", "ital"]

# ---------------------------------------------------------------------------
# KONYHA TÍPUS kulcsszavak
# ---------------------------------------------------------------------------
CUISINE_KEYWORDS = {
    "cseh": [
        "gulas", "svickova", "vyvar", "knedlik", "rizek", "bramborak",
        "kyselo", "pecene",
    ],
    "ázsiai": [
        "pho", "bibimbap", "curry", "kari", "teriyaki", "wok", "sushi",
        "nem ", "wagyu", "poke",
    ],
    "olasz": [
        "pasta", "pizza", "risotto", "spaghetti", "lasagne", "gnocchi",
        "tagliatelle", "penne",
    ],
    "mexikói": [
        "quesadilla", "enchilada", "burrito", "fajita",
    ],
}
DEFAULT_CUISINE = "egyéb"
CUISINE_ORDER = ["cseh", "ázsiai", "olasz", "mexikói"]

# HTTP fejlécek a scrapinghez (udvarias User-Agent)
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PragueLunchMenuBot/1.0; "
        "+https://github.com/; personal non-commercial lunch menu aggregator)"
    ),
    "Accept-Language": "cs,en;q=0.8",
}

REQUEST_TIMEOUT = 20  # másodperc
REQUEST_DELAY_SEC = 1.5  # udvarias késleltetés a kerület-oldalak lekérése között