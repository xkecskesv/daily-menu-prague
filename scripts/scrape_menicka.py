#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prágai ebédmenü-szűrő – scraper + statikus HTML generátor
===========================================================

Lekéri a menicka.cz megadott kerület-oldalait, kinyeri az aznapi
ebédmenüket, kategorizálja és konyha-típus szerint címkézi őket
(fix kulcsszó-szótár alapján, NEM AI-hívással), kiszámolja a becsült
gyalogos távolságot két referenciaponttól, majd egyetlen önálló
`docs/index.html` fájlba renderel egy kliens-oldali szűrős/kereshető
felületet (Jinja2 sablon, minden CSS/JS egy fájlban, külső függőség
nélkül a végtermékben).

Használat:
    python scrape_menicka.py                  # éles futás, docs/index.html
    python scrape_menicka.py --debug           # részletes diagnosztika
    python scrape_menicka.py --offline fixtures/  # helyi HTML fájlokból
    python scrape_menicka.py --out docs/index.html

A menicka.cz DOM-szerkezete idővel változhat, ezért a parser két
rétegű: elsőként ismert CSS-mintákat próbál (div#menicka-<id>, h2>a,
ár-span-ek), majd ha ez nem talál semmit, szöveg-alapú (regex) fallback-re
vált. `--debug` kapcsolóval a script kiírja, hány éttermet/ételt talált
kerületenként, és mely éttermekhez hiányzik koordináta a
coordinates.py táblából.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover
    print("Hiányzik a 'requests' csomag. Telepítsd: pip install -r requirements.txt")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    print("Hiányzik a 'beautifulsoup4' csomag. Telepítsd: pip install -r requirements.txt")
    sys.exit(1)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:  # pragma: no cover
    print("Hiányzik a 'jinja2' csomag. Telepítsd: pip install -r requirements.txt")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scripts.config as config  # noqa: E402
from scripts.coordinates import COORDINATES  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("menicka")


# ---------------------------------------------------------------------------
# Adatmodell
# ---------------------------------------------------------------------------
@dataclass
class MenuItem:
    name: str
    price: int
    category: str
    cuisine: str


@dataclass
class Restaurant:
    slug: str
    name: str
    district_slug: str
    district_name: str
    url: str
    items: list = field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    dist_a_km: Optional[float] = None
    dist_a_min: Optional[int] = None
    dist_b_km: Optional[float] = None
    dist_b_min: Optional[int] = None


# ---------------------------------------------------------------------------
# Szöveg-normalizálás és kategorizálás (fix kulcsszó-szótár, nincs AI hívás)
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text: str) -> str:
    return strip_accents(text).lower()


def categorize(name: str) -> str:
    norm = normalize(name)
    for cat in config.CATEGORY_ORDER:
        keywords = config.CATEGORY_KEYWORDS[cat]
        for kw in keywords:
            if strip_accents(kw).lower() in norm:
                return cat
    return config.DEFAULT_CATEGORY


def detect_cuisine(name: str) -> str:
    norm = normalize(name)
    for cuisine in config.CUISINE_ORDER:
        keywords = config.CUISINE_KEYWORDS[cuisine]
        for kw in keywords:
            if strip_accents(kw).lower() in norm:
                return cuisine
    return config.DEFAULT_CUISINE


# ---------------------------------------------------------------------------
# Zaj-szűrés: sorok, amik biztosan NEM ételnevek (jegyzetek, admin szövegek)
# ---------------------------------------------------------------------------
NOISE_SUBSTRINGS = [
    "poznamka", "objednavky", "telefonicke objednavky", "plati od",
    "vyuzijte", "pro vyzvednuti", "gluten free =", "veg. =", "g. f. =",
    "alergeny", "zaslani menu", "pridat k oblibenym", "zavolat",
    "rozvoz", "objednat jidlo online", "zobrazit vice jidel",
    "akce dnes", "akce zitra", "hlavni jidla ----", "polevky ----",
]
JUNK_LINES_EXACT = {"zavolat", "akce dnes", "akce zítra", "rozvoz", ""}

# ár mintázatok: "170 Kč", "170,-Kč", "170 K", "170,- Kč"
PRICE_LINE_RE = re.compile(r"^\s*(\d{1,4})[\s,.\-]{0,4}K[čc]\.?\s*$", re.IGNORECASE)
PRICE_INLINE_RE = re.compile(r"(\d{2,4})\s*,?\s*-?\s*K[čc]\b", re.IGNORECASE)
ORDINAL_LINE_RE = re.compile(r"^\d{1,2}[.)]$")
MIN_PRICE, MAX_PRICE = 15, 3000


def is_noise(name: str) -> bool:
    norm = normalize(name)
    if len(norm) < 3:
        return True
    return any(sub in norm for sub in NOISE_SUBSTRINGS)


def clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" -–|,")
    # allergén-kódok levágása a végéről, pl. "... A: 1, 3, 7" vagy "(1,3,7)"
    name = re.sub(r"\(?A:?\s*[\d,\s]+\)?\s*$", "", name).strip()
    name = re.sub(r"\(\s*[\d,\s]+\)\s*$", "", name).strip()
    name = re.sub(r"\s+", " ", name).strip(" -–|,.:")
    return name


# ---------------------------------------------------------------------------
# Étterem-blokkok kinyerése a kerület-oldal HTML-jéből
# ---------------------------------------------------------------------------
def find_restaurant_blocks(soup: BeautifulSoup):
    blocks = soup.find_all("div", id=re.compile(r"^menicka-\d+$"))
    if blocks:
        return blocks
    blocks = soup.select("div.menicka")
    if blocks:
        return blocks
    blocks = soup.find_all(
        lambda tag: tag.name == "div"
        and tag.get("class")
        and any("menicka" in c.lower() for c in tag.get("class"))
    )
    return blocks


def extract_slug(href: str) -> str:
    href = href.strip()
    m = re.search(r"/?([\w\-]+)\.html", href)
    if m:
        return m.group(1)
    return re.sub(r"\W+", "-", href).strip("-")


def parse_restaurant_block(block, district_slug: str, district_name: str) -> Optional[Restaurant]:
    # --- Név + link kinyerése ---
    a_tag = None
    h2 = block.find("h2")
    if h2:
        a_tag = h2.find("a")
    if a_tag is None:
        a_tag = block.find("a", href=re.compile(r"^\d+-[\w\-]+\.html"))
    if a_tag is None or not a_tag.get_text(strip=True):
        return None

    name = clean_name(a_tag.get_text(" ", strip=True))
    href = a_tag.get("href", "")
    slug = extract_slug(href)
    url = href if href.startswith("http") else f"https://www.menicka.cz/{href.lstrip('/')}"

    if not name or not slug:
        return None

    # --- Étel-sorok kinyerése a blokk teljes szövegéből ---
    text = block.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and normalize(ln) not in JUNK_LINES_EXACT]

    # A vendéglő neve általában az első sor(ok) egyike - távolítsuk el, hogy
    # ne keveredjen bele az első étel nevébe.
    name_norm = normalize(name)
    lines = [ln for ln in lines if normalize(ln) != name_norm]

    items: list[MenuItem] = []
    buffer: list[str] = []

    def flush_buffer_with_price(price: int):
        raw_name = " ".join(buffer).strip()
        buffer.clear()
        raw_name = re.sub(r"^\d{1,2}[.)]\s*", "", raw_name)  # sorszám levágása
        raw_name = clean_name(raw_name)
        if not raw_name or is_noise(raw_name):
            return
        if not (MIN_PRICE <= price <= MAX_PRICE):
            return
        items.append(
            MenuItem(
                name=raw_name,
                price=price,
                category=categorize(raw_name),
                cuisine=detect_cuisine(raw_name),
            )
        )

    for line in lines:
        if ORDINAL_LINE_RE.match(line):
            # sorszám önálló sorban -> ez egy új elem kezdete, a régi buffer
            # (ha ár nélkül maradt) eldobjuk, mert nem tudtuk hozzá kötni az árat
            buffer.clear()
            continue

        price_only = PRICE_LINE_RE.match(line)
        if price_only:
            price = int(price_only.group(1))
            flush_buffer_with_price(price)
            continue

        inline_price = PRICE_INLINE_RE.search(line)
        if inline_price and len(line) < 220:
            price = int(inline_price.group(1))
            name_part = line[: inline_price.start()]
            buffer.append(name_part)
            flush_buffer_with_price(price)
            continue

        buffer.append(line)

    # --- Duplikátumok kiszűrése (pl. kép + szöveg kétszer felsorolva) ---
    seen = set()
    unique_items = []
    for it in items:
        key = (normalize(it.name), it.price)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(it)

    if not unique_items:
        return None  # nincs mai menü/ár -> kihagyjuk az éttermet

    return Restaurant(
        slug=slug,
        name=name,
        district_slug=district_slug,
        district_name=district_name,
        url=url,
        items=unique_items,
    )


