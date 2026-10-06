# -*- coding: utf-8 -*-
"""
FORMULIR DIGITAL MONITORING SUHU DAN KELEMBAPAN DEPARTEMEN RADIOLOGI PHPK 2026
Primaya Hospital  |  Form/PHG/GAD-11-1/Rev.03

Jalankan :  streamlit run app.py
Syarat   :  pip install streamlit pandas reportlab openpyxl      (streamlit >= 1.36)
"""
import base64
import calendar
import datetime as dt
import io
import json
import math
import os
import textwrap
import urllib.request
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Radiologi - Primaya Hospital",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = "data_primaya"
ENTRY_FILE = os.path.join(DATA_DIR, "entries.csv")
CFG_FILE = os.path.join(DATA_DIR, "config.json")
LOGO_FILE = "Primaya Logo.png"
FOOTER_FILE = "Primaya Footer.png"
FONT_REG = "Lexend-Regular.ttf"
FONT_BOLD = "Lexend-Bold.ttf"
os.makedirs(DATA_DIR, exist_ok=True)

FONT_URLS = {
    FONT_REG: [
        "https://github.com/google/fonts/raw/main/ofl/lexend/static/Lexend-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/static/Lexend-Regular.ttf",
    ],
    FONT_BOLD: [
        "https://github.com/google/fonts/raw/main/ofl/lexend/static/Lexend-Bold.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/static/Lexend-Bold.ttf",
    ],
}

BLN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
SHIFT_NAME = {"P": "Pagi", "S": "Siang", "M": "Malam"}
SHIFT_LABEL = {"P": "P - Pagi (08.00)", "S": "S - Sore (14.00)", "M": "M - Malam (21.00)"}
SHIFT_HOUR = {"P": 8, "S": 14, "M": 21}

STD_RADIOLOGI = dict(t_lo=20.0, t_hi=24.0, h_lo=40.0, h_hi=60.0)
DEFAULT_CFG = {
    "rooms": [dict(nama=n, tekanan=False, **STD_RADIOLOGI) for n in
              ["Philips Briliance CT", "USG", "R.Operator", "ESWL", "Panoramik", "Radiografi Umum"]],
    "staff": ["SL", "AG", "AY", "WT", "FF"],
}


# =====================================================================
# 0. AUTO-DOWNLOAD FONT LEXEND
# =====================================================================
def ensure_lexend_fonts():
    """Unduh file Lexend dari Google Fonts bila belum ada. Return (reg_ok, bold_ok)."""
    reg_ok = os.path.exists(FONT_REG)
    bold_ok = os.path.exists(FONT_BOLD)
    for path, urls in FONT_URLS.items():
        if os.path.exists(path):
            continue
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r, open(path, "wb") as f:
                    f.write(r.read())
                if path == FONT_REG:
                    reg_ok = True
                if path == FONT_BOLD:
                    bold_ok = True
                break
            except Exception:
                continue
    return reg_ok, bold_ok


# =====================================================================
# 1. PENYIMPANAN
# =====================================================================
ECOLS = ["id", "dibuat", "ruang", "tanggal", "shift", "suhu", "kelembapan", "tek", "tek_tanda", "petugas", "status", "temuan", "tindakan"]


def load_cfg():
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("rooms") and c.get("staff"):
                return c
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CFG))


def save_cfg(c):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)


def rooms():
    return load_cfg()["rooms"]


def room_names():
    return [r["nama"] for r in rooms()]


def room_std(name):
    for r in rooms():
        if r["nama"] == name:
            return r
    return dict(nama=name, tekanan=False, **STD_RADIOLOGI)


def load_entries():
    if os.path.exists(ENTRY_FILE):
        try:
            df = pd.read_csv(ENTRY_FILE, dtype=str).fillna("")
        except Exception:
            df = pd.DataFrame(columns=ECOLS)
    else:
        df = pd.DataFrame(columns=ECOLS)
    for c in ECOLS:
        if c not in df.columns:
            df[c] = ""
    return df[ECOLS]


