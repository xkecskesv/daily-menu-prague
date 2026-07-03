# -*- coding: utf-8 -*-
"""
STATIKUS KOORDINÁTA-TÁBLA
==========================
Ezt a fájlt a fejlesztő (Te) tartja karban manuálisan.

Kulcs: az étterem "slug"-ja, azaz a menicka.cz-s URL-jéből az azonosító rész.
       Pl. a "https://www.menicka.cz/5750-snemovna-v-jakubsky.html" URL-hez
       tartozó kulcs: "5750-snemovna-v-jakubsky"
       (a scraper pontosan ezt a kulcsot generálja minden étteremhez, lásd
       scrape_menicka.py -> extract_slug(), és --debug futtatásnál kiírja
       a hiányzó kulcsokat, hogy könnyű legyen pótolni őket).

Érték: (lat, lng) tuple, Google Maps-ről vagy Nominatim-ról másolva.
       Google Maps-en: jobb klikk a helyre -> az első sor a koordináta.

Ha egy étteremhez nincs bejegyzés itt, a generált oldalon egyszerűen nem
jelenik meg távolság / gyaloglási idő az adott étteremnél (a szűrés és a
többi funkció változatlanul működik).

Ez a fájl szándékosan üres induláskor (vagy néhány példával) - a
--debug kapcsolóval futtatott scraper kiírja a hiányzó slugokat és az
étterem nevét/kerületét, hogy könnyen fel tudd tölteni.
"""

# Formátum: "slug": (lat, lng)
COORDINATES: dict[str, tuple[float, float]] = {
    # --- PÉLDA BEJEGYZÉSEK (töröld / írd felül valós adatokkal) ---
    # "5750-snemovna-v-jakubsky": (50.0879, 14.4208),
    # "9302-fuze": (50.0862, 14.4223),
    # "7116-malostranska-beseda": (50.0879, 14.4045),
}