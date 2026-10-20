# -*- coding: utf-8 -*-
"""
PHT-Tracker (Pressure, Humidity, Temp)
FORMULIR DIGITAL MONITORING SUHU DAN KELEMBAPAN DEPARTEMEN RADIOLOGI PHPK 2026
Primaya Hospital  |  Form/PHG/GAD-11-1/Rev.03
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
FONT_FILE = "Primaya Font.ttf"

os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "rooms": [
        "Ruang X-Ray 1",
        "Ruang X-Ray 2",
        "Ruang CT-Scan",
        "Ruang MRI",
        "Ruang USG",
        "Ruang Mammografi",
        "Ruang Panoramic",
        "Ruang Fluoroskopi",
    ],
    "temp_min": 18.0,
    "temp_max": 26.0,
    "hum_min": 30.0,
    "hum_max": 60.0,
}

ENTRY_COLS = [
    "timestamp", "tanggal", "shift", "ruang",
    "suhu", "kelembapan", "catatan", "petugas",
]

SHIFTS = ["Pagi", "Siang", "Malam"]


# ---------------------------------------------------------------- helpers
def load_config():
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG


def save_config(cfg):
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_entries():
    if os.path.exists(ENTRY_FILE):
        try:
            df = pd.read_csv(ENTRY_FILE)
            for c in ENTRY_COLS:
                if c not in df.columns:
                    df[c] = None
            return df[ENTRY_COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=ENTRY_COLS)


def save_entries(df):
    df.to_csv(ENTRY_FILE, index=False, encoding="utf-8")


def img_to_b64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ---------------------------------------------------------------- header
def render_header():
    st.markdown(
        """
        <div style="text-align:center; line-height:1.2; margin-bottom:10px;">
            <h1 style="font-size:3.2rem; font-weight:900; color:#0B5FA5;
                       letter-spacing:2px; margin:0 0 4px 0;
                       text-transform:uppercase;">PHT-Tracker</h1>
            <p style="font-size:1.05rem; font-weight:500; color:#555;
                      letter-spacing:1px; margin:0 0 14px 0;
                      font-style:italic;">Pressure · Humidity · Temp</p>
            <h3 style="font-size:1.15rem; font-weight:600; color:#222;
                       margin:0 0 6px 0; letter-spacing:0.5px;">
                FORMULIR DIGITAL MONITORING SUHU DAN KELEMBAPAN<br>
                DEPARTEMEN RADIOLOGI PHPK 2026</h3>
            <p style="font-size:0.9rem; color:#777; margin:0;">
                Primaya Hospital &nbsp;|&nbsp; Form/PHG/GAD-11-1/Rev.03</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- sidebar
def render_sidebar(cfg):
    with st.sidebar:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, use_container_width=True)
        st.markdown("### 📋 Ringkasan")
        entries = load_entries()
        if not entries.empty:
            df = entries.copy()
            today = dt.date.today().isoformat()
            st.metric("Total Entri", len(df))
            st.metric("Entri Hari Ini",
                      int((df["tanggal"] == today).sum()))
            alert_mask = (
                (df["suhu"] < cfg["temp_min"]) | (df["suhu"] > cfg["temp_max"]) |
                (df["kelembapan"] < cfg["hum_min"]) | (df["kelembapan"] > cfg["hum_max"])
            )
            st.metric("⚠️ Di Luar Rentang", int(alert_mask.sum()))
        else:
            st.caption("Belum ada data.")
        st.markdown("---")
        st.caption(f"📁 `{os.path.abspath(DATA_DIR)}`")
        st.caption(f"Form/PHG/GAD-11-1/Rev.03")


# ---------------------------------------------------------------- input form
def render_entry_form(cfg, entries):
    st.subheader("📝 Input Data Monitoring")

    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        tanggal = c1.date_input("Tanggal", value=dt.date.today())
        shift = c2.selectbox("Shift", SHIFTS)
        ruang = c3.selectbox("Ruang", cfg["rooms"])

        c4, c5 = st.columns(2)
        suhu = c4.number_input(
            "Suhu (°C)", min_value=-10.0, max_value=60.0,
            value=22.0, step=0.1, format="%.1f",
        )
        kelembapan = c5.number_input(
            "Kelembapan (%)", min_value=0.0, max_value=100.0,
            value=50.0, step=0.5, format="%.1f",
        )

        petugas = st.text_input("Petugas", placeholder="Nama petugas pemeriksa")
        catatan = st.text_area("Catatan (opsional)", placeholder="Kondisi ruangan, kendala, dsb.")

        submitted = st.form_submit_button(
            "💾 Simpan Data", use_container_width=True, type="primary",
        )

    if submitted:
        alerts = []
        if not (cfg["temp_min"] <= suhu <= cfg["temp_max"]):
            alerts.append(
                f"Suhu **{suhu}°C** di luar rentang "
                f"{cfg['temp_min']}–{cfg['temp_max']}°C."
            )
        if not (cfg["hum_min"] <= kelembapan <= cfg["hum_max"]):
            alerts.append(
                f"Kelembapan **{kelembapan}%** di luar rentang "
                f"{cfg['hum_min']}–{cfg['hum_max']}%."
            )

        new_row = {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "tanggal": tanggal.isoformat(),
            "shift": shift,
            "ruang": ruang,
            "suhu": float(suhu),
            "kelembapan": float(kelembapan),
            "catatan": catatan.strip(),
            "petugas": petugas.strip(),
        }
        entries = pd.concat([entries, pd.DataFrame([new_row])], ignore_index=True)
        save_entries(entries)

        for a in alerts:
            st.warning(f"⚠️ {a}")
        st.success(f"✅ Data tersimpan: **{ruang}** · {tanggal} · shift {shift}.")
        st.rerun()


# ---------------------------------------------------------------- data view
def render_table(entries, cfg):
    st.subheader("📊 Tabel & Grafik")
    if entries.empty:
        st.info("Belum ada data. Silakan input pada tab 📝 Input Data.")
        return

    df = entries.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df["_ym"] = df["tanggal"].dt.strftime("%Y-%m")
    df["tanggal"] = df["tanggal"].dt.date

    c1, c2, c3 = st.columns(3)
    month_opts = sorted(df["_ym"].dropna().unique().tolist(), reverse=True)
    sel_month = c1.selectbox("Bulan", ["Semua"] + month_opts)
    room_opts = sorted(df["ruang"].dropna().unique().tolist())
    sel_room = c2.selectbox("Ruang", ["Semua"] + room_opts)
    sel_shift = c3.selectbox("Shift", ["Semua"] + SHIFTS)

    f = df.copy()
    if sel_month != "Semua":
        f = f[f["_ym"] == sel_month]
    if sel_room != "Semua":
        f = f[f["ruang"] == sel_room]
    if sel_shift != "Semua":
        f = f[f["shift"] == sel_shift]

    st.caption(f"Menampilkan **{len(f)}** dari **{len(df)}** entri.")

    view = f.drop(columns=["_ym", "timestamp"], errors="ignore")
    st.dataframe(view, use_container_width=True, hide_index=True)

    if not f.empty:
        st.markdown("**Tren Suhu & Kelembapan**")
        chart_df = (
            f[["tanggal", "suhu", "kelembapan"]]
            .sort_values("tanggal")
            .set_index("tanggal")
        )
        st.line_chart(chart_df)

        st.markdown("**Ringkasan Statistik**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Suhu rata-rata", f"{f['suhu'].mean():.1f} °C")
        m2.metric("Suhu min/max", f"{f['suhu'].min():.1f} / {f['suhu'].max():.1f} °C")
        m3.metric("Kelembapan rata-rata", f"{f['kelembapan'].mean():.1f} %")
        m4.metric("Kelembapan min/max",
                  f"{f['kelembapan'].min():.1f} / {f['kelembapan'].max():.1f} %")


# ---------------------------------------------------------------- export
def build_html_report(df, cfg):
    logo_b64 = img_to_b64(LOGO_FILE)
    footer_b64 = img_to_b64(FOOTER_FILE)
    font_b64 = img_to_b64(FONT_FILE)

    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:64px;">'
        if logo_b64 else ""
    )
    footer_html = (
        f'<img src="data:image/png;base64,{footer_b64}" style="width:100%;">'
        if footer_b64 else ""
    )
    font_css = (
        f"@font-face {{ font-family:'PrimayaFont'; "
        f"src:url(data:font/ttf;base64,{font_b64}); }}"
        if font_b64 else ""
    )
    font_stack = "PrimayaFont, " if font_b64 else ""

    rows = ""
    for _, r in df.iterrows():
        warn_s = (
            " style='background:#fff3cd'"
            if not (cfg["temp_min"] <= r["suhu"] <= cfg["temp_max"]) else ""
        )
        warn_h = (
            " style='background:#fff3cd'"
            if not (cfg["hum_min"] <= r["kelembapan"] <= cfg["hum_max"]) else ""
        )
        rows += textwrap.dedent(f"""
            <tr>
                <td>{escape(str(r["tanggal"]))}</td>
                <td>{escape(str(r["shift"]))}</td>
                <td>{escape(str(r["ruang"]))}</td>
                <td{warn_s}>{r["suhu"]}</td>
                <td{warn_h}>{r["kelembapan"]}</td>
                <td>{escape(str(r["petugas"]))}</td>
                <td>{escape(str(r["catatan"]))}</td>
            </tr>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>PHT-Tracker Report</title>
<style>
{font_css}
body {{ font-family: {font_stack}Arial, sans-serif; padding:24px; color:#222; }}
h1 {{ color:#0B5FA5; text-align:center; letter-spacing:2px; margin:4px 0; }}
.sub {{ text-align:center; color:#555; margin-bottom:20px; font-size:13px; }}
table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
th, td {{ border:1px solid #ccc; padding:8px; text-align:left; font-size:12px; }}
th {{ background:#0B5FA5; color:white; }}
</style></head>
<body>
<div style="text-align:center;">{logo_html}</div>
<h1>PHT-Tracker</h1>
<p class="sub">
FORMULIR DIGITAL MONITORING SUHU DAN KELEMBAPAN DEPARTEMEN RADIOLOGI PHPK 2026<br>
Primaya Hospital &nbsp;|&nbsp; Form/PHG/GAD-11-1/Rev.03
</p>
<table>
<thead><tr>
<th>Tanggal</th><th>Shift</th><th>Ruang</th>
<th>Suhu (°C)</th><th>Kelembapan (%)</th>
<th>Petugas</th><th>Catatan</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
<div style="margin-top:30px;">{footer_html}</div>
</body></html>"""


def render_export(entries, cfg):
    st.subheader("📤 Export Data")
    if entries.empty:
        st.info("Belum ada data untuk di-export.")
        return

    df = entries.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce").dt.date
    stamp = dt.date.today().isoformat()

    col1, col2 = st.columns(2)

    col1.download_button(
        "⬇️ Download CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"pht_tracker_{stamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Monitoring")
        col2.download_button(
            "⬇️ Download Excel",
            data=buf.getvalue(),
            file_name=f"pht_tracker_{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as e:
        col2.caption(f"Excel tidak tersedia (install `openpyxl`): {e}")

    st.markdown("---")
    html = build_html_report(df, cfg)
    st.download_button(
        "⬇️ Download HTML (Print / PDF Ready)",
        data=html.encode("utf-8"),
        file_name=f"pht_tracker_{stamp}.html",
        mime="text/html",
        use_container_width=True,
    )

    with st.expander("🔍 Pratinjau HTML"):
        components.html(html, height=600, scrolling=True)


# ---------------------------------------------------------------- settings
def render_settings(cfg):
    st.subheader("⚙️ Pengaturan")

    with st.form("cfg_form"):
        rooms_text = st.text_area(
            "Daftar ruang (satu per baris)",
            value="\n".join(cfg["rooms"]),
            height=220,
        )
        c1, c2 = st.columns(2)
        t_min = c1.number_input("Suhu min (°C)", value=float(cfg["temp_min"]), step=0.5)
        t_max = c2.number_input("Suhu max (°C)", value=float(cfg["temp_max"]), step=0.5)

        c3, c4 = st.columns(2)
        h_min = c3.number_input("Kelembapan min (%)", value=float(cfg["hum_min"]), step=1.0)
        h_max = c4.number_input("Kelembapan max (%)", value=float(cfg["hum_max"]), step=1.0)

        saved = st.form_submit_button(
            "💾 Simpan Pengaturan", type="primary", use_container_width=True,
        )

    if saved:
        cfg["rooms"] = [r.strip() for r in rooms_text.splitlines() if r.strip()]
        cfg["temp_min"], cfg["temp_max"] = float(t_min), float(t_max)
        cfg["hum_min"], cfg["hum_max"] = float(h_min), float(h_max)
        save_config(cfg)
        st.success("Pengaturan disimpan.")
        st.rerun()

    with st.expander("⚠️ Danger Zone"):
        st.caption("Tindakan ini tidak dapat dibatalkan.")
        if st.button("🗑️ Hapus semua data entries"):
            save_entries(pd.DataFrame(columns=ENTRY_COLS))
            st.success("Semua data entries telah dihapus.")
            st.rerun()


# ---------------------------------------------------------------- footer
def render_footer():
    st.markdown("---")
    if os.path.exists(FOOTER_FILE):
        st.image(FOOTER_FILE, use_container_width=True)
    st.caption(
        "PHT-Tracker · Primaya Hospital · "
        "Form/PHG/GAD-11-1/Rev.03 · Departemen Radiologi PHPK 2026"
    )


# ---------------------------------------------------------------- main
def main():
    cfg = load_config()
    entries = load_entries()

    render_header()
    render_sidebar(cfg)

    tab_input, tab_data, tab_export, tab_cfg = st.tabs(
        ["📝 Input Data", "📊 Tabel & Grafik", "📤 Export", "⚙️ Pengaturan"]
    )

    with tab_input:
        render_entry_form(cfg, entries)
    with tab_data:
        render_table(entries, cfg)
    with tab_export:
        render_export(entries, cfg)
    with tab_cfg:
        render_settings(cfg)

    render_footer()


if __name__ == "__main__":
    main()