def save_entry(overwrite=True, **kw):
    df = load_entries()
    if overwrite and len(df):
        m = (df["ruang"] == kw["ruang"]) & (df["tanggal"] == kw["tanggal"]) & (df["shift"] == kw["shift"])
        df = df[~m]
    row = {c: "" for c in ECOLS}
    for k, v in kw.items():
        row[k] = str(v)
    nid = 1 + max([int(x) for x in df["id"] if str(x).isdigit()] + [0])
    row["id"] = str(nid)
    row["dibuat"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(ENTRY_FILE, index=False)


def delete_entry(eid):
    df = load_entries()
    df[df["id"] != str(eid)].to_csv(ENTRY_FILE, index=False)


def TODAY():
    """Tanggal sistem aktual (sidebar date_input DIHAPUS)."""
    v = st.session_state.get("sim_today")
    return v if isinstance(v, dt.date) else dt.date.today()


def fnum(v):
    return ("%g" % v)


# =====================================================================
# 2. DATA BULANAN + ANALISA
# =====================================================================
def slot_due(d, s, today):
    if d < today:
        return True
    if d > today:
        return False
    if today == dt.date.today():
        return dt.datetime.now().hour >= SHIFT_HOUR[s]
    return True


def month_data(ruang, y, m, today):
    out = {}
    df = load_entries()
    df = df[df["ruang"] == ruang]
    for r in df.to_dict("records"):
        try:
            td = dt.date.fromisoformat(r["tanggal"])
            if td.year != y or td.month != m:
                continue
            tek = float(r["tek"]) if r["tek"] != "" else None
            ket = r["temuan"] + (" (" + r["tindakan"] + ")" if r["tindakan"] and r["temuan"] else "")
            out[(td.day, r["shift"][:1])] = dict(suhu=float(r["suhu"]), hum=float(r["kelembapan"]), tek=tek, tek_tanda=r["tek_tanda"],
                                                petugas=r["petugas"], ket=ket, real=True, id=r["id"])
        except Exception:
            continue
    return out


def classify(v, lo, hi):
    return "ok" if lo <= v <= hi else ("high" if v > hi else "low")


def analyze(ruang, y, m, today):
    std = room_std(ruang)
    data = month_data(ruang, y, m, today)
    n = calendar.monthrange(y, m)[1]
    slots, empty_by_day = {}, {}
    high, low, hum_bad = [], [], []
    due = filled = ok = 0
    for d in range(1, n + 1):
        dd = dt.date(y, m, d)
        for s in "PSM":
            is_due = slot_due(dd, s, today)
            e = data.get((d, s))
            if e is None:
                slots[(d, s)] = dict(state="empty" if is_due else "future")
                if is_due:
                    due += 1
                    empty_by_day.setdefault(d, []).append(s)
                continue
            st_ = classify(e["suhu"], std["t_lo"], std["t_hi"])
            hs = classify(e["hum"], std["h_lo"], std["h_hi"])
            slots[(d, s)] = dict(state=st_, t=e["suhu"], h=e["hum"], hstate=hs, petugas=e["petugas"])
            if is_due:
                due += 1
                filled += 1
                ok += 1 if st_ == "ok" else 0
            if st_ == "high":
                high.append((d, s, e["suhu"]))
            elif st_ == "low":
                low.append((d, s, e["suhu"]))
            if hs != "ok":
                hum_bad.append((d, s, e["hum"], hs))
    full_empty = [d for d, v in empty_by_day.items() if len(v) == 3]
    return dict(std=std, n=n, slots=slots, empty_by_day=empty_by_day, high=high, low=low, hum_bad=hum_bad, due=due, filled=filled, ok=ok,
                pct_fill=(filled / due * 100 if due else 0.0), pct_ok=(ok / filled * 100 if filled else 0.0),
                pct_ach=(ok / due * 100 if due else 0.0), full_empty=sorted(full_empty), n_empty=due - filled)


# =====================================================================
# 3. GAMBAR FORMULIR
# =====================================================================
U2PT = 842.0 / 2573.0
OFF = 150.0
BAND, GRAY, TEAL, NAVY, RED, BLACK = "#cfe2f3", "#efefef", "#1b7895", "#004e75", "#ff0000", "#000000"

FONT_FAMILY_SVG = "Lexend, Helvetica, Arial, sans-serif"


class Sheet:
    def __init__(self):
        self.ops = []

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1.0):
        self.ops.append(("rect", x, y, w, h, fill, stroke, lw))

    def line(self, x1, y1, x2, y2, color=BLACK, lw=1.0):
        self.ops.append(("line", x1, y1, x2, y2, color, lw))

    def text(self, x, y, s, size=11, bold=False, color=BLACK, anchor="start", spacing=0.0):
        self.ops.append(("text", x, y, s, size, bold, color, anchor, spacing))

    def circle(self, cx, cy, r, fill=None, stroke=None, lw=1.0):
        self.ops.append(("circle", cx, cy, r, fill, stroke, lw))

    def ctext(self, x, y, w, h, s, size=11, bold=False, color=BLACK):
        lines = str(s).split("\n")
        lh = size * 1.18
        base = y + (h - lh * len(lines)) / 2 + size * 0.82
        for i, ln in enumerate(lines):
            self.text(x + w / 2, base + i * lh, ln, size, bold, color, "middle")

    def image(self, x, y, w, h, data_b64):
        self.ops.append(("image", x, y, w, h, data_b64))


X0, LABW, DAYW, KETW, RH = 5.0, 73.0, 65.0, 173.0, 14.25
SUB = DAYW / 3
XD = X0 + LABW
XK = XD + 31 * DAYW
XE = XK + KETW
LW = 0.75

REF_HEAD = ["Operasi", "Tindakan", "Rawat inap/rawat\njalan/isolasi/Bayi\nNormal", "Teknik/Ruang\nPanel/Ruang Mesin\nRO", "Teknik/Ruang\nPanel/Ruang Mesin\nRO",
            "ICU/PICU/HCU/NIC\nU/IGD", "Laboratorium/Radiol\nogi/Kamar\nJenazah/Farmasi", "Mesin Lift", "Dapur", "IGD", "Luka Bakar",
            "CSSD -\nPembersihan/Penge\nmasan", "CSSD -\nPenyimpanan Steril", "Gudang Linen\nBersih/Rekam Medis", "Server/MCFA/Kontr\nol/UPS",
            "Genset/Trafo", "Angiografi/Radioter\napi/Kedokteran\nNuklir"]
REF_SUHU = ["20-26", "20-24", "22-24", "22-24", "22-26", "22-26", "20-24", "20-24", "22-30", "22-26", "24-26", "22-26", "20-24", "22-26", "20-24", "35-40", "20-24"]
REF_HUM = ["40-60"] * 12 + ["40-50"] + ["40-60"] * 4
REF_SRC = [(XD, 620, "Peraturan Menteri Kesehatan Republik Indonesia No. 02 Tahun 2023\ntentang Kesehatan Lingkungan"),
           (620, 1162, "Peraturan Menteri Kesehatan Republik Indonesia No. 40 Tahun 2022 Tentang Persyaratan\nTeknis Bangunan, Prasarana, dan Peralatan Kesehatan Rumah Sakit"),
           (1162, 1684, "Peraturan Menteri Kesehatan Republik Indonesia No. 72 Tahun 2016 Tentang Standar\nPelayanan Kefarmasian di Rumah Sakit"),
           (1684, XD + 29 * DAYW, "CDC: Guidelines for Environmental Infection\nControl in Healthcare Facilities 2003")]
CATATAN = ["- P (Pagi) Pkl 08.00 Waktu Setempat, S (Sore) Pkl 14.00 Waktu Setempat, M (Malam) Pkl 21.00 Waktu Setempat",
           "- Tek = Tekanan (diisi jika ruangan mempunyai tekanan) positif dan negatif, dengan perbedaan tekanan udara luar minimal lebih rendah 2,5 pascal dibanding tekanan udara di sebelahnya",
           "- Jika suhu, kelembaban dan tekanan tidak sesuai dengan batasan normal, segera hubungi petugas maintenance"]


def _logo_b64():
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def _footer_b64():
    if os.path.exists(FOOTER_FILE):
        with open(FOOTER_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def build_form(ruang, y, m, data):
    std = room_std(ruang)
    lo, hi, hl, hh = std["t_lo"], std["t_hi"], std["h_lo"], std["h_hi"]
    ymin, ymax = min(16, int(math.floor(lo)) - 4), max(32, int(math.ceil(hi)) + 8)
    nrow = ymax - ymin + 1
    sh = Sheet()

    # ---- HEADER PDF: logo Primaya kiri atas + judul kanan atas ----
    logo = _logo_b64()
    if logo:
        sh.image(8, 18, 120, 50, logo)
    else:
        sh.text(8, 50, "PRIMAYA", 40, True, "#095475")
        sh.text(14, 68, "HOSPITAL", 11.5, True, "#095475", "start", 9.5)

    sh.text(XE, 33, "FORMULIR DIGITAL SUHU, KELEMBAPAN,", 27, True, TEAL, "end")
    sh.text(XE, 66, "DAN TEKANAN RUANGAN", 27, True, TEAL, "end")

    # Info bulan/tahun & ruang
    sh.text(X0, 88, "Bulan, Tahun : {} {}".format(BLN[m - 1].upper(), y), 10.5)
    sh.text(426, 88, "Ruang : " + ruang, 10.5)

    # ---- header tabel ----
    Y1, Y2, YT = 103.0, 118.0, 133.0
    sh.rect(X0, Y1, LABW, 15, None, BLACK, LW)
    sh.ctext(X0, Y1, LABW, 15, "Tanggal", 10.5)
    sh.rect(X0, Y2, LABW, 15, None, BLACK, LW)
    sh.ctext(X0, Y2, LABW, 15, "°C", 10.5, True)
    for d in range(1, 32):
        x = XD + (d - 1) * DAYW
        sh.rect(x, Y1, DAYW, 15, None, BLACK, LW)
        sh.ctext(x, Y1, DAYW, 15, str(d), 10.5)
        for k, c in enumerate("PSM"):
            sh.rect(x + k * SUB, Y2, SUB, 15, None, BLACK, LW)
            sh.ctext(x + k * SUB, Y2, SUB, 15, c, 10)
    sh.rect(XK, Y1, KETW, 30, GRAY, BLACK, LW)
    sh.ctext(XK, Y1, KETW, 30, "Keterangan", 11)

    # ---- baris suhu ----
    for r in range(nrow):
        v = ymax - r
        yy = YT + r * RH
        sh.rect(X0, yy, XE - X0, RH, BAND if v % 2 == 0 else None, BLACK, LW)
        sh.ctext(X0, yy, LABW, RH, str(v), 10.5, True, BLACK if lo <= v <= hi else RED)
    y_hum = YT + nrow * RH
    y_tp, y_tm = y_hum + 15, y_hum + 41
    y_n0 = y_tm + 14
    nh = [28.0, 27.0, 27.0]
    y_end = y_n0 + sum(nh)
    for (yy, hh_, lab) in [(y_hum, 15, "Kelembapan"), (y_tp, 26, "Tek +"), (y_tm, 14, "Tek -")]:
        sh.rect(X0, yy, XE - X0, hh_, None, BLACK, LW)
        sh.ctext(X0, yy, LABW, hh_, lab, 10)

    for i in range(1, 93):
        sh.line(XD + i * SUB, YT, XD + i * SUB, y_n0, BLACK, LW)
    for x in (XD, XK):
        sh.line(x, Y1, x, y_end, BLACK, LW)

    # ---- titik suhu, kelembapan, tekanan ----
    for (d, s), e in data.items():
        k = "PSM".index(s)
        cx = XD + (d - 1) * DAYW + (k + .5) * SUB
        row = int(math.floor(e["suhu"] + 0.5))
        if ymin <= row <= ymax:
            cy = YT + (ymax - row) * RH + RH / 2
            sh.circle(cx, cy, 2.7, BLACK if lo <= e["suhu"] <= hi else RED)
        sh.ctext(cx - SUB / 2, y_hum, SUB, 15, str(int(round(e["hum"]))), 9.5, not (hl <= e["hum"] <= hh))
        if e.get("tek") is not None:
            yy, hh_ = (y_tp, 26) if e.get("tek_tanda") != "-" else (y_tm, 14)
            sh.ctext(cx - SUB / 2, yy, SUB, hh_, fnum(e["tek"]), 8.5)

    # ---- nama petugas ----
    yy = y_n0
    for (lab, s), hh_ in zip([("Nama\n(Pagi)", "P"), ("Nama\n(Siang)", "S"), ("Nama\n(Malam)", "M")], nh):
        sh.rect(X0, yy, LABW, hh_, BAND, BLACK, LW)
        sh.ctext(X0, yy, LABW, hh_, lab, 9.5)
        for d in range(1, 32):
            x = XD + (d - 1) * DAYW
            sh.rect(x, yy, DAYW, hh_, BAND, BLACK, LW)
            e = data.get((d, s))
            if e:
                sh.ctext(x, yy, DAYW, hh_, e["petugas"], 11)
        yy += hh_
    sh.rect(XK, y_n0, KETW, y_end - y_n0, BAND, BLACK, LW)

    # ---- keterangan ----
    notes = []
    for (d, s), e in sorted(data.items()):
        if e.get("ket"):
            notes.extend(textwrap.wrap("{}/{}: {}".format(d, s, e["ket"]), 33))
    maxl = nrow
    if len(notes) > maxl:
        notes = notes[:maxl - 1] + ["... (selengkapnya di data)"]
    for i, ln in enumerate(notes):
        sh.text(XK + 4, YT + i * RH + RH / 2 + 3, ln, 8.5)

    # ---- blok mengetahui ----
    xm = XD + 29 * DAYW
    sh.rect(xm, y_end, XE - xm, 158, None, "#bdbdbd", 0.8)
    sh.text((xm + XE) / 2, y_end + 38, "Mengetahui", 10.5, True, BLACK, "middle")
    sh.text((xm + XE) / 2, y_end + 52, "Koordinator Unit", 10.5, True, BLACK, "middle")
    sh.text((xm + XE) / 2, y_end + 151, "(" + "." * 62 + ")", 10, True, BLACK, "middle")
    sh.rect(xm, y_end + 158, XE - xm, 36, None, "#bdbdbd", 0.8)
    sh.ctext(xm, y_end + 158, XE - xm, 36, "Form/PHG/GAD-11-1/Rev.03", 11, False, "#0a4d7a")

    # ---- catatan ----
    sh.text(X0, y_end + 24, "Catatan:", 10.5)
    for i, ln in enumerate(CATATAN):
        sh.text(X0, y_end + 38 + i * 13.5, ln, 10.5)

    # ---- tabel acuan ----
    y_r = y_end + 82
    cw = (xm - 122.0) / 17.0
    sh.rect(X0, y_r, 117, 46, BAND, BLACK, LW)
    sh.ctext(X0, y_r, 117, 46, "Ruangan/Unit", 10.5)
    for i, t in enumerate(REF_HEAD):
        x = 122 + i * cw
        sh.rect(x, y_r, cw, 46, BAND, BLACK, LW)
        sh.ctext(x, y_r, cw, 46, t, 9.2)
        for (yy, hh_, val) in [(y_r + 46, 15, REF_SUHU[i]), (y_r + 61, 15, REF_HUM[i])]:
            sh.rect(x, yy, cw, hh_, None, BLACK, LW)
            sh.ctext(x, yy, cw, hh_, val, 9.5)
    for (yy, lab) in [(y_r + 46, "Suhu (°C)"), (y_r + 61, "Kelembaban (%)")]:
        sh.rect(X0, yy, 117, 15, None, BLACK, LW)
        sh.ctext(X0, yy, 117, 15, lab, 9.5)
    sh.rect(X0, y_r + 76, LABW, 36, None, "#9e9e9e", 0.8)
    sh.ctext(X0, y_r + 76, LABW, 36, "Sumber", 9.5)
    for (a, b, t) in REF_SRC:
        sh.rect(a, y_r + 76, b - a, 36, None, "#9e9e9e", 0.8)
        sh.ctext(a, y_r + 76, b - a, 36, t, 9.5)

    # ==================================================================
    # >>> REVISI 1: FOOTER DIPERBESAR (dari 49 -> 90) TAPI TIDAK MELEBIHI BORDER
    # Gambar di-scale memenuhi tinggi footer tanpa melewati batas atas/bawah.
    # ==================================================================
    yf = y_r + 112          # posisi atas footer
    footer_h = 90.0         # >>> tinggi baru (dari 49px -> 90px)
    sh.rect(X0, yf, XE - X0, footer_h, NAVY, None, 0)

    footer = _footer_b64()
    if footer:
        # Gambar footer dibuat lebih besar, menempel full-width, tapi tingginya dibatasi footer_h
        sh.image(X0, yf, XE - X0, footer_h, footer)
    else:
        sh.circle(40, yf + footer_h / 2, 10, None, "#ffffff", 1.8)
        sh.line(30, yf + footer_h / 2, 50, yf + footer_h / 2, "#ffffff", 1.4)
        sh.text(60, yf + footer_h / 2 + 5, "www.primayahospital.com", 15, False, "#ffffff")

    sh.height = yf + footer_h
    return sh


def sheet_to_svg(sh, width_px=1400):
    W, H = XE + 8, sh.height + 8
    p = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='-3 -3 {} {}' width='{}' height='{}' font-family=\"{}\">".format(
        W, H, width_px, int(width_px * H / W), FONT_FAMILY_SVG),
        "<rect x='-3' y='-3' width='{}' height='{}' fill='#ffffff'/>".format(W, H)]
    for op in sh.ops:
        k = op[0]
        if k == "rect":
            _, x, y, w, h, fill, stroke, lw = op
            p.append("<rect x='{:.2f}' y='{:.2f}' width='{:.2f}' height='{:.2f}' fill='{}' stroke='{}' stroke-width='{}'/>".format(
                x, y, w, h, fill or "none", stroke or "none", lw))
        elif k == "line":
            _, x1, y1, x2, y2, c, lw = op
            p.append("<line x1='{:.2f}' y1='{:.2f}' x2='{:.2f}' y2='{:.2f}' stroke='{}' stroke-width='{}'/>".format(x1, y1, x2, y2, c, lw))
        elif k == "circle":
            _, cx, cy, r, fill, stroke, lw = op
            p.append("<circle cx='{:.2f}' cy='{:.2f}' r='{}' fill='{}' stroke='{}' stroke-width='{}'/>".format(cx, cy, r, fill or "none", stroke or "none", lw))
        elif k == "image":
            _, x, y, w, h, data_b64 = op
            # preserveAspectRatio="none" -> stretch agar mengisi persis kotak
            p.append("<image x='{:.2f}' y='{:.2f}' width='{:.2f}' height='{:.2f}' preserveAspectRatio='none' href='data:image/png;base64,{}'/>".format(x, y, w, h, data_b64))
        else:
            _, x, y, s, size, bold, color, anchor, spacing = op
            p.append("<text x='{:.2f}' y='{:.2f}' font-size='{}' font-weight='{}' fill='{}' text-anchor='{}'{}>{}</text>".format(
                x, y, size, "bold" if bold else "normal", color, anchor, " letter-spacing='{}'".format(spacing) if spacing else "", escape(s)))
    return "".join(p) + "</svg>"


# =====================================================================
# >>> REVISI 2: Perbaikan registrasi font Lexend
# =====================================================================
LEXEND_FONT_REG_NAME = "Lexend"            # nama internal untuk ReportLab
LEXEND_FONT_BOLD_NAME = "Lexend-Bold"

LEXEND_STATUS = {"reg": False, "bold": False, "tried": False, "err": ""}


def _register_lexend(force=False):
    """Daftarkan font Lexend ke ReportLab. Kembalikan (reg_ok, bold_ok)."""
    if LEXEND_STATUS["tried"] and not force:
        return LEXEND_STATUS["reg"], LEXEND_STATUS["bold"]

    ensure_lexend_fonts()

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    reg_ok = bold_ok = False
    err_msgs = []

    # Register Regular
    if os.path.exists(FONT_REG):
        try:
            pdfmetrics.registerFont(TTFont(LEXEND_FONT_REG_NAME, FONT_REG))
            # Verifikasi font terdaftar dengan benar
            _ = pdfmetrics.getFont(LEXEND_FONT_REG_NAME)
            reg_ok = True
        except Exception as e:
            err_msgs.append("Regular: " + str(e))
    else:
        err_msgs.append("File Lexend-Regular.ttf tidak ditemukan.")

    # Register Bold
    if os.path.exists(FONT_BOLD):
        try:
            pdfmetrics.registerFont(TTFont(LEXEND_FONT_BOLD_NAME, FONT_BOLD))
            _ = pdfmetrics.getFont(LEXEND_FONT_BOLD_NAME)
            bold_ok = True
        except Exception as e:
            err_msgs.append("Bold: " + str(e))
    else:
        err_msgs.append("File Lexend-Bold.ttf tidak ditemukan.")

    LEXEND_STATUS.update(reg=reg_ok, bold=bold_ok, tried=True, err=" | ".join(err_msgs))
    return reg_ok, bold_ok


def lexend_available():
    """Cek apakah kedua font Lexend bisa didaftarkan."""
    r, b = _register_lexend()
    return r and b


def lexend_debug_info():
    """Kembalikan string info untuk ditampilkan di UI."""
    _register_lexend()
    return (
        f"File Regular : {'ADA' if os.path.exists(FONT_REG) else 'TIDAK ADA'} ({FONT_REG})\n"
        f"File Bold    : {'ADA' if os.path.exists(FONT_BOLD) else 'TIDAK ADA'} ({FONT_BOLD})\n"
        f"Register Reg : {'OK' if LEXEND_STATUS['reg'] else 'GAGAL'}\n"
        f"Register Bold: {'OK' if LEXEND_STATUS['bold'] else 'GAGAL'}\n"
        f"Error        : {LEXEND_STATUS['err'] or '(tidak ada)'}"
    )