def parse_district_html(html: str, district_slug: str, district_name: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    blocks = find_restaurant_blocks(soup)
    restaurants = []
    for block in blocks:
        try:
            r = parse_restaurant_block(block, district_slug, district_name)
        except Exception as exc:  # sosem szabad, hogy egy hibás blokk megállítsa a futást
            log.warning("Hiba egy étterem-blokk feldolgozásakor (%s): %s", district_slug, exc)
            r = None
        if r:
            restaurants.append(r)
    return restaurants


# ---------------------------------------------------------------------------
# HTTP letöltés
# ---------------------------------------------------------------------------
def fetch_district_html(slug: str) -> str:
    url = config.BASE_URL.format(slug=slug)
    log.info("Letöltés: %s", url)
    resp = requests.get(url, headers=config.HTTP_HEADERS, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# ---------------------------------------------------------------------------
# Távolságszámítás (Haversine)
# ---------------------------------------------------------------------------
def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def apply_distances(restaurants: list) -> None:
    for r in restaurants:
        coords = COORDINATES.get(r.slug)
        if not coords:
            continue
        r.lat, r.lng = coords
        for key, point in config.REFERENCE_POINTS.items():
            dist_km = haversine_km(r.lat, r.lng, point["lat"], point["lng"])
            minutes = round(dist_km / config.WALK_SPEED_KMH * 60)
            if key == "A":
                r.dist_a_km, r.dist_a_min = round(dist_km, 2), minutes
            else:
                r.dist_b_km, r.dist_b_min = round(dist_km, 2), minutes


# ---------------------------------------------------------------------------
# JSON-szerializálás a sablonhoz
# ---------------------------------------------------------------------------
def restaurants_to_json(restaurants: list) -> str:
    payload = []
    for r in restaurants:
        payload.append(
            {
                "slug": r.slug,
                "name": r.name,
                "district": r.district_name,
                "districtSlug": r.district_slug,
                "url": r.url,
                "distA_km": r.dist_a_km,
                "distA_min": r.dist_a_min,
                "distB_km": r.dist_b_km,
                "distB_min": r.dist_b_min,
                "items": [
                    {
                        "name": it.name,
                        "price": it.price,
                        "category": it.category,
                        "cuisine": it.cuisine,
                    }
                    for it in r.items
                ],
            }
        )
    return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# HTML render (Jinja2)
# ---------------------------------------------------------------------------
def render_html(restaurants: list, out_path: Path, template_dir: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("index.html.j2")

    all_prices = [it.price for r in restaurants for it in r.items]
    price_min = min(all_prices) if all_prices else 0
    price_max = max(all_prices) if all_prices else 500

    now = datetime.now(timezone.utc).astimezone()
    updated_str = now.strftime("%Y. %m. %d. %H:%M")

    html = template.render(
        restaurants_json=restaurants_to_json(restaurants),
        districts=config.DISTRICTS,
        reference_points=config.REFERENCE_POINTS,
        price_min=price_min,
        price_max=price_max,
        updated_str=updated_str,
        restaurant_count=len(restaurants),
        item_count=sum(len(r.items) for r in restaurants),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    log.info("Kimenet elmentve: %s", out_path)


# ---------------------------------------------------------------------------
# Fő futás
# ---------------------------------------------------------------------------
def run(offline_dir: Optional[Path], debug: bool, out_path: Path, template_dir: Path) -> None:
    all_restaurants: list = []

    for slug, name in config.DISTRICTS.items():
        if offline_dir:
            fixture = offline_dir / f"{slug}.html"
            if not fixture.exists():
                log.warning("Hiányzó offline fixture: %s (kihagyva)", fixture)
                continue
            html = fixture.read_text(encoding="utf-8", errors="replace")
        else:
            try:
                html = fetch_district_html(slug)
            except requests.RequestException as exc:
                log.error("Letöltési hiba (%s): %s", slug, exc)
                continue
            time.sleep(config.REQUEST_DELAY_SEC)

        restaurants = parse_district_html(html, slug, name)
        log.info("%s: %d étterem, %d étel", name, len(restaurants),
                  sum(len(r.items) for r in restaurants))
        all_restaurants.extend(restaurants)

    apply_distances(all_restaurants)

    if debug:
        missing = [r for r in all_restaurants if r.slug not in COORDINATES]
        log.info("=== DEBUG összegzés ===")
        log.info("Összes étterem: %d, összes étel: %d",
                  len(all_restaurants), sum(len(r.items) for r in all_restaurants))
        log.info("Koordináta nélküli éttermek: %d / %d", len(missing), len(all_restaurants))
        for r in missing[:50]:
            log.info('  "%s": (LAT, LNG),  # %s – %s', r.slug, r.name, r.district_name)
        if len(missing) > 50:
            log.info("  ... és még %d további", len(missing) - 50)

    if not all_restaurants:
        log.error("Nem sikerült egyetlen éttermet sem feldolgozni – a HTML nem került legenerálásra.")
        sys.exit(2)

    render_html(all_restaurants, out_path, template_dir)


def main():
    parser = argparse.ArgumentParser(description="Prágai ebédmenü scraper + HTML generátor")
    parser.add_argument("--debug", action="store_true", help="részletes diagnosztikai kimenet")
    parser.add_argument(
        "--offline", type=str, default=None,
        help="helyi könyvtár, amiben <slug>.html fixture fájlok vannak (teszteléshez)",
    )
    parser.add_argument(
        "--out", type=str, default=str(Path(__file__).resolve().parent.parent / "docs" / "index.html"),
        help="kimeneti HTML fájl útvonala (alapértelmezett: docs/index.html)",
    )
    parser.add_argument(
        "--template-dir", type=str,
        default=str(Path(__file__).resolve().parent.parent / "templates"),
        help="a Jinja2 sablonokat tartalmazó könyvtár",
    )
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    random.seed()  # csak a "Napi meglepetés" JS oldalon van random, itt nincs rá szükség

    run(
        offline_dir=Path(args.offline) if args.offline else None,
        debug=args.debug,
        out_path=Path(args.out),
        template_dir=Path(args.template_dir),
    )


if __name__ == "__main__":
    main()