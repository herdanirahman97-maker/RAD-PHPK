# -*- coding: utf-8 -*-
"""
Formulir Digital Suhu & Kelembapan Departemen Radiologi - Primaya Hospital
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

st.set_page_config(page_title="Radiologi - Primaya Hospital", page_icon="🏥", layout="wide")

DATA_DIR = "data_primaya_radiologi"
ENTRY_FILE = os.path.join(DATA_DIR, "entries.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# =====================================================================
# STYLING & BRANDING
# =====================================================================
st.markdown("""
<style>
.stApp{background:#f4f7fa}
.block-container{padding-top:1.2rem;max-width:100%}
[data-testid=stSidebar]{background:#ffffff}
button[kind="primary"]{background:#005580;border-color:#005580}
.prim-header-box{
    display:flex; align-items:center; justify-content:space-between;
    background:linear-gradient(135deg,#003358,#005580); 
    color:white; padding:16px 22px; border-radius:10px; margin-bottom:16px;
}
.prim-title h1{font-size:18px; margin:0; font-weight:700;}
.prim-title p{font-size:11px; margin:3px 0 0; opacity:.90;}
.card{background:#fff;border-radius:8px;padding:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.stat-box{display:flex;gap:12px;margin-bottom:12px}
.stat-card{flex:1;background:#fff;border-radius:8px;padding:12px 14px;box-shadow:0 1px 2px rgba(0,0,0,0.05);border-top:4px solid #005580}
.stat-card .t{font-size:11px;color:#666}
.stat-card .v{font-size:22px;font-weight:bold;margin:4px 0;color:#111}
</style>
""", unsafe_allow_html=True)

ROOM_STANDARDS = {
    "CT Scan": {"temp": (18, 22), "hum": (40, 60), "ref": "Standar Alat CT"},
    "USG": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "R.Operator": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "ESWL": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Panoramik": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"},
    "Radiografi Umum": {"temp": (20, 24), "hum": (40, 60), "ref": "Permenkes No. 40 Tahun 2022"}
}

ROOM_LIST = list(ROOM_STANDARDS.keys())
SHIFTS = ["P - Pagi (08.00)", "S - Sore (14.00)", "M - Malam (21.00)"]
STAFF_LIST = ["SL", "AG", "AY", "WT", "FF"]
BLN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

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

def render_header(title):
    logo_path = "Primaya Logo.png"
    logo_html = ""
    if os.path.exists(logo_path):
        import base64
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{encoded}' style='height:38px; object-fit:contain; background:white; padding:4px 10px; border-radius:6px; margin-right:15px;'>"
    else:
        logo_html = "<div style='background:white;color:#005580;padding:6px 12px;border-radius:6px;font-weight:bold;margin-right:15px;'>+ PRIMAYA</div>"
        
    st.markdown(f"""
    <div class='prim-header-box'>
        <div style='display:flex; align-items:center;'>
            {logo_html}
            <div class='prim-title'>
                <h1>FORMULIR DIGITAL SUHU & KELEMBAPAN &ndash; RADIOLOGI</h1>
                <p>{title}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 1. MENU: DASHBOARD
# =====================================================================
def page_dashboard():
    render_header("Dashboard Rangkuman Pencapaian Suhu & Kelembapan")
    
    col1, col2 = st.columns([2, 2])
    ruang = col1.selectbox("Pilih Ruangan Radiologi", ROOM_LIST)
    t = TODAY()
    m_idx = col2.selectbox("Pilih Bulan", range(1, 13), format_func=lambda x: BLN[x-1], index=t.month-1)
    
    std = ROOM_STANDARDS[ruang]
    t_lo, t_hi = std["temp"]
    
    days_in_month = calendar.monthrange(t.year, m_idx)[1]
    real_data = {}
    for r in load_entries().to_dict("records"):
        if r["ruang"] == ruang:
            try:
                td = dt.date.fromisoformat(r["tanggal"])
                if td.year == t.year and td.month == m_idx:
                    real_data[(td.day, (r["shift"] or "P")[:1])] = r
            except Exception:
                pass
                
    rnd = random.Random(zlib.crc32(ruang.encode()))
    records_evaluated = []
    empty_slots = []
    abnormal_slots = []
    
    for d in range(1, days_in_month + 1):
        cur_date = dt.date(t.year, m_idx, d)
        for s_code in ["P", "S", "M"]:
            if (d, s_code) in real_data:
                item = real_data[(d, s_code)]
                val_t = float(item["suhu"])
                is_abn = not (t_lo <= val_t <= t_hi)
                records_evaluated.append(1)
                if is_abn:
                    abnormal_slots.append(f"Tanggal {d} Shift {s_code} (Suhu: {val_t}°C)")
            elif DUMMY() and cur_date <= t:
                val_t = round(rnd.uniform(t_lo - 0.5, t_hi + 0.5), 1)
                if rnd.random() < 0.08:
                    val_t = t_hi + 1.5
                is_abn = not (t_lo <= val_t <= t_hi)
                records_evaluated.append(1)
                if is_abn:
                    abnormal_slots.append(f"Tanggal {d} Shift {s_code} (Suhu: {val_t}°C)")
            else:
                if cur_date <= t:
                    empty_slots.append(f"Tanggal {d} Shift {s_code}")

    total_expected = min(t.day, days_in_month) * 3 if m_idx == t.month else days_in_month * 3
    total_filled = len(records_evaluated)
    pct = round((total_filled / total_expected) * 100) if total_expected > 0 else 0
    
    st.markdown(f"""
    <div class='stat-box'>
        <div class='stat-card'><div class='t'>Persentase Pengisian Data</div><div class='v'>{pct}%</div></div>
        <div class='stat-card' style='border-top-color:#d64545'><div class='t'>Total Suhu Di Luar Batas</div><div class='v' style='color:#d64545'>{len(abnormal_slots)} Slot</div></div>
        <div class='stat-card' style='border-top-color:#f0a81c'><div class='t'>Total Jadwal Kosong / Belum Diisi</div><div class='v' style='color:#f0a81c'>{len(empty_slots)} Slot</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ⚠️ Tanggal & Shift Suhu Di Atas/Bawah Batas Standar")
        if abnormal_slots:
            for ab in abnormal_slots:
                st.markdown(f"- 🔴 {ab} *(Target: {t_lo}&ndash;{t_hi}°C)*")
        else:
            st.success("Tidak ada catatan suhu di luar batas standar pada periode ini.")
            
    with c2:
        st.markdown("### 📭 Tanggal & Shift Kosong (Belum Terisi)")
        if empty_slots:
            st.info("Berikut daftar slot waktu yang belum diinput datanya:")
            st.write(", ".join(empty_slots[:30]))
            if len(empty_slots) > 30:
                st.caption(f"...dan {len(empty_slots)-30} slot lainnya.")
        else:
            st.success("Semua jadwal pemantauan terisi lengkap!")

# =====================================================================
# 2. MENU: INPUT SUHU HARIAN
# =====================================================================
def page_input():
    render_header("Formulir Input Suhu Harian Radiologi")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        ruang = st.selectbox("Pilih Ruangan Radiologi *", ROOM_LIST)
        std = ROOM_STANDARDS[ruang]
        t_lo, t_hi = std["temp"]
        h_lo, h_hi = std["hum"]
        
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal Pengukuran *", value=TODAY())
        shift = st.selectbox("Shift Pemantauan *", SHIFTS)
        
        c3, c4 = st.columns(2)
        suhu = c3.number_input(f"Suhu (°C) [Standar: {t_lo}-{t_hi}] *", value=float((t_lo+t_hi)/2), step=0.1, format="%.1f")
        hum = c4.number_input(f"Kelembapan (%) [Standar: {h_lo}-{h_hi}] *", value=50.0, step=1.0, format="%.0f")
        
        ok_t = t_lo <= suhu <= t_hi
        ok_h = h_lo <= hum <= h_hi
        
        if not ok_t:
            st.warning(f"⚠ Perhatian: Suhu {suhu}°C berada di luar rentang standar ({t_lo}&ndash;{t_hi}°C).")
            
        petugas = st.selectbox("Inisial Radiografer *", STAFF_LIST)
        
        temuan, tindakan = "", ""
        if not (ok_t and ok_h):
            temuan = st.text_area("Temuan Ketidaksesuaian *")
            tindakan = st.selectbox("Tindakan Korektif *", ["Lapor Teknisi AC / Maintenance", "Pengaturan AC / Dehumidifier", "Lainnya"])
            
        code = shift[0]
        if st.button("Simpan Data Suhu", type="primary"):
            if not ok_t and not temuan.strip():
                st.error("Karena suhu di luar batas standar, kolom Temuan wajib diisi.")
            else:
                save_entry(ruang=ruang, tanggal=tgl.isoformat(), shift=code, suhu=suhu, kelembapan=hum,
                           petugas=petugas, status="Abnormal" if not ok_t else "Normal", temuan=temuan, tindakan=tindakan)
                st.success(f"Data suhu untuk {ruang} berhasil disimpan!")
                st.toast("Data berhasil disimpan ke sistem!", icon="✅")
                
    with col2:
        st.markdown("""
        <div class='card'>
            <b>Panduan Pengisian:</b><br>
            1. Pilih ruangan Radiologi yang dipantau.<br>
            2. Masukkan angka suhu dan kelembapan aktual.<br>
            3. Pilih inisial Radiografer (SL, AG, AY, WT, FF).<br>
            4. Jika suhu melebihi standar, sistem mewajibkan pengisian temuan tindakan korektif.
        </div>
        """, unsafe_allow_html=True)

# =====================================================================
# 3. MENU: DOWNLOAD DATA (FORMAT GRAFIK TITIK HITAM/MERAH & PETUGAS)
# =====================================================================
def page_download():
    render_header("Unduh Rekapitulasi Data Format Formulir Resmi Primaya")
    
    col_f1, col_f2 = st.columns(2)
    selected_filter_room = col_f1.selectbox("Pilih Ruangan untuk Diunduh", ROOM_LIST)
    t = TODAY()
    sel_month = col_f2.selectbox("Pilih Bulan Laporan", range(1, 13), format_func=lambda x: BLN[x-1], index=t.month-1)
    
    st.markdown(f"### Preview Matrik Format Formulir Fisik ({selected_filter_room} - {BLN[sel_month-1]} {t.year})")
    st.caption("🔴 Titik Merah = Suhu di luar batas standar | ⚫ Titik Hitam = Suhu normal")
    
    days_in_month = calendar.monthrange(t.year, sel_month)[1]
    
    real_data = {}
    for r in load_entries().to_dict("records"):
        if r["ruang"] == selected_filter_room:
            try:
                td = dt.date.fromisoformat(r["tanggal"])
                if td.year == t.year and td.month == sel_month:
                    real_data[(td.day, (r["shift"] or "P")[:1])] = r
            except Exception:
                pass
                
    rnd = random.Random(zlib.crc32(selected_filter_room.encode()))
    std = ROOM_STANDARDS[selected_filter_room]
    t_lo, t_hi = std["temp"]
    h_lo, h_hi = std["hum"]
    
    # Rentang suhu visual untuk tabel matriks (misal dari 16°C sampai 32°C)
    temp_levels = list(range(32, 15, -1))
    
    matrix_data = []
    
    # Baris Suhu (16 sampai 32 derajat) dengan titik hitam/merah
    for temp_val in temp_levels:
        row_dict = {"Parameter / Suhu": f"{temp_val} °C"}
        for d in range(1, 32):
            cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
            for s_code in ["P", "S", "M"]:
                col_key = f"Tgl {d} ({s_code})"
                if d <= days_in_month:
                    val = None
                    if (d, s_code) in real_data:
                        val = float(real_data[(d, s_code)]["suhu"])
                    elif DUMMY() and cur_date <= t:
                        val = round(rnd.uniform(t_lo - 0.5, t_hi + 0.5), 1)
                        if rnd.random() < 0.05:
                            val = t_hi + 1.5
                            
                    if val is not None and round(val) == temp_val:
                        # Tentukan titik hitam atau merah berdasarkan standar
                        if t_lo <= val <= t_hi:
                            row_dict[col_key] = "● (Hitam)"   # Normal
                        else:
                            row_dict[col_key] = "🔴 (Merah)"   # Di luar batas
                    else:
                        row_dict[col_key] = ""
                else:
                    row_dict[col_key] = "-"
        matrix_data.append(row_dict)
        
    # Baris Kelembapan
    hum_row = {"Parameter / Suhu": "Kelembapan (%)"}
    for d in range(1, 32):
        cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
        for s_code in ["P", "S", "M"]:
            col_key = f"Tgl {d} ({s_code})"
            if d <= days_in_month:
                if (d, s_code) in real_data:
                    hum_row[col_key] = str(real_data[(d, s_code)]["kelembapan"])
                elif DUMMY() and cur_date <= t:
                    hum_row[col_key] = str(int(round(rnd.uniform(45, 55), 0)))
                else:
                    hum_row[col_key] = ""
            else:
                hum_row[col_key] = "-"
    matrix_data.append(hum_row)
    
    # Baris Inisial Petugas per Shift (Pagi, Sore, Malam)
    for shift_name, s_code in [("Nama (Pagi)", "P"), ("Nama (Siang)", "S"), ("Nama (Malam)", "M")]:
        staff_row = {"Parameter / Suhu": shift_name}
        for d in range(1, 32):
            cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
            for sc in ["P", "S", "M"]:
                col_key = f"Tgl {d} ({sc})"
                if sc == s_code and d <= days_in_month:
                    if (d, s_code) in real_data:
                        staff_row[col_key] = real_data[(d, s_code)]["petugas"]
                    elif DUMMY() and cur_date <= t:
                        staff_row[col_key] = STAFF_LIST[(d + (0 if s_code=='P' else 1 if s_code=='S' else 2)) % len(STAFF_LIST)]
                    else:
                        staff_row[col_key] = ""
                else:
                    if sc == s_code:
                        staff_row[col_key] = ""
                    else:
                        # Kolom shift lain dikosongkan pada baris shift ini agar persis seperti form cetak
                        pass
        # Perbaikan mapping kolom shift per baris petugas
        clean_staff_row = {"Parameter / Suhu": shift_name}
        for d in range(1, 32):
            for sc in ["P", "S", "M"]:
                col_key = f"Tgl {d} ({sc})"
                if sc == s_code and d <= days_in_month:
                    val_st = ""
                    if (d, s_code) in real_data:
                        val_st = real_data[(d, s_code)]["petugas"]
                    elif DUMMY() and dt.date(t.year, sel_month, d) <= t:
                        val_st = STAFF_LIST[(d + (0 if s_code=='P' else 1 if s_code=='S' else 2)) % len(STAFF_LIST)]
                    clean_staff_row[col_key] = val_st
                else:
                    clean_staff_row[col_key] = ""
        matrix_data.append(clean_staff_row)

    final_df = pd.DataFrame(matrix_data)
    st.dataframe(final_df, use_container_width=True)
    
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        final_df.to_excel(xw, sheet_name=f"Form_{selected_filter_room[:12]}", index=False)
        
    st.download_button(
        label=f"⬇️️ Download Excel Format Formulir Resmi ({selected_filter_room})",
        data=bio.getvalue(),
        file_name=f"Formulir_Suhu_{selected_filter_room.lower().replace(' ', '_')}_{BLN[sel_month-1]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

# =====================================================================
# NAVIGASI UTAMA
# =====================================================================
pages = {
    "Menu Utama": [
        st.Page(page_dashboard, title="1. Dashboard Rangkuman", icon="📊", default=True),
        st.Page(page_input, title="2. Input Suhu Harian", icon="🌡️"),
        st.Page(page_download, title="3. Download Data", icon="🗂️"),
    ]
}

pg = st.navigation(pages)

with st.sidebar:
    st.markdown("---")
    st.markdown("<div style='background:#005580;color:#fff;border-radius:8px;padding:8px;text-align:center'><b>RADIOLOGI DEPARTMENT</b></div>", unsafe_allow_html=True)
    st.date_input("Tanggal Simulasi", value=dt.date(2026, 9, 5), key="sim_today")
    st.checkbox("Tampilkan Data Dummy", value=True, key="use_dummy", help="Mengisi otomatis data simulasi untuk keperluan demo dashboard")
    st.caption("Form/PHG/GAD-11-1/Rev.03")

pg.run()