def sheets_to_pdf(sheets, title="Formulir Suhu dan Kelembapan"):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader

    reg_ok, bold_ok = _register_lexend()
    # >>> REVISI 2: Pakai Lexend untuk SEMUA teks PDF
    fn_reg = LEXEND_FONT_REG_NAME if reg_ok else "Helvetica"
    fn_bold = LEXEND_FONT_BOLD_NAME if bold_ok else ("Helvetica-Bold")

    buf = io.BytesIO()
    pw, ph = landscape(A4)
    c = Canvas(buf, pagesize=(pw, ph))
    c.setTitle(title)
    c.setAuthor("Primaya Hospital - Departemen Radiologi")
    tx = lambda x: (x + OFF) * U2PT
    ty = lambda y: ph - (y + OFF) * U2PT

    for sh in sheets:
        for op in sh.ops:
            k = op[0]
            if k == "rect":
                _, x, y, w, h, fill, stroke, lw = op
                if not fill and not stroke:
                    continue
                if fill:
                    c.setFillColor(HexColor(fill))
                if stroke:
                    c.setStrokeColor(HexColor(stroke))
                    c.setLineWidth(max(lw * U2PT, 0.1))
                c.rect(tx(x), ty(y + h), w * U2PT, h * U2PT, stroke=1 if stroke else 0, fill=1 if fill else 0)
            elif k == "line":
                _, x1, y1, x2, y2, col, lw = op
                c.setStrokeColor(HexColor(col))
                c.setLineWidth(max(lw * U2PT, 0.1))
                c.line(tx(x1), ty(y1), tx(x2), ty(y2))
            elif k == "circle":
                _, cx, cy, r, fill, stroke, lw = op
                if fill:
                    c.setFillColor(HexColor(fill))
                if stroke:
                    c.setStrokeColor(HexColor(stroke))
                    c.setLineWidth(max(lw * U2PT, 0.1))
                c.circle(tx(cx), ty(cy), r * U2PT, stroke=1 if stroke else 0, fill=1 if fill else 0)
            elif k == "image":
                _, x, y, w, h, data_b64 = op
                try:
                    img = ImageReader(io.BytesIO(base64.b64decode(data_b64)))
                    # preserveAspectRatio=False -> stretch mengisi kotak persis
                    c.drawImage(img, tx(x), ty(y + h), w * U2PT, h * U2PT, mask="auto", preserveAspectRatio=False)
                except Exception:
                    pass
            else:
                _, x, y, s, size, bold, color, anchor, spacing = op
                fn = fn_bold if bold else fn_reg
                fs = size * U2PT
                c.setFillColor(HexColor(color))
                c.setFont(fn, fs)
                if spacing:
                    sp = spacing * U2PT
                    xx = tx(x)
                    for chh in s:
                        c.drawString(xx, ty(y), chh)
                        xx += stringWidth(chh, fn, fs) + sp
                elif anchor == "middle":
                    c.drawCentredString(tx(x), ty(y), s)
                elif anchor == "end":
                    c.drawRightString(tx(x), ty(y), s)
                else:
                    c.drawString(tx(x), ty(y), s)
        c.showPage()
    c.save()
    return buf.getvalue()


# =====================================================================
# 4. STYLE & KOMPONEN  (mode light saja)
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');

