"""
Discord RPC Státusz Szerkesztő (modern, tálcás verzió)
Futtatás:  python discord_rpc_app.py
A szükséges csomagokat (lásd requirements.txt) első indításkor magától telepíti.
A Discord asztali alkalmazásnak futnia kell!
"""
import json
import os
import sys
import time
import traceback
import threading

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")


def fatal(msg):
    """Hibát ír ki, fájlba menti, és nyitva tartja az ablakot."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass
    try:
        if sys.stdout is None:
            raise RuntimeError("nincs konzol")
        print("\n===== HIBA =====\n" + msg)
        input("\nNyomj Entert a bezáráshoz...")
    except Exception:
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _r = _tk.Tk()
            _r.withdraw()
            _mb.showerror("Discord RPC hiba", msg[:1500] + "\n\n(Részletek: error.log)")
        except Exception:
            pass
    sys.exit(1)


try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except Exception:
    fatal("A tkinter nincs telepítve. Telepítsd újra a Pythont, és pipáld be a 'tcl/tk and IDLE' opciót.\n\n" + traceback.format_exc())

REQUIRED = {"customtkinter": "customtkinter", "pystray": "pystray", "PIL": "pillow", "pypresence": "pypresence"}


def ensure_packages():
    """Első indításkor automatikusan telepíti a hiányzó csomagokat."""
    import importlib
    import importlib.util
    import subprocess
    missing = [pkg for mod, pkg in REQUIRED.items() if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    print("Első indítás: hiányzó csomagok telepítése (" + ", ".join(missing) + ")...\nEz eltarthat egy percig.\n")
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + missing
    try:
        subprocess.check_call(cmd)
    except Exception:
        try:
            subprocess.check_call(cmd + ["--user"])
        except Exception:
            fatal(
                "Az automatikus telepítés nem sikerült. Telepítsd kézzel:\n\n"
                "    python -m pip install -r requirements.txt\n\n" + traceback.format_exc()
            )
    importlib.invalidate_caches()


ensure_packages()

try:
    import customtkinter as ctk
    import pystray
    from PIL import Image, ImageDraw
    from pypresence import Presence
except Exception:
    fatal(
        "Hiányzik egy csomag. Futtasd ezt a parancsot, majd indítsd újra:\n\n"
        "    python -m pip install pypresence pystray pillow customtkinter\n\n" + traceback.format_exc()
    )

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpc_config.json")

# ---------- színek ----------
BG = "#16171b"
SIDEBAR = "#1c1d22"
CARD = "#25262c"
FIELD = "#33353c"
FIELD_H = "#42444c"
FG = "#e3e5e8"
MUTED = "#8e939c"
ACCENT = "#5865f2"
ACCENT_H = "#4752c4"
GREEN = "#23a55a"
RED = "#da373c"
RED_BG = "#3b2427"

ctk.set_appearance_mode("dark")


def make_tray_image(active=False):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 62, 62), radius=16, fill=ACCENT)
    d.ellipse((18, 18, 46, 46), fill="white")
    if active:
        d.ellipse((38, 38, 60, 60), fill=GREEN, outline=BG, width=3)
    return img


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Discord RPC Szerkesztő")
        self.geometry("1120x720")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self.rpc = None
        self.start_ts = None
        self.vars = {}
        self.notified = False
        self.profiles = {}
        self.current = ""
        self.local_imgs = {}
        self._img_cache = {}
        self._pv_key = "__init__"
        self.profile_widgets = []

        self.f_h1 = ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        self.f_h2 = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        self.f_b = ctk.CTkFont(family="Segoe UI", size=13)
        self.f_bb = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.f_s = ctk.CTkFont(family="Segoe UI", size=12)
        self.f_t = ctk.CTkFont(family="Segoe UI", size=11, weight="bold")

        self.timer_mode = tk.StringVar(value="Nincs")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_sidebar()
        self.build_main()
        self.build_right()

        self.load_config()
        self.update_preview()

        self.tray = pystray.Icon(
            "discord_rpc", make_tray_image(False), "Discord RPC",
            menu=pystray.Menu(
                pystray.MenuItem("Megnyitás", lambda *_: self.after(0, self.show_window), default=True),
                pystray.MenuItem("Profilok", pystray.Menu(self.tray_profile_items)),
                pystray.MenuItem("Státusz leállítása", lambda *_: self.after(0, self.stop)),
                pystray.MenuItem("Kilépés", lambda *_: self.after(0, self.quit_app)),
            ),
        )
        self.tray.run_detached()
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.after(1000, self._tick)

    # =====================================================
    #  FELÜLET
    # =====================================================
    def build_sidebar(self):
        side = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=SIDEBAR)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(side, text="◉  Discord RPC", font=self.f_h1, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=22, pady=(26, 0))
        ctk.CTkLabel(side, text="Státusz szerkesztő", font=self.f_s, text_color=MUTED, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=22, pady=(0, 22))
        ctk.CTkLabel(side, text="PROFILOK", font=self.f_t, text_color=MUTED, anchor="w").grid(
            row=2, column=0, sticky="ew", padx=22, pady=(0, 6))

        self.profile_list = ctk.CTkScrollableFrame(side, fg_color="transparent", corner_radius=0)
        self.profile_list.grid(row=3, column=0, sticky="nsew", padx=(12, 6))

        acts = ctk.CTkFrame(side, fg_color="transparent")
        acts.grid(row=4, column=0, sticky="ew", padx=16, pady=(10, 8))
        acts.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(acts, text="＋  Új profil", height=38, corner_radius=10, font=self.f_bb,
                      fg_color=ACCENT, hover_color=ACCENT_H, command=self.new_profile
                      ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ctk.CTkButton(acts, text="💾 Mentés", height=34, corner_radius=10, font=self.f_b,
                      fg_color=FIELD, hover_color=FIELD_H, command=self.save_profile
                      ).grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(acts, text="🗑 Törlés", height=34, corner_radius=10, font=self.f_b,
                      fg_color=RED_BG, hover_color=RED, command=self.delete_profile
                      ).grid(row=1, column=1, sticky="ew", padx=(4, 0))

        pill = ctk.CTkFrame(side, fg_color=CARD, corner_radius=12)
        pill.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 18))
        self.status_dot = ctk.CTkLabel(pill, text="●", font=self.f_b, text_color=MUTED, width=20)
        self.status_dot.pack(side="left", padx=(12, 0), pady=10)
        self.status_text = ctk.CTkLabel(pill, text="Nincs csatlakozva", font=self.f_s, anchor="w",
                                        justify="left", wraplength=170)
        self.status_text.pack(side="left", padx=(2, 10), pady=10, fill="x", expand=True)

    def add_field(self, parent, key, label, placeholder="", pick=False, hint=None, horizontal=False):
        var = tk.StringVar()
        var.trace_add("write", lambda *_: self.update_preview())
        self.vars[key] = var

        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        if horizontal:
            wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        else:
            wrap.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkLabel(wrap, text=label, font=self.f_s, text_color=MUTED, anchor="w").pack(fill="x")
        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder, height=38, corner_radius=10,
                     border_width=0, fg_color=FIELD, font=self.f_b).pack(side="left", fill="x", expand=True)
        if pick:
            ctk.CTkButton(row, text="📁", width=46, height=38, corner_radius=10, fg_color=FIELD,
                          hover_color=FIELD_H, command=lambda k=key: self.pick_image(k)
                          ).pack(side="left", padx=(8, 0))
        if hint:
            ctk.CTkLabel(wrap, text=hint, font=self.f_s, text_color=MUTED, anchor="w",
                         justify="left", wraplength=420).pack(fill="x", pady=(4, 0))

    def build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(main, text="Beállítások", font=self.f_h1, anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 12))

        tabs = ctk.CTkTabview(
            main, fg_color=CARD, corner_radius=16,
            segmented_button_fg_color=FIELD, segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_H, segmented_button_unselected_color=FIELD,
            segmented_button_unselected_hover_color=FIELD_H,
        )
        tabs.grid(row=1, column=0, sticky="nsew")
        for name in ("Alap", "Képek", "Gombok", "Egyéb"):
            tabs.add(name)

        t = tabs.tab("Alap")
        self.add_field(t, "client_id", "Client ID *", "Pl. 123456789012345678",
                       hint="Discord Developer Portal → New Application → Application ID")
        self.add_field(t, "details", "Felső sor", "Pl. Fejlesztés alatt")
        self.add_field(t, "state", "Alsó sor", "Pl. Discord RPC app készítése")

        t = tabs.tab("Képek")
        self.add_field(t, "large_image", "Nagy kép", "Kulcs vagy kép link (📁 = feltöltés a gépről)", pick=True)
        self.add_field(t, "large_text", "Nagy kép szövege (hover)", "")
        self.add_field(t, "small_image", "Kis kép", "Kulcs vagy kép link", pick=True)
        self.add_field(t, "small_text", "Kis kép szövege (hover)", "")

        t = tabs.tab("Gombok")
        self.add_field(t, "btn1_label", "1. gomb felirata", "Pl. Weboldalam")
        self.add_field(t, "btn1_url", "1. gomb linkje", "https://")
        self.add_field(t, "btn2_label", "2. gomb felirata", "")
        self.add_field(t, "btn2_url", "2. gomb linkje", "https://",
                       hint="A gombokat te nem látod a saját profilodon, csak mások.")

        t = tabs.tab("Egyéb")
        ctk.CTkLabel(t, text="Csapat létszám", font=self.f_s, text_color=MUTED, anchor="w").pack(
            fill="x", padx=20, pady=(12, 0))
        pr = ctk.CTkFrame(t, fg_color="transparent")
        pr.pack(fill="x", padx=20)
        self.add_field(pr, "party_cur", "Jelenlegi", "Pl. 2", horizontal=True)
        self.add_field(pr, "party_max", "Maximum", "Pl. 4", horizontal=True)
        ctk.CTkLabel(t, text="Időzítő", font=self.f_s, text_color=MUTED, anchor="w").pack(
            fill="x", padx=20, pady=(18, 4))
        ctk.CTkSegmentedButton(
            t, values=["Nincs", "Eltelt idő"], variable=self.timer_mode, height=38, corner_radius=10,
            selected_color=ACCENT, selected_hover_color=ACCENT_H, unselected_color=FIELD,
            unselected_hover_color=FIELD_H, fg_color=FIELD, font=self.f_b,
            command=lambda _v: self.update_preview(),
        ).pack(fill="x", padx=20)

    def build_right(self):
        right = ctk.CTkFrame(self, fg_color="transparent", width=340)
        right.grid(row=0, column=2, sticky="ns", padx=(0, 24), pady=24)

        ctk.CTkLabel(right, text="Előnézet", font=self.f_h1, anchor="w").pack(fill="x", pady=(0, 12))

        card = ctk.CTkFrame(right, fg_color=CARD, corner_radius=16, width=320)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="JÁTSZIK", font=self.f_t, text_color=MUTED, anchor="w").pack(
            fill="x", padx=16, pady=(14, 8))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16)
        imgbox = ctk.CTkFrame(body, fg_color="transparent", width=96, height=96)
        imgbox.pack(side="left")
        imgbox.pack_propagate(False)
        self.pv_img = ctk.CTkLabel(imgbox, text="", width=96, height=96)
        self.pv_ph = ctk.CTkLabel(imgbox, text="🖼", font=ctk.CTkFont(size=34), width=96, height=96,
                                  fg_color=FIELD, corner_radius=12, text_color=MUTED)
        self.pv_ph.pack()

        txt = ctk.CTkFrame(body, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.pv_details = ctk.CTkLabel(txt, text="", font=self.f_bb, anchor="w", justify="left", wraplength=190)
        self.pv_details.pack(fill="x")
        self.pv_state = ctk.CTkLabel(txt, text="", font=self.f_b, anchor="w", justify="left", wraplength=190)
        self.pv_state.pack(fill="x")
        self.pv_extra = ctk.CTkLabel(txt, text="", font=self.f_s, text_color=MUTED, anchor="w",
                                     justify="left", wraplength=190)
        self.pv_extra.pack(fill="x", pady=(2, 0))

        self.pv_btnrow = ctk.CTkFrame(card, fg_color="transparent")
        self.pv_btnrow.pack(fill="x", padx=16, pady=(12, 16))
        self.pv_b1 = ctk.CTkLabel(self.pv_btnrow, text="", fg_color=FIELD, corner_radius=8, height=34, font=self.f_b)
        self.pv_b2 = ctk.CTkLabel(self.pv_btnrow, text="", fg_color=FIELD, corner_radius=8, height=34, font=self.f_b)

        self.start_btn = ctk.CTkButton(right, text="▶   Indítás", height=46, corner_radius=12, font=self.f_h2,
                                       fg_color=ACCENT, hover_color=ACCENT_H, command=self.start)
        self.start_btn.pack(fill="x", pady=(20, 8))
        self.update_btn = ctk.CTkButton(right, text="⟳   Frissítés", height=40, corner_radius=12, font=self.f_bb,
                                        fg_color=FIELD, hover_color=FIELD_H, state="disabled",
                                        command=self.update_presence)
        self.update_btn.pack(fill="x", pady=4)
        self.stop_btn = ctk.CTkButton(right, text="■   Leállítás", height=40, corner_radius=12, font=self.f_bb,
                                      fg_color=RED_BG, hover_color=RED, state="disabled", command=self.stop)
        self.stop_btn.pack(fill="x", pady=4)
        ctk.CTkButton(right, text="⏷   Tálcára", height=36, corner_radius=12, font=self.f_b,
                      fg_color="transparent", border_width=1, border_color=FIELD, hover_color=FIELD,
                      text_color=MUTED, command=self.hide_window).pack(fill="x", pady=(14, 0))

    # =====================================================
    #  ELŐNÉZET
    # =====================================================
    def preview_image(self):
        val = self.vars["large_image"].get().strip()
        path = self.local_imgs.get(val) or (val if val and os.path.isfile(val) else None)
        if not path:
            return None, None
        if path not in self._img_cache:
            try:
                im = Image.open(path).convert("RGBA")
                w, h = im.size
                s = min(w, h)
                im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((192, 192))
                self._img_cache[path] = ctk.CTkImage(light_image=im, dark_image=im, size=(96, 96))
            except Exception:
                self._img_cache[path] = None
        return path, self._img_cache[path]

    def timer_on(self):
        return self.timer_mode.get().startswith("Eltelt")

    def update_preview(self):
        if not hasattr(self, "pv_b2"):
            return
        g = lambda k: self.vars[k].get().strip()

        d, s = g("details"), g("state")
        self.pv_details.configure(text=d or "Felső sor", text_color=FG if d else MUTED)
        self.pv_state.configure(text=s or "Alsó sor", text_color=FG if s else MUTED)

        extra = []
        if g("party_cur") and g("party_max"):
            extra.append(f"({g('party_cur')} / {g('party_max')})")
        if self.timer_on():
            if self.rpc and self.start_ts:
                sec = int(time.time() - self.start_ts)
                h, rem = divmod(sec, 3600)
                m, sc = divmod(rem, 60)
                extra.append((f"{h}:{m:02d}:{sc:02d}" if h else f"{m:02d}:{sc:02d}") + " eltelt")
            else:
                extra.append("00:00 eltelt")
        self.pv_extra.configure(text="   ".join(extra))

        for w in (self.pv_b1, self.pv_b2):
            w.pack_forget()
        for n, w in (("1", self.pv_b1), ("2", self.pv_b2)):
            label = g(f"btn{n}_label")
            if label:
                w.configure(text=label)
                w.pack(fill="x", pady=3)

        path, img = self.preview_image()
        key = path if img else None
        if key != self._pv_key:
            self._pv_key = key
            if img:
                self.pv_ph.pack_forget()
                self.pv_img.configure(image=img)
                self.pv_img.pack()
            else:
                self.pv_img.pack_forget()
                self.pv_ph.pack()

    def _tick(self):
        try:
            if self.rpc and self.timer_on():
                self.update_preview()
        except Exception:
            pass
        self.after(1000, self._tick)

    def set_status(self, text, state=None):
        self.status_dot.configure(text_color={None: MUTED, True: GREEN, False: RED}[state])
        self.status_text.configure(text=text)

    # =====================================================
    #  ABLAK / TÁLCA
    # =====================================================
    def hide_window(self):
        self.withdraw()
        if not self.notified:
            self.notified = True
            try:
                self.tray.notify("A program a háttérben fut. A tálca ikonjára kattintva nyithatod meg.", "Discord RPC")
            except Exception:
                pass

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self.save_config()
        self.stop()
        try:
            self.tray.stop()
        except Exception:
            pass
        self.destroy()

    def set_tray_active(self, active):
        try:
            self.tray.icon = make_tray_image(active)
            self.tray.title = "Discord RPC – fut" if active else "Discord RPC"
        except Exception:
            pass

    # =====================================================
    #  KONFIGURÁCIÓ ÉS PROFILOK
    # =====================================================
    def collect(self):
        d = {k: v.get() for k, v in self.vars.items()}
        d["timer_mode"] = "Eltelt idő" if self.timer_on() else "Nincs"
        return d

    def apply(self, d):
        for k, v in self.vars.items():
            v.set(d.get(k, ""))
        self.timer_mode.set("Eltelt idő" if str(d.get("timer_mode", "")).startswith("Eltelt") else "Nincs")

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        if data and "profiles" not in data:  # régi formátum átvétele
            data = {"profiles": {"Alap": data}, "current": "Alap", "draft": data}
        self.profiles = data.get("profiles", {})
        self.current = data.get("current", "")
        if self.current not in self.profiles:
            self.current = ""
        self.local_imgs = data.get("images", {})
        self.apply(data.get("draft", {}))
        self.refresh_profiles()

    def save_config(self):
        data = {"profiles": self.profiles, "current": self.current,
                "draft": self.collect(), "images": self.local_imgs}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def refresh_profiles(self):
        for w in self.profile_widgets:
            w.destroy()
        self.profile_widgets = []
        if not self.profiles:
            lbl = ctk.CTkLabel(self.profile_list, text="Még nincs mentett profil.\nÁllítsd be a státuszt, majd\nnyomd meg az Új profil gombot.",
                               font=self.f_s, text_color=MUTED, justify="left")
            lbl.pack(anchor="w", padx=10, pady=10)
            self.profile_widgets.append(lbl)
        for name in sorted(self.profiles):
            sel = name == self.current
            b = ctk.CTkButton(
                self.profile_list, text=name, anchor="w", height=38, corner_radius=10, font=self.f_b,
                fg_color=ACCENT if sel else "transparent", hover_color=ACCENT_H if sel else FIELD,
                text_color="white" if sel else FG, command=lambda n=name: self.switch_profile(n),
            )
            b.pack(fill="x", pady=2, padx=(0, 4))
            self.profile_widgets.append(b)
        if hasattr(self, "tray"):
            try:
                self.tray.update_menu()
            except Exception:
                pass

    def switch_profile(self, name):
        if name not in self.profiles:
            return
        self.current = name
        self.apply(self.profiles[name])
        self.update_preview()
        self.save_config()
        self.refresh_profiles()
        if self.rpc:
            self.update_presence()
            self.set_status(f"Profil betöltve és frissítve: {name}", True)
        else:
            self.set_status(f"Profil betöltve: {name}")

    def save_profile(self):
        if not self.current:
            return self.new_profile()
        self.profiles[self.current] = self.collect()
        self.save_config()
        self.set_status(f"Profil mentve: {self.current}", True if self.rpc else None)

    def new_profile(self):
        name = ctk.CTkInputDialog(text="Profil neve:", title="Új profil").get_input()
        name = (name or "").strip()
        if not name:
            return
        if name in self.profiles and not messagebox.askyesno("Felülírás", f"A(z) '{name}' profil már létezik. Felülírod?"):
            return
        self.profiles[name] = self.collect()
        self.current = name
        self.refresh_profiles()
        self.save_config()
        self.set_status(f"Profil elmentve: {name}", True if self.rpc else None)

    def delete_profile(self):
        if not self.current:
            return
        if not messagebox.askyesno("Törlés", f"Biztosan törlöd a(z) '{self.current}' profilt?"):
            return
        del self.profiles[self.current]
        self.current = ""
        self.refresh_profiles()
        self.save_config()
        self.set_status("Profil törölve.")

    def tray_profile_items(self):
        def make(n):
            return lambda *_: self.after(0, lambda: self.switch_profile(n))
        items = [
            pystray.MenuItem(n, make(n), checked=lambda item, n=n: n == self.current, radio=True)
            for n in sorted(self.profiles)
        ]
        return tuple(items) or (pystray.MenuItem("(nincs mentett profil)", None, enabled=False),)

    # =====================================================
    #  KÉP FELTÖLTÉS
    # =====================================================
    def pick_image(self, key):
        path = filedialog.askopenfilename(
            title="Válassz képet",
            filetypes=[("Képek", "*.png *.jpg *.jpeg *.gif *.webp"), ("Minden fájl", "*.*")],
        )
        if not path:
            return
        if os.path.getsize(path) > 8 * 1024 * 1024:
            messagebox.showerror("Hiba", "A kép túl nagy (max. 8 MB). Válassz kisebbet.")
            return
        if not messagebox.askyesno(
            "Feltöltés",
            "A kép feltöltődik a catbox.moe ingyenes képtárhelyre, és a linkje nyilvános lesz "
            "(aki ismeri a linket, látja). Folytatod?",
        ):
            return
        self.set_status("Kép feltöltése...")
        threading.Thread(target=self._upload, args=(key, path), daemon=True).start()

    def _upload(self, key, path):
        import uuid
        import urllib.request
        try:
            boundary = uuid.uuid4().hex
            name = os.path.basename(path)
            with open(path, "rb") as f:
                content = f.read()
            parts = [
                f'--{boundary}\r\nContent-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n'.encode(),
                (f'--{boundary}\r\nContent-Disposition: form-data; name="fileToUpload"; filename="{name}"\r\n'
                 f'Content-Type: application/octet-stream\r\n\r\n').encode() + content + b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
            req = urllib.request.Request(
                "https://catbox.moe/user/api.php",
                data=b"".join(parts),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "Mozilla/5.0 DiscordRPCEditor",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                url = resp.read().decode().strip()
            if not url.startswith("http"):
                raise RuntimeError(url or "Ismeretlen válasz a szervertől")
            self.after(0, lambda u=url: self._upload_done(key, u, path))
        except Exception as e:
            err = str(e) or repr(e)
            self.after(0, lambda m=err: (
                self.set_status("Feltöltés sikertelen.", False),
                messagebox.showerror("Feltöltési hiba", m),
            ))

    def _upload_done(self, key, url, path):
        self.local_imgs[url] = path
        self.vars[key].set(url)
        self.save_config()
        self.set_status("Kép feltöltve, a link beírva. Nyomd meg az Indítás / Frissítés gombot.", True)

    # =====================================================
    #  RPC
    # =====================================================
    def build_payload(self):
        g = lambda k: self.vars[k].get().strip()
        p = {}
        for k in ("details", "state", "large_image", "large_text", "small_image", "small_text"):
            if g(k):
                p[k] = g(k)
        for k in ("details", "state", "large_text", "small_text"):
            if k in p and len(p[k]) < 2:
                p[k] += " "

        buttons = []
        for n in ("1", "2"):
            label, url = g(f"btn{n}_label"), g(f"btn{n}_url")
            if label and url:
                if not url.startswith(("http://", "https://")):
                    raise ValueError(f"A(z) {n}. gomb linkje http:// vagy https:// kezdetű legyen.")
                buttons.append({"label": label[:32], "url": url})
        if buttons:
            p["buttons"] = buttons

        if g("party_cur") and g("party_max"):
            try:
                p["party_size"] = [int(g("party_cur")), int(g("party_max"))]
            except ValueError:
                raise ValueError("A csapat létszámnak számnak kell lennie.")

        if self.timer_on() and self.start_ts:
            p["start"] = self.start_ts

        if not p:
            raise ValueError("Tölts ki legalább egy mezőt (pl. a felső sort).")
        return p

    def start(self):
        cid = self.vars["client_id"].get().strip()
        if not cid.isdigit():
            messagebox.showerror("Hiba", "Adj meg érvényes Client ID-t (csak számok).")
            return
        self.start_btn.configure(state="disabled")
        self.set_status("Csatlakozás...")
        self.save_config()
        self.start_ts = int(time.time())
        threading.Thread(target=self._connect, args=(cid,), daemon=True).start()

    def _connect(self, cid):
        try:
            self.rpc = Presence(cid)
            self.rpc.connect()
            self.rpc.update(**self.build_payload())
            self.after(0, self._on_connected)
        except Exception as e:
            self.rpc = None
            err = str(e) or repr(e)
            self.after(0, lambda m=err: self._on_error(m))

    def _on_connected(self):
        self.set_status("Fut, látszik a profilodon.", True)
        self.update_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.set_tray_active(True)

    def _on_error(self, e):
        self.set_status("Hiba történt.", False)
        self.start_btn.configure(state="normal")
        messagebox.showerror("Hiba", f"{e}\n\nEllenőrizd, hogy a Discord asztali app fut, és a Client ID helyes.")

    def update_presence(self):
        if not self.rpc:
            return
        try:
            self.save_config()
            self.rpc.update(**self.build_payload())
            self.set_status("Frissítve.", True)
        except Exception as e:
            messagebox.showerror("Hiba", str(e))

    def stop(self):
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
            self.rpc = None
        self.set_status("Leállítva.")
        self.start_btn.configure(state="normal")
        self.update_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.set_tray_active(False)
        self.update_preview()


def relaunch_detached():
    """Windowson újraindítja magát konzol nélkül, így a terminál bezárása nem állítja le."""
    if os.name != "nt" or "--bg" in sys.argv:
        return False
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        return False
    import subprocess
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED | NEW_GROUP | NO_WINDOW
    subprocess.Popen([pyw, os.path.abspath(__file__), "--bg"], creationflags=flags, close_fds=True)
    print("A program elindult a háttérben (nézd a tálca rejtett ikonjait). A terminált bezárhatod.")
    return True


if __name__ == "__main__":
    if relaunch_detached():
        sys.exit(0)
    try:
        App().mainloop()
    except Exception:
        fatal("A program elindításakor hiba történt:\n\n" + traceback.format_exc())
