# -*- coding: utf-8 -*-
"""
Formulir Digital Suhu, Kelembapan, dan Tekanan Ruangan
Primaya Hospital | Streamlit App (app.py)

Jalankan: streamlit run app.py
Syarat: streamlit>=1.36, pandas, openpyxl
"""
import calendar
import datetime as dt
import io
import os
import random
import zlib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Monitoring Suhu & Ruangan - Primaya Hospital", page_icon="🏥", layout="wide")

DATA_DIR = "data_primaya"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
ENTRY_FILE = os.path.join(DATA_DIR, "entries.csv")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================================
# 1. CSS & STYLING (BRANDING PRIMAYA)
# =====================================================================
st.markdown("""
<style>
.stApp{background:#f4f7fa}
.block-container{padding-top:1.2rem;max-width:100%}
[data-testid=stSidebar]{background:#ffffff}
button[kind="primary"]{background:#005580;border-color:#005580}
.prim-logo-container{
    display:flex; align-items:center; gap:14px; 
    background:linear-gradient(135deg,#003358,#005580); 
    color:white; padding:18px 24px; border-radius:10px; margin-bottom:16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
}
.prim-logo-icon{
    background:white; color:#005580; width:48px; height:48px; 
    border-radius:10px; display:flex; align-items:center; justify-content:center; 
    font-size:26px; font-weight:bold; flex-shrink:0; box-shadow:0 2px 4px rgba(0,0,0,0.15);
}
.prim-logo-text h1{font-size:20px; margin:0; font-weight:700; letter-spacing:0.5px;}
.prim-logo-text p{font-size:12px; margin:4px 0 0; opacity:.90; letter-spacing:0.3px;}
.dc-pn{background:#f6f8fb;border:1px solid #e1e7ef;border-radius:8px;padding:12px 14px;font-size:12.5px;line-height:1.75;margin-bottom:12px}
.dc-pn b{display:block;margin-bottom:3px}.dc-pn.gr{background:#f1faf4;border-color:#bfe3cb}
.dc-pn.rd{background:#fff4f4;border-color:#f2c0c0}
.dc-hint{font-size:12px;margin:-8px 0 8px 2px}.dc-hint.ok{color:#2e9e5b}.dc-hint.bad{color:#d64545}
</style>
""", unsafe_allow_html=True)

