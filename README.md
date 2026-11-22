# Discord RPC Szerkesztő

Egy modern, tálcán futó program, amellyel **bármit kiírhatsz a Discord profilodra** (Rich Presence): saját szöveg, kép, gombok, csapatlétszám és időzítő. A beállításaidat **profilokba** mentheted, és egy kattintással válthatsz közöttük.

> *English: a small Windows app with a modern GUI that sets a fully custom Discord Rich Presence (text, images, buttons, party size, timer), supports saved profiles and runs in the system tray. See the Hungarian setup guide below; all you need is Python 3.9+ and a Discord Application ID.*

<!-- Tegyél ide egy képernyőképet: ![Képernyőkép](screenshot.png) -->

## Funkciók

- Saját felső és alsó sor, nagy és kis kép, hover szövegek
- Akár 2 gomb linkkel
- Csapatlétszám (pl. 2/4) és "eltelt idő" időzítő
- **Képfeltöltés a gépedről** (📁 gomb)
- **Profilok**: mentsd el a különböző státuszaidat, és válts köztük
- **Élő előnézet** a Discord-kártyáról
- **Tálca ikon**: bezáráskor a háttérben fut tovább, a profilok innen is válthatók
- Az első indításkor **magától telepíti** a szükséges csomagokat

## Telepítés

### 1. Python
Töltsd le a Pythont (3.9 vagy újabb): https://www.python.org/downloads/

> Telepítéskor pipáld be az **"Add python.exe to PATH"** opciót!

### 2. A program letöltése
```
git clone https://github.com/bencejanicsak538-max/Discord-RNC-app.git
cd Discord-RNC-app
```
Vagy a GitHub oldalon: **Code → Download ZIP**, majd csomagold ki.

### 3. Indítás
Dupla kattintás a **`start.bat`** fájlra, vagy a mappában:
```
python discord_rpc_app.py
```
Első indításkor a program magától letölti a hiányzó csomagokat (`customtkinter`, `pystray`, `pillow`, `pypresence`). Ez eltarthat egy percig. Utána a program a háttérben indul, és megjelenik a tálcán (rejtett ikonok, a `^` nyíl).

Ha az automatikus telepítés nem sikerül, kézzel is megteheted:
```
python -m pip install -r requirements.txt
```

## Discord alkalmazás létrehozása (egyszeri, 2 perc)

A Discord minden státuszt egy "alkalmazáshoz" köt, ennek a neve jelenik meg a profilodon a "Játszik" mellett.

1. Nyisd meg: https://discord.com/developers/applications
2. Kattints a **New Application** gombra, és adj neki nevet (például "Fejlesztek").
3. A **General Information** oldalon másold ki az **Application ID**-t.
4. Illeszd be a programban az **Alap** fül **Client ID** mezőjébe.

## Használat

1. Indítsd el a **Discord asztali alkalmazást** (a böngészős verzió nem működik).
2. Töltsd ki a mezőket (felső sor, alsó sor, ...). Az előnézet jobb oldalon élőben mutatja az eredményt.
3. Nyomd meg az **Indítás** gombot. Később a **Frissítés** gombbal módosíthatod élőben.
4. Az ablak bezárásakor a program a tálcára kerül. Teljes kilépés: jobb klikk a tálca ikonra, majd **Kilépés**.

### Képek
- **A gépedről:** kattints a 📁 gombra a Képek fülön. A program feltölti a képet a [catbox.moe](https://catbox.moe) ingyenes tárhelyre, és beírja a linket. **A feltöltött kép nyilvános linken érhető el**, ezért ne tölts fel privát képet.
- **Saját link:** bármilyen https képlinket beírhatsz.
- **Discord Art Assets:** a Developer Portalon az alkalmazásod **Rich Presence → Art Assets** menüjében feltöltött kép nevét is beírhatod kulcsként.
- Ideális a négyzet alakú, 512×512 vagy 1024×1024 képméret (max. 8 MB).

### Profilok
- **＋ Új profil:** elmenti az aktuális beállításokat egy névvel.
- **💾 Mentés:** felülírja a kiválasztott profilt.
- **🗑 Törlés:** törli a kiválasztott profilt.
- A profilra kattintva minden mező betöltődik. Ha a státusz fut, azonnal frissül is.
- A tálca ikonon jobb klikk, majd **Profilok** menüből is válthatsz.

### Automatikus indítás a gép bekapcsolásakor (Windows)
1. Nyomj **Win + R**-t, írd be: `shell:startup`, Enter.
2. Hozz létre ebben a mappában egy parancsikont a `start.bat` fájlhoz.

## Hibaelhárítás

| Probléma | Megoldás |
|---|---|
| `python` nem található | Telepítsd újra a Pythont az "Add to PATH" opcióval, vagy használd a `py` parancsot (`py discord_rpc_app.py`). |
| Nem csatlakozik / hibaüzenet | A Discord **asztali** alkalmazásának futnia kell, és a Client ID-nak helyesnek kell lennie. |
| Nem látom a gombokat | A saját gombjaidat te nem látod, csak mások. |
| A kép nem jelenik meg | Várj pár másodpercet, majd nyomj Frissítést. A linknek https-sel kell kezdődnie. |
| Nincs semmi a Discordon | Ellenőrizd a Discord beállításaiban: **Tevékenységi adatvédelem → Tevékenységi státusz megjelenítése**. |
| A program nem indul | Nézd meg az `error.log` fájlt a program mappájában. |

## Adatvédelem

A beállításaid (Client ID, profilok, feltöltött képek linkjei) a program mappájában lévő `rpc_config.json` fájlban vannak, ez **nem kerül GitHubra** (`.gitignore`). Ha megosztod a programot, ezt a fájlt ne add tovább.

## Licenc

MIT, lásd a `LICENSE` fájlt.