:root, html, body { color-scheme: light !important; }
html, body, [class*="css"], .stApp, .stMarkdown, .stButton, .stTextInput,
.stSelectbox, .stDateInput, .stNumberInput, .stRadio, .stCheckbox, .stDataFrame,
[data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stAppViewContainer"] {
    font-family: 'Lexend', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    color-scheme: light !important;
}
.stApp{background:#f4f7fa !important;color:#111 !important}
[data-testid=stSidebar]{background:#ffffff !important;color:#111 !important}
[data-testid="stHeader"]{background:transparent !important}
.block-container{padding-top:1.2rem;max-width:100%}
button[kind="primary"]{background:#005580;border-color:#005580}

/* Header hero - TANPA logo, full center */
.ph-hero{
  background:linear-gradient(135deg,#003358,#005580);
  color:#fff;padding:26px 30px;border-radius:12px;margin-bottom:18px;
  text-align:center;
  box-shadow:0 3px 10px rgba(0,0,0,.08);
}
.ph-hero h1{
  font-size:22px;margin:0 0 6px;font-weight:800;letter-spacing:.4px;
}
.ph-hero h2{
  font-size:14px;margin:0;font-weight:500;opacity:.95;letter-spacing:.3px;
}
.ph-hero .divider{
  display:inline-block;width:70px;height:3px;background:#ffd166;
  margin:10px auto 10px;border-radius:2px;
}

.kp{display:flex;gap:12px;margin:6px 0 14px}.kc{flex:1;background:#fff;border-radius:8px;padding:12px 16px;box-shadow:0 1px 3px #0001;border-top:4px solid #005580}
.kc .t{font-size:12px;color:#667}.kc .v{font-size:28px;font-weight:700;margin:2px 0;color:#111}.kc .s{font-size:11px;color:#778}
.cal{border-collapse:collapse;font-size:11px}.cal td,.cal th{border:1px solid #fff;text-align:center;min-width:26px;height:24px;padding:0 2px}
.cal th{background:#cfe2f3;color:#124}.cal td.l{text-align:left;font-weight:700;background:#eef4fb;padding:0 8px;min-width:80px}
.s-ok{background:#2e9e5b;color:#fff}.s-high{background:#d64545;color:#fff;font-weight:700}.s-low{background:#f0a81c;color:#2b2000;font-weight:700}
.s-empty{background:#9aa5b1;color:#fff}.s-future{background:#eef1f5;color:#bbb}
.lg2{display:flex;gap:16px;font-size:12px;margin:8px 0}.lg2 i{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:6px;vertical-align:-3px}
.box{background:#fff;border-radius:8px;padding:12px 16px;box-shadow:0 1px 3px #0001;margin-bottom:10px;font-size:13px;line-height:1.7}
.hint{font-size:12px;margin:-8px 0 8px 2px}.hint.ok{color:#2e9e5b}.hint.bad{color:#d64545}
.warn{background:#fff4e5;border-left:4px solid #f0a81c;padding:10px 14px;border-radius:6px;font-size:12.5px;margin:8px 0}
.ok-info{background:#e8f5ec;border-left:4px solid #2e9e5b;padding:10px 14px;border-radius:6px;font-size:12.5px;margin:8px 0}
</style>
""", unsafe_allow_html=True)


def header(subtitle=""):
    """Header hero: center, TANPA logo (logo sudah dipindah ke sidebar)."""
    title = "FORMULIR DIGITAL MONITORING SUHU DAN KELEMBAPAN"
    subtitle = "DEPARTEMEN RADIOLOGI PHPK 2026"
    st.markdown(
        "<div class='ph-hero'>"
        "<h1>{title}</h1>"
        "<div class='divider'></div>"
        "<h2>{subtitle}</h2>"
        "</div>".format(title=title, subtitle=subtitle),
        unsafe_allow_html=True)


def filter_bar(prefix):
    t = TODAY()
    c1, c2, c3 = st.columns([2.2, 1.6, 1])
    ruang = c1.selectbox("Ruangan", room_names(), key=prefix + "_ruang")
    bln = c2.selectbox("Bulan", list(range(1, 13)), format_func=lambda x: BLN[x - 1], index=t.month - 1, key=prefix + "_bln")
    yrs = list(range(t.year - 2, t.year + 2))
    thn = c3.selectbox("Tahun", yrs, index=yrs.index(t.year), key=prefix + "_thn")
    return ruang, int(bln), int(thn)


def days_text(days):
    return ", ".join(str(d) for d in days) if days else "-"


# =====================================================================
# 5. HALAMAN
# =====================================================================
def page_dashboard():
    header()
    st.caption("Dashboard rangkuman pencapaian suhu & kelembapan")
    ruang, m, y = filter_bar("db")
    an = analyze(ruang, y, m, TODAY())
    std = an["std"]
    if an["due"] == 0:
        st.info("Belum ada slot pengukuran yang jatuh tempo pada bulan ini.")
    st.markdown("""
    <div class='kp'>
      <div class='kc'><div class='t'>Persentase pengisian</div><div class='v'>{pf:.0f}%</div><div class='s'>{f} dari {d} slot terisi (P/S/M)</div></div>
      <div class='kc' style='border-top-color:#2e9e5b'><div class='t'>Suhu dalam batas ({lo:g}&ndash;{hi:g} &deg;C)</div><div class='v' style='color:#2e9e5b'>{po:.0f}%</div><div class='s'>{o} dari {f} data terisi</div></div>
      <div class='kc' style='border-top-color:#d64545'><div class='t'>Suhu DI ATAS batas</div><div class='v' style='color:#d64545'>{hi_n}</div><div class='s'>slot pengukuran</div></div>
      <div class='kc' style='border-top-color:#f0a81c'><div class='t'>Suhu di bawah batas</div><div class='v' style='color:#d98e00'>{lo_n}</div><div class='s'>slot pengukuran</div></div>
      <div class='kc' style='border-top-color:#9aa5b1'><div class='t'>Slot kosong / belum diisi</div><div class='v' style='color:#667'>{e}</div><div class='s'>{fe} tanggal kosong total</div></div>
    </div>""".format(pf=an["pct_fill"], f=an["filled"], d=an["due"], lo=std["t_lo"], hi=std["t_hi"], po=an["pct_ok"], o=an["ok"],
                     hi_n=len(an["high"]), lo_n=len(an["low"]), e=an["n_empty"], fe=len(an["full_empty"])), unsafe_allow_html=True)

    head = "<tr><th></th>" + "".join("<th>{}</th>".format(d) for d in range(1, an["n"] + 1)) + "</tr>"
    body = ""
    for s in "PSM":
        body += "<tr><td class='l'>{}</td>".format(SHIFT_NAME[s])
        for d in range(1, an["n"] + 1):
            c = an["slots"][(d, s)]
            stt = c["state"]
            tip = {"ok": "{:g}°C normal", "high": "{:g}°C DI ATAS batas", "low": "{:g}°C di bawah batas"}.get(stt, "")
            tip = "Tgl {} {}: ".format(d, SHIFT_NAME[s]) + (tip.format(c["t"]) if tip else ("KOSONG" if stt == "empty" else "belum jatuh tempo"))
            txt = {"ok": "&#10003;", "high": "&#9650;", "low": "&#9660;", "empty": "&ndash;", "future": ""}[stt]
            body += "<td class='s-{}' title='{}'>{}</td>".format(stt, tip, txt)
        body += "</tr>"
    st.markdown("<div style='overflow-x:auto'><table class='cal'>{}{}</table></div>".format(head, body), unsafe_allow_html=True)
    st.markdown("<div class='lg2'><span><i class='s-ok'></i>Dalam batas</span><span><i class='s-high'></i>&#9650; Di atas batas</span><span><i class='s-low'></i>&#9660; Di bawah batas</span>"
                "<span><i class='s-empty'></i>Kosong (belum diisi)</span><span><i class='s-future'></i>Belum jatuh tempo</span></div>", unsafe_allow_html=True)

    hi_days = sorted(set(d for d, _, _ in an["high"]))
    lo_days = sorted(set(d for d, _, _ in an["low"]))
    emp_days = sorted(an["empty_by_day"].keys())
    st.markdown("<div class='box'><b>Ringkasan {} - {} {}</b><br>"
                "&#128308; Tanggal dengan suhu <b>di atas batas</b> ({:g} &deg;C): <b>{}</b><br>"
                "&#128992; Tanggal dengan suhu di bawah batas ({:g} &deg;C): <b>{}</b><br>"
                "&#9899; Tanggal yang ada <b>slot kosong</b>: <b>{}</b><br>"
                "&#9898; Tanggal <b>kosong total</b> (P, S, M belum diisi): <b>{}</b></div>".format(
                    ruang, BLN[m - 1], y, std["t_hi"], days_text(hi_days), std["t_lo"], days_text(lo_days), days_text(emp_days), days_text(an["full_empty"])),
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Suhu di atas batas**")
        st.dataframe(pd.DataFrame([dict(Tanggal=d, Shift=SHIFT_NAME[s], **{"Suhu (°C)": v, "Batas atas": std["t_hi"], "Selisih": round(v - std["t_hi"], 1)}) for d, s, v in an["high"]]
                                  or [dict(Tanggal="-", Shift="-", **{"Suhu (°C)": "-", "Batas atas": "-", "Selisih": "-"})]), hide_index=True)
        if an["low"]:
            st.markdown("**Suhu di bawah batas**")
            st.dataframe(pd.DataFrame([dict(Tanggal=d, Shift=SHIFT_NAME[s], **{"Suhu (°C)": v, "Batas bawah": std["t_lo"], "Selisih": round(v - std["t_lo"], 1)}) for d, s, v in an["low"]]), hide_index=True)
    with c2:
        st.markdown("**Tanggal & shift kosong**")
        st.dataframe(pd.DataFrame([dict(Tanggal=d, **{"Shift kosong": ", ".join(SHIFT_NAME[x] for x in v), "Status": "Kosong total" if len(v) == 3 else "Sebagian"}) for d, v in sorted(an["empty_by_day"].items())]
                                  or [dict(Tanggal="-", **{"Shift kosong": "Semua terisi", "Status": "-"})]), hide_index=True)
    with c3:
        st.markdown("**Kelembapan di luar batas ({:g}–{:g} %)**".format(std["h_lo"], std["h_hi"]))
        st.dataframe(pd.DataFrame([dict(Tanggal=d, Shift=SHIFT_NAME[s], **{"Kelembapan (%)": v, "Keterangan": "Di atas" if k == "high" else "Di bawah"}) for d, s, v, k in an["hum_bad"]]
                                  or [dict(Tanggal="-", Shift="-", **{"Kelembapan (%)": "-", "Keterangan": "-"})]), hide_index=True)

    st.markdown("**Rekap semua ruangan - {} {}**".format(BLN[m - 1], y))
    rows = []
    for rn in room_names():
        a = analyze(rn, y, m, TODAY())
        rows.append({"Ruangan": rn, "% Pengisian": round(a["pct_fill"]), "% Suhu dalam batas": round(a["pct_ok"]), "Suhu di atas batas": len(a["high"]),
                     "Suhu di bawah batas": len(a["low"]), "Slot kosong": a["n_empty"], "Tanggal kosong total": days_text(a["full_empty"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True)


def page_input():
    header()
    st.caption("Input suhu harian")
    left, right = st.columns([2.2, 1], gap="large")
    cfg = load_cfg()
    with left:
        ruang = st.selectbox("Ruangan *", room_names(), key="in_ruang")
        std = room_std(ruang)
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal pengukuran *", value=TODAY(), key="in_tgl")
        shift_key = c2.radio("Shift pemantauan *", list(SHIFT_LABEL.keys()), format_func=lambda k: SHIFT_LABEL[k], horizontal=True, key="in_shift")
        c3, c4 = st.columns(2)
        suhu = c3.number_input("Suhu (°C) [standar {:g}–{:g}] *".format(std["t_lo"], std["t_hi"]), value=float((std["t_lo"] + std["t_hi"]) / 2), step=0.1, format="%.1f", key="in_suhu")
        hum = c4.number_input("Kelembapan (%) [standar {:g}–{:g}] *".format(std["h_lo"], std["h_hi"]), value=50.0, step=1.0, format="%.0f", key="in_hum")
        ts, hs = classify(suhu, std["t_lo"], std["t_hi"]), classify(hum, std["h_lo"], std["h_hi"])
        with c3:
            st.markdown("<div class='hint {}'>{}</div>".format("ok" if ts == "ok" else "bad", "✓ Dalam batas standar" if ts == "ok" else "⚠ {} batas standar ({:g}–{:g} °C)".format("DI ATAS" if ts == "high" else "DI BAWAH", std["t_lo"], std["t_hi"])), unsafe_allow_html=True)
        with c4:
            st.markdown("<div class='hint {}'>{}</div>".format("ok" if hs == "ok" else "bad", "✓ Dalam batas standar" if hs == "ok" else "⚠ {} batas standar ({:g}–{:g} %)".format("DI ATAS" if hs == "high" else "DI BAWAH", std["h_lo"], std["h_hi"])), unsafe_allow_html=True)
        tek, tek_tanda = None, ""
        if std.get("tekanan") or st.checkbox("Ruangan ini memiliki tekanan (isi Tek + / Tek -)", key="in_has_tek"):
            c5, c6 = st.columns(2)
            tek_tanda = "+" if c5.radio("Jenis tekanan", ["Tek +", "Tek -"], horizontal=True, key="in_tek_t") == "Tek +" else "-"
            tek = c6.number_input("Tekanan (Pa)", value=0.0, step=0.5, key="in_tek")
        petugas = st.selectbox("Inisial Radiografer *", cfg["staff"], key="in_petugas")
        abn = ts != "ok" or hs != "ok"
        temuan, tindakan = "", ""
        if abn:
            temuan = st.text_area("Temuan ketidaksesuaian * (wajib karena di luar batas standar)", key="in_temuan")
            tindakan = st.selectbox("Tindakan korektif *", ["Lapor Teknisi AC / Maintenance", "Pengaturan AC / Dehumidifier", "Lainnya"], key="in_tindakan")
        ada = load_entries()
        dup = len(ada[(ada["ruang"] == ruang) & (ada["tanggal"] == tgl.isoformat()) & (ada["shift"] == shift_key)]) > 0
        timpa = True
        if dup:
            st.warning("Data {} - {} - shift {} sudah ada.".format(ruang, tgl.strftime("%d/%m/%Y"), SHIFT_NAME[shift_key]))
            timpa = st.checkbox("Timpa data yang sudah ada", key="in_timpa")
        if st.button("Simpan data suhu", type="primary", key="in_save", disabled=(dup and not timpa)):
            if abn and not temuan.strip():
                st.error("Kolom Temuan wajib diisi karena suhu/kelembapan di luar batas standar.")
            else:
                save_entry(overwrite=True, ruang=ruang, tanggal=tgl.isoformat(), shift=shift_key, suhu=suhu, kelembapan=hum, tek="" if tek is None else tek, tek_tanda=tek_tanda,
                           petugas=petugas, status="Abnormal" if abn else "Normal", temuan=temuan, tindakan=tindakan)
                st.success("Data tersimpan: {} - {} - {} ({} °C / {} %).".format(ruang, tgl.strftime("%d/%m/%Y"), SHIFT_NAME[shift_key], fnum(suhu), fnum(hum)))
                st.toast("Data berhasil disimpan", icon="✅")
    with right:
        st.markdown("<div class='box'><b>Panduan pengisian</b><br>1. Pilih ruangan, tanggal, dan shift (P 08.00 · S 14.00 · M 21.00).<br>2. Isi suhu & kelembapan aktual.<br>3. Pilih inisial radiografer.<br>"
                    "4. Bila di luar batas standar, temuan & tindakan korektif wajib diisi - akan tampil di kolom <i>Keterangan</i> pada formulir.<br>5. Cek hasilnya di menu Dashboard atau Download.</div>", unsafe_allow_html=True)
    st.markdown("**Data terakhir - {}**".format(ruang))
    df = load_entries()
    df = df[df["ruang"] == ruang].sort_values("id", key=lambda s: s.astype(int), ascending=False).head(15)
    if len(df):
        st.dataframe(df[["id", "tanggal", "shift", "suhu", "kelembapan", "petugas", "status", "temuan"]], hide_index=True)
        cc1, cc2 = st.columns([1, 3])
        did = cc1.selectbox("Hapus data ID", list(df["id"]), key="in_del")
        if cc2.button("Hapus data terpilih", key="in_del_btn"):
            delete_entry(did)
            st.success("Data ID {} dihapus.".format(did))
    else:
        st.caption("Belum ada data yang diinput untuk ruangan ini.")


def page_download():
    header()
    st.caption("Download data - formulir resmi (PDF)")

    # >>> Cek font & tampilkan debug info
    reg_ok, bold_ok = _register_lexend()
    if reg_ok and bold_ok:
        st.markdown(
            "<div class='ok-info'>✅ <b>Font Lexend terpasang dengan benar.</b> "
            "Semua teks PDF akan memakai font Lexend.</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div class='warn'>⚠️ <b>Font Lexend belum berhasil dipasang.</b><br>"
            "Letakkan file <code>Lexend-Regular.ttf</code> dan <code>Lexend-Bold.ttf</code> di folder yang sama dengan "
            "<code>app.py</code>. Sementara PDF akan memakai Helvetica.</div>",
            unsafe_allow_html=True)
        with st.expander("🔧 Info Debug Font"):
            st.code(lexend_debug_info())

    ruang, m, y = filter_bar("dl")
    sh = build_form(ruang, y, m, month_data(ruang, y, m, TODAY()))
    zoom = st.slider("Zoom preview (%)", 60, 200, 100, 10, key="dl_zoom")
    wpx = int(1400 * zoom / 100)
    svg = sheet_to_svg(sh, wpx)
    components.html("<div style='overflow:auto;background:#fff;border:1px solid #d5dbe3'>{}</div>".format(svg), height=int(wpx * (sh.height + 8) / (XE + 8)) + 30, scrolling=True)
    fname = "Form_Suhu_Kelembapan_{}_{}_{:02d}".format(ruang.replace(" ", "_").replace(".", ""), y, m)
    c1, c2, c3 = st.columns(3)
    try:
        c1.download_button("⬇️ Download PDF (ruangan ini)", sheets_to_pdf([sh], "Formulir Suhu dan Kelembapan - " + ruang), fname + ".pdf", "application/pdf", key="dl_pdf")
        allsh = [build_form(rn, y, m, month_data(rn, y, m, TODAY())) for rn in room_names()]
        c2.download_button("⬇️ Download PDF (semua ruangan)", sheets_to_pdf(allsh, "Formulir Suhu dan Kelembapan - Semua Ruangan"), "Form_Suhu_Kelembapan_SEMUA_{}_{:02d}.pdf".format(y, m), "application/pdf", key="dl_pdf_all")
    except ImportError:
        st.error("Library reportlab belum terpasang. Jalankan:  pip install reportlab")
    rows = []
    for (d, s), e in sorted(month_data(ruang, y, m, TODAY()).items()):
        rows.append({"Ruang": ruang, "Tanggal": dt.date(y, m, d).isoformat(), "Shift": SHIFT_NAME[s], "Suhu (°C)": e["suhu"], "Kelembapan (%)": e["hum"],
                     "Tekanan": "" if e["tek"] is None else "{}{}".format(e["tek_tanda"], fnum(e["tek"])), "Petugas": e["petugas"], "Keterangan": e["ket"], "Sumber": "Input"})
    dfm = pd.DataFrame(rows)
    c3.download_button("⬇️ Download data (CSV)", dfm.to_csv(index=False).encode("utf-8-sig"), fname + ".csv", "text/csv", key="dl_csv")
    st.caption("PDF A4 landscape, vektor. Memuat logo Primaya (kiri atas), footer Primaya (full width), tabel standar suhu & kelembapan, serta Form/PHG/GAD-11-1/Rev.03.")


# =====================================================================
# 6. NAVIGASI & SIDEBAR
# =====================================================================
pg = st.navigation([
    st.Page(page_dashboard, title="1. Dashboard", icon="📊", url_path="dashboard", default=True),
    st.Page(page_input, title="2. Input Suhu Harian", icon="🌡️", url_path="input"),
    st.Page(page_download, title="3. Download Data", icon="⬇️", url_path="download"),
])

with st.sidebar:
    # >>> REVISI 3: LOGO PRIMAYA di ujung kanan atas sidebar
    if os.path.exists(LOGO_FILE):
        with open(LOGO_FILE, "rb") as f:
            _b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            "<div style='display:flex;justify-content:flex-end;margin-bottom:8px'>"
            "<img src='data:image/png;base64,{b64}' style='height:48px;background:#fff;padding:4px 8px;border-radius:6px'>"
            "</div>".format(b64=_b64),
            unsafe_allow_html=True)

    # Kotak RADIOLOGY DEPARTMENT
    st.markdown(
        "<div style='background:#005580;color:#fff;border-radius:8px;padding:10px;text-align:center'>"
        "<b>RADIOLOGY DEPARTMENT</b><br><span style='font-size:11px;opacity:.9'>PHPK 2026</span></div>",
        unsafe_allow_html=True)

    # >>> REVISI 4: HAPUS st.date_input "Tanggal sistem (hari ini)"
    # TODAY() sekarang fallback ke dt.date.today() otomatis.

    with st.expander("Pengaturan ruang & petugas"):
        cfg = load_cfg()
        nm = st.text_input("Nama ruang baru", key="cfg_nm")
        c1, c2 = st.columns(2)
        tl = c1.number_input("Suhu min (°C)", value=20.0, step=0.5, key="cfg_tl")
        th = c2.number_input("Suhu maks (°C)", value=24.0, step=0.5, key="cfg_th")
        hl = c1.number_input("Kelembapan min (%)", value=40.0, step=1.0, key="cfg_hl")
        hh = c2.number_input("Kelembapan maks (%)", value=60.0, step=1.0, key="cfg_hh")
        tk = st.checkbox("Ruang bertekanan (Tek +/-)", key="cfg_tk")
        if st.button("Simpan ruang", key="cfg_add"):
            if nm.strip():
                cfg["rooms"] = [r for r in cfg["rooms"] if r["nama"] != nm.strip()] + [dict(nama=nm.strip(), t_lo=tl, t_hi=th, h_lo=hl, h_hi=hh, tekanan=tk)]
                save_cfg(cfg)
                st.success("Ruang disimpan.")
        stf = st.text_input("Inisial petugas (pisahkan koma)", value=",".join(cfg["staff"]), key="cfg_staff")
        if st.button("Simpan petugas", key="cfg_staff_btn"):
            cfg["staff"] = [x.strip().upper() for x in stf.split(",") if x.strip()] or cfg["staff"]
            save_cfg(cfg)
            st.success("Petugas disimpan.")
    st.caption("Form/PHG/GAD-11-1/Rev.03")

pg.run()