DASH_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{overflow-x:hidden;background:transparent}
body{font-family:'Arial',sans-serif;color:#1f2937;font-size:12px}
.wrap{padding:2px}
.sec{background:#fff;border-radius:8px;margin-bottom:12px;overflow:hidden;box-shadow:0 1px 2px #0001}
.sh{background:#cfe3f7;padding:11px 14px;font-weight:bold;font-size:12.5px;display:flex;justify-content:space-between}
.tw{padding:10px 14px;overflow-x:auto}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #dfe5ec;padding:5px 6px;text-align:center;font-size:10.5px}
th{background:#005580;color:#fff;font-weight:600}td.l,th.l{text-align:left}
.stats{display:flex;gap:10px;margin-bottom:10px}.stat{flex:1;background:#f6f8fb;border-radius:6px;padding:8px 12px}
.stat .l{font-size:10.5px;color:#666}.stat .v{font-size:18px;font-weight:bold}
"""

AUTOSIZE = """<script>
function fit(){try{var h=Math.ceil(document.body.getBoundingClientRect().height)+8;
window.frameElement.style.height=h+'px';}catch(e){}}
window.addEventListener('load',fit);
try{new ResizeObserver(fit).observe(document.body);}catch(e){}
</script>"""

def render(body, height=550):
    doc = "<html><head><meta charset='utf-8'><style>" + DASH_CSS + "</style></head><body><div class='wrap'>" + body + "</div>" + AUTOSIZE + "</body></html>"
    components.html(doc, height=height, scrolling=True)

def render_logo_header(subtitle="Sistem Pemantauan Lingkungan Ruangan Medis & Penunjang"):
    st.markdown(f"""
    <div class='prim-logo-container'>
        <div class='prim-logo-icon'>+</div>
        <div class='prim-logo-text'>
            <h1>PRIMAYA HOSPITAL</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 2. DATA MASTER & STANDAR RUANGAN PRIMAYA
# =====================================================================
BLN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

ROOM_STANDARDS = {
    "Operasi": {"temp": (20, 26), "hum": (40, 60), "ref": "Permenkes No. 02 Tahun 2023"},
    "Tindakan": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 02 Tahun 2023"},
    "Rawat inap/rawat jalan/isolasi/Bayi Normal": {"temp": (22, 24), "hum": (40, 60), "ref": "Permenkes No. 02 Tahun 2023"},
    "Teknik/Ruang Panel/Ruang Mesin RO": {"temp": (22, 24), "hum": (40, 60), "ref": "Permenkes No. 02 Tahun 2023"},
    "ICU/PICU/HCU/NICU/IGD": {"temp": (22, 26), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Laboratorium/Radiologi/Kamar Jenazah/Farmasi": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Mesin Lift": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Dapur": {"temp": (22, 30), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Luka Bakar": {"temp": (24, 26), "hum": (40, 60), "ref": "Permenkes No. 72 Tahun 2016"},
    "CSSD - Pembersihan/Penyimpanan": {"temp": (22, 26), "hum": (40, 50), "ref": "Permenkes No. 72 Tahun 2016"},
    "Gudang Linen Bersih/Rekam Medis": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 72 Tahun 2016"},
    "Server/MCFA/Kontrol/UPS": {"temp": (20, 24), "hum": (40, 60), "ref": "Standar IT"},
    "Genset/Trafo": {"temp": (35, 40), "hum": (40, 60), "ref": "Standar MEP"},
    "Angiografi/Radioterapi/Kedokteran Nuklir": {"temp": (20, 24), "hum": (40, 60), "ref": "CDC Guidelines"},
    "Philips Brilliance CT": {"temp": (18, 22), "hum": (40, 60), "ref": "Standar Alat CT"}
}

ROOM_LIST = list(ROOM_STANDARDS.keys())
SHIFTS = ["P - Pagi (08.00)", "S - Sore (14.00)", "M - Malam (21.00)"]
STAFF_LIST = ["AG", "FF", "SL", "AY", "WT", "ND", "RR"]

ECOLS = ["id", "dibuat", "ruang", "tanggal", "shift", "suhu", "kelembapan", "petugas", "status", "temuan", "tindakan"]

def load_entries():
    if os.path.exists(ENTRY_FILE):
        try:
            return pd.read_csv(ENTRY_FILE, dtype=str).fillna("")
        except Exception:
            return pd.DataFrame(columns=ECOLS)
    return pd.DataFrame(columns=ECOLS)

def save_entry(**kw):
    df = load_entries()
    row = {c: "" for c in ECOLS}
    for k, v in kw.items():
        row[k] = str(v)
    row["id"] = str(len(df) + 1)
    row["dibuat"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(ENTRY_FILE, index=False)

def TODAY():
    v = st.session_state.get("sim_today")
    return v if isinstance(v, dt.date) else dt.date(2026, 9, 5)

def DUMMY():
    return bool(st.session_state.get("use_dummy", True))

def recs(ruang=None):
    df = load_entries()
    if ruang:
        df = df[df["ruang"] == ruang]
    out = []
    for r in df.to_dict("records"):
        try:
            r["tgl"] = dt.date.fromisoformat(r["tanggal"])
        except Exception:
            continue
        out.append(r)
    return out

# =====================================================================
# 3. GRAFIK & VISUALISASI
# =====================================================================
def suhu_series(ruang, y, m, today, dummy):
    n = calendar.monthrange(y, m)[1]
    T, H, W = [None] * (n * 3), [None] * (n * 3), [""] * (n * 3)
    r = random.Random(zlib.crc32(ruang.encode()))
    std = ROOM_STANDARDS.get(ruang, {"temp": (18, 24), "hum": (40, 60)})
    t_lo, t_hi = std["temp"]
    h_lo, h_hi = std["hum"]

    real = {}
    for x in recs(ruang):
        if x["tgl"].year == y and x["tgl"].month == m:
            real[(x["tgl"].day, (x["shift"] or "P")[:1])] = x

    for d in range(1, n + 1):
        for k, code in enumerate("PSM"):
            idx = (d - 1) * 3 + k
            dv_t = r.uniform(t_lo, t_hi)
            dv_h = r.uniform(h_lo, h_hi)
            if r.random() < .05:
                dv_t = t_hi + r.uniform(0.5, 2.0)

            if (d, code) in real:
                x = real[(d, code)]
                try:
                    T[idx], H[idx] = float(x["suhu"]), float(x["kelembapan"])
                except ValueError:
                    pass
                W[idx] = x["petugas"][:2].upper()
            elif dummy and dt.date(y, m, d) <= today:
                T[idx], H[idx], W[idx] = round(dv_t, 1), round(dv_h, 1), STAFF_LIST[idx % len(STAFF_LIST)]
    return T, H, W, t_lo, t_hi, h_lo, h_hi

def chart_svg(title, vals, who, ymin, ymax, lo, hi, n, W=1450):
    L = 36
    cw = (W - L) / (n * 3)
    Hh, top, bot = 180, 30, 14
    y = lambda v: top + (ymax - v) / (ymax - ymin) * Hh
    s = f"<svg width='{W}' height='{top + Hh + bot + 14}' xmlns='http://www.w3.org/2000/svg' font-family='Arial' font-size='9'>"
    s += f"<rect x='0' y='0' width='{W}' height='15' fill='#e2e8f0'/><text x='{W/2}' y='11' text-anchor='middle' font-weight='bold'>{title}</text>"
    for d in range(n):
        x = L + d * 3 * cw
        s += f"<rect x='{x}' y='15' width='{3*cw}' height='{top - 15 + Hh}' fill='{'#f8fafc' if d%2 else '#fff'}'/><text x='{x + 1.5*cw}' y='24' text-anchor='middle' font-weight='bold'>{d+1}</text>"
        for k, nm in enumerate("PSM"):
            s += f"<text x='{x + (k+.5)*cw}' y='31' text-anchor='middle' font-size='7'>{nm}</text>"
    s += f"<rect x='{L}' y='{y(hi)}' width='{W-L}' height='{y(lo)-y(hi)}' fill='#2e9e5b' opacity='.08'/>"
    v = ymin
    while v <= ymax:
        bad = v < lo or v > hi
        s += f"<line x1='{L}' x2='{W}' y1='{y(v)}' y2='{y(v)}' stroke='#e2e8f0'/><text x='18' y='{y(v)+3}' text-anchor='middle' fill='{'#d64545' if bad else '#333'}'>{v:g}</text>"
        v += max(1, (ymax - ymin) // 5)
    for t in (lo, hi):
        s += f"<line x1='{L}' x2='{W}' y1='{y(t)}' y2='{y(t)}' stroke='#005580' stroke-dasharray='4 2' stroke-width='1.2'/>"
    pts = [(L + (i + .5) * cw, y(max(ymin, min(ymax, val)))) if val is not None else None for i, val in enumerate(vals)]
    for p, val in zip(pts, vals):
        if p is not None:
            bad = val < lo or val > hi
            s += f"<circle cx='{p[0]:.1f}' cy='{p[1]:.1f}' r='3' fill='{'#d64545' if bad else '#005580'}'/>"
    for i in range(n * 3):
        s += f"<text x='{L + (i+.5)*cw:.1f}' y='{top + Hh + 10}' text-anchor='middle' font-size='6.5' fill='#555'>{who[i]}</text>"
    return s + f"<text x='18' y='{top + Hh + 10}' text-anchor='middle' font-size='6.5' font-weight='bold'>PIC</text></svg>"

def monitoring_section_html(ruang, y, m, today, dummy):
    n = calendar.monthrange(y, m)[1]
    T, H, W, t_lo, t_hi, h_lo, h_hi = suhu_series(ruang, y, m, today, dummy)
    tv, hv = [v for v in T if v is not None], [v for v in H if v is not None]
    inT = sum(t_lo <= v <= t_hi for v in tv)
    inH = sum(h_lo <= v <= h_hi for v in hv)
    
    def st_(l, v, c="#111"):
        return f"<div class='stat'><div class='l'>{l}</div><div class='v' style='color:{c}'>{v}</div></div>"
    
    stats = f"<div class='stats'>{st_('Ruang', ruang)}{st_('Target Suhu', f'{t_lo}&ndash;{t_hi} °C')}{st_('Target Kelembapan', f'{h_lo}&ndash;{h_hi} %')}{st_('Suhu Sesuai', f'{inT}/{len(tv)}' if tv else '-')}{st_('Kelembapan Sesuai', f'{inH}/{len(hv)}' if hv else '-')}</div>"
    body = stats + chart_svg(f"MONITORING SUHU (°C) &middot; {ruang}", T, W, 15, 42, t_lo, t_hi, n)
    body += "<div style='height:6px'></div>" + chart_svg(f"KELEMBAPAN (%) &middot; {ruang}", H, W, 30, 70, h_lo, h_hi, n)
    return f"<div class='sec'><div class='sh'>{ruang} &ndash; {BLN[m-1]} {y}</div><div class='tw'>{body}</div></div>"

# =====================================================================
# 4. HALAMAN APLIKASI
# =====================================================================
def page_home():
    render_logo_header("Formulir Digital Suhu, Kelembapan, dan Tekanan Ruangan")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ruangan Terdaftar", len(ROOM_LIST))
    col2.metric("Shift Pemantauan", "3 Shift (Pagi, Sore, Malam)")
    col3.metric("Standar Kepatuhan", "Permenkes / CDC")
    
    st.markdown("### Daftar Standar Ruangan & Parameter")
    data_tab = [{"Ruang / Unit": k, "Suhu Min-Max (°C)": f"{v['temp'][0]} - {v['temp'][1]}", "Kelembapan (%)": f"{v['hum'][0]} - {v['hum'][1]}", "Referensi": v['ref']} for k, v in ROOM_STANDARDS.items()]
    st.dataframe(pd.DataFrame(data_tab), use_container_width=True)

def page_input():
    render_logo_header("Input Data Harian Suhu & Kelembapan")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        ruang = st.selectbox("Pilih Ruangan / Unit *", ROOM_LIST, key="in_ruang")
        std = ROOM_STANDARDS[ruang]
        t_lo, t_hi = std["temp"]
        h_lo, h_hi = std["hum"]
        
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal *", value=TODAY(), key="in_tgl")
        shift = st.selectbox("Shift *", SHIFTS, key="in_shift")
        
        c3, c4 = st.columns(2)
        suhu = c3.number_input(f"Suhu (°C) [Standar: {t_lo}-{t_hi}] *", value=float((t_lo+t_hi)/2), step=0.1, format="%.1f", key="in_suhu")
        hum = c4.number_input(f"Kelembapan (%) [Standar: {h_lo}-{h_hi}] *", value=50.0, step=1.0, format="%.0f", key="in_hum")
        
        ok_t = t_lo <= suhu <= t_hi
        ok_h = h_lo <= hum <= h_hi
        with c3:
            st.markdown(f"<div class='dc-hint {'ok' if ok_t else 'bad'}'>{'✓ Sesuai standar' + f' ({t_lo}-{t_hi}°C)' if ok_t else '⚠ Di luar batas standar'}</div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='dc-hint {'ok' if ok_h else 'bad'}'>{'✓ Sesuai standar' + f' ({h_lo}-{h_hi}%)' if ok_h else '⚠ Di luar batas standar'}</div>", unsafe_allow_html=True)
            
        petugas = st.text_input("Inisial Petugas (mis. AG, FF) *", value="AG", key="in_pet")
        abn = not (ok_t and ok_h)
        temuan, tindakan = "", ""
        if abn:
            temuan = st.text_area("Temuan Ketidaksesuaian *", key="in_tem")
            tindakan = st.selectbox("Tindakan Korektif *", ["Lapor Maintenance / AC", "Pengaturan Dehumidifier", "Lainnya"], key="in_tind")
            
        code = shift[0]
        if st.button("Simpan Data Suhu", type="primary"):
            if not petugas.strip():
                st.error("Inisial petugas wajib diisi.")
            elif abn and not temuan.strip():
                st.error("Temuan wajib diisi karena nilai di luar batas standar.")
            else:
                save_entry(ruang=ruang, tanggal=tgl.isoformat(), shift=code, suhu=suhu, kelembapan=hum,
                           petugas=petugas, status="Abnormal" if abn else "Normal", temuan=temuan, tindakan=tindakan)
                st.success(f"Data untuk {ruang} berhasil disimpan!")
                st.toast("Data tersimpan & grafik diperbarui", icon="✅")
                
    with col2:
        st.markdown("<div class='dc-pn gr'><b>Panduan Pengisian</b><br>1. Pilih ruangan sesuai lokasi.<br>2. Masukkan hasil ukur suhu & kelembapan.<br>3. Jika di luar batas Permenkes, wajib mengisi temuan & tindakan korektif.</div>", unsafe_allow_html=True)

def page_dashboard():
    render_logo_header("Dashboard Pemantauan Suhu & Kelembapan")
    
    c1, c2, c3 = st.columns([2, 2, 1])
    ruang = c1.selectbox("Pilih Ruangan", ROOM_LIST, key="db_ruang")
    t = TODAY()
    m = c2.selectbox("Bulan", BLN, index=t.month-1, key="db_bln")
    m_idx = BLN.index(m) + 1
    
    render(monitoring_section_html(ruang, t.year, m_idx, t, DUMMY()), 480)

def page_rekap():
    render_logo_header("Rekapitulasi & Unduh Data")
    
    df = load_entries()
    if df.empty:
        st.info("Belum ada data tersimpan. Silakan lakukan input melalui menu Input Data.")
        return
        
    st.dataframe(df, use_container_width=True)
    
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="Data_Suhu_Primaya", index=False)
    st.download_button("⬇️ Download Rekap Excel", bio.getvalue(), "rekap_suhu_primaya.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================================================================
# 5. NAVIGASI UTAMA
# =====================================================================
pages = {
    "Primaya Monitoring": [
        st.Page(page_home, title="Beranda & Standar", icon="🏥", default=True),
        st.Page(page_input, title="Input Suhu & Kelembapan", icon="🌡️"),
        st.Page(page_dashboard, title="Dashboard Grafik", icon="📈"),
        st.Page(page_rekap, title="Rekap & Download", icon="🗂️"),
    ]
}

pg = st.navigation(pages)

with st.sidebar:
    st.markdown("---")
    st.markdown("<div style='background:#005580;color:#fff;border-radius:8px;padding:12px;text-align:center'><b>+ PRIMAYA HOSPITAL</b><br><small>Suhu & Kelembapan</small></div>", unsafe_allow_html=True)
    st.date_input("Tanggal Simulasi", value=dt.date(2026, 9, 5), key="sim_today")
    st.checkbox("Tampilkan Data Dummy", value=True, key="use_dummy")
    st.caption("Form/PHG/GAD-11-1/Rev.03")

pg.run()
