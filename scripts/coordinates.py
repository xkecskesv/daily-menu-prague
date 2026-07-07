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

    # --- Automatikusan geokódolva (OpenStreetMap Nominatim) ---
    "1886-u-jindrisske-veze": (50.0844909, 14.4294297),  # U Jindřišské věže – Praha 1 (automatikus)
    "2103-hostinec-u-rotundy": (50.0825609, 14.4145029),  # Hostinec u Rotundy – Praha 1 (automatikus)
    "2366-restaurace-u-3-trojek": (50.0867767, 14.4551214),  # Restaurace U 3 trojek – Praha 3 (automatikus)
    "4834-ztraceny-raj": (50.100903, 14.420886),  # Ztracený ráj – Praha 7 (automatikus)
    "5118-holesovicka-sedma": (50.1004146, 14.433158),  # Holešovická Sedma – Praha 7 (automatikus)
    "6481-stereo": (50.1007103, 14.4241421),  # Stereo – Praha 7 (automatikus)
    "6512-u-houbare": (50.1011823, 14.4334155),  # U Houbaře – Praha 7 (automatikus)
    "6513-domazlicka-jizba": (50.0990756, 14.4338613),  # Domažlická Jizba – Praha 7 (automatikus)
    "9302-fuze": (50.0884511, 14.4348986),  # FUZE – Praha 1 (automatikus)
    "9425-u-tri-zlatych-trojek": (50.0889728, 14.4050058),  # U tří zlatých trojek – Praha 1 (automatikus)
    "9733-spravovna": (50.0791413, 14.4483217),  # Spravovna – Praha 3 (automatikus)
    "9868-himalaya-restaurant": (50.0784915, 14.4225485),  # Himalaya Restaurant – Praha 1 (automatikus)
    "9914-jidelna-svetozor": (50.0816884, 14.4250275),  # Jídelna SVĚTOZOR – Praha 1 (automatikus)
}
