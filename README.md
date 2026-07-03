# Menička Praha — napi ebédmenü-szűrő

Statikus, kliens-oldali szűrős/kereshető oldal, ami a [menicka.cz](https://www.menicka.cz)
kiválasztott prágai kerület-oldalait (Praha 1, 3, 7, 8) dolgozza fel, kategorizálja és
konyha-típus szerint címkézi az ételeket (fix, kódba írt kulcsszó-szótár alapján — **nincs
AI-hívás a feldolgozásban**), és egyetlen önálló `docs/index.html` fájlba renderel. A repó
GitHub Actions-szel naponta automatikusan újrafuttatja a scrapert, és GitHub Pages-en
publikálja az eredményt.

## Repó-struktúra

```
.
├── scripts/
│   ├── scrape_menicka.py   # scraper + HTML-generátor (fő belépési pont)
│   ├── config.py           # kerületek, kategória-/konyha-kulcsszavak, referenciapontok
│   └── coordinates.py      # statikus étterem-koordináta tábla (manuálisan karbantartva)
├── templates/
│   └── index.html.j2       # Jinja2 sablon: az egész oldal (CSS + JS egy fájlban)
├── docs/
│   └── index.html          # GENERÁLT kimenet — ez a GitHub Pages forrása
├── .github/workflows/
│   └── update.yml          # napi cron: scraper futtatása + docs/index.html commitolása
└── requirements.txt
```

## Első üzembe helyezés

1. **Repó létrehozása / feltöltés.** Töltsd fel ezt a struktúrát egy GitHub repóba (public
   vagy private, mindkettő működik Actions-szel; publikus Pages-hez ha private repó, Pro/Team
   csomag kell — érdemes publikusra tenni, ha ez nem gond).

2. **GitHub Pages bekapcsolása.**
   Repó → *Settings* → *Pages* → *Build and deployment* → *Source*: **Deploy from a branch** →
   *Branch*: `main`, mappa: **`/docs`** → *Save*.
   Néhány percen belül élesedik az oldal a `https://<felhasználó>.github.io/<repó>/` címen.

3. **Actions engedélyezése írási joggal.**
   Repó → *Settings* → *Actions* → *General* → *Workflow permissions* → **Read and write
   permissions** (a workflow maga is beállítja a `permissions: contents: write`-ot, de a repó
   szintű alapértelmezést is érdemes engedélyezőre állítani, különben a push elbukhat).

4. **Első manuális futtatás.**
   Repó → *Actions* → *Ebédmenü frissítése* → *Run workflow* → *Run workflow*.
   Ez legenerálja a `docs/index.html`-t és commitolja. Ha ez lefutott, a Pages oldal élesben
   is mutatja az első adatokat.

Ezután a workflow hétköznaponta (hét minden napján 09:15 UTC-kor — ld. lent) automatikusan
lefut, és ha van tartalmi változás, commitolja + pusholja a friss `docs/index.html`-t.

> **Cron időzítés:** a `.github/workflows/update.yml`-ben a `cron: "15 9 * * 1-5"` UTC-ben
> hétköznap 09:15-kor fut (ez CET/CEST szerint kb. 10:15/11:15, tehát ebéd előtt). GitHub
> Actions cronja nem garantáltan pontos időpontban indul (percekig csúszhat forgalmas
> időszakokban) — ha ez gond, indíts korábbra időzítve, vagy futtasd többször naponta.

## Koordináták feltöltése (a távolság-számításhoz)

A `scripts/coordinates.py` fájl szándékosan üresen (vagy néhány példával) indul. A
`--debug` kapcsolóval futtatott scraper kiírja a hiányzó slugokat és az étterem nevét/kerületét:

```bash
cd scripts
pip install -r ../requirements.txt
python scrape_menicka.py --debug --out /tmp/test.html
```

A log végén egy másolható lista jelenik meg, pl.:

```
"5750-snemovna-v-jakubsky": (LAT, LNG),  # Sněmovna v Jakubský – Praha 1
```

Ezt keresd meg Google Maps-en (jobb klikk a helyre → az első sor a koordináta), majd írd be
a `coordinates.py`-ba. Amíg egy étteremhez nincs koordináta, a szűrő és a lista változatlanul
működik rá — csak a távolság/gyaloglási idő mező marad üres nála.

## Helyi fejlesztés / tesztelés

```bash
pip install -r requirements.txt
python scripts/scrape_menicka.py --debug
# vagy offline fixture-ökkel, ha van mentett HTML-ed a kerület-oldalakról:
python scripts/scrape_menicka.py --offline fixtures/ --debug
```

A kimenet alapból `docs/index.html`. Nyisd meg böngészőben — az oldal teljesen kliens-oldali,
nincs szükség szerverre.

## Testreszabás

- **Kerületek, kulcsszavak, referenciapontok:** `scripts/config.py` — tiszta Python
  szótárak, AI-hívás nélkül, bátran bővíthető.
- **Design / elrendezés / szűrőlogika:** `templates/index.html.j2` — egyetlen fájlban van a
  CSS és a JS is, külső függőség nélkül. A JSON adat a `#restaurants-data`
  `<script type="application/json">` tag-ben landol, onnan olvassa be a kliens-oldali JS.
- **Ütemezés:** `.github/workflows/update.yml` → `cron` sor.

## Megjegyzések

- A parser két rétegű (ismert CSS-minták, majd szöveg-alapú fallback), mert a menicka.cz
  DOM-ja időnként változhat. Ha egyszer csak 0 éttermet talál, először `--debug`-bal nézd meg
  a logot, és ha kell, frissítsd a `find_restaurant_blocks` / `parse_restaurant_block`
  szelektorait a `scripts/scrape_menicka.py`-ban.
- A scraper udvarias `User-Agent`-et küld és késleltetést tart a kérések között
  (`config.REQUEST_DELAY_SEC`) — ezt ne vedd ki, ez véd a felesleges terheléstől.
- Az oldal minden szöveges tartalmat (étel-/étteremnév) HTML-escape-el a beillesztés előtt,
  így a scrapelt adat nem futtathat be tetszőleges HTML-t a böngészőben.