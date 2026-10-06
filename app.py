# -*- coding: utf-8 -*-
import calendar
import datetime as dt
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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');
.stApp { background: #f4f7fa; font-family: 'Lexend', sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 100%; }
[data-testid=sidebar] { background: #ffffff; font-family: 'Lexend', sans-serif; }
button[kind="primary"] { background: #005580; border-color: #005580; font-family: 'Lexend', sans-serif; }
.prim-header-box {
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(135deg,#003358,#005580); 
    color: white; padding: 16px 22px; border-radius: 10px; margin-bottom: 16px;
    font-family: 'Lexend', sans-serif;
}
.prim-title h1 { font-size: 18px; margin: 0; font-weight: 700; font-family: 'Lexend', sans-serif; }
.prim-title p { font-size: 11px; margin: 3px 0 0; opacity: .90; font-family: 'Lexend', sans-serif; }
.card { background: #fff; border-radius: 8px; padding: 14px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); font-family: 'Lexend', sans-serif; }
.stat-box { display: flex; gap: 12px; margin-bottom: 12px; }
.stat-card { flex: 1; background: #fff; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border-top: 4px solid #005580; font-family: 'Lexend', sans-serif; }
.stat-card .t { font-size: 11px; color: #666; font-family: 'Lexend', sans-serif; }
.stat-card .v { font-size: 22px; font-weight: bold; margin: 4px 0; color: #111; font-family: 'Lexend', sans-serif; }
</style>
""", unsafe_allow_html=True)

ROOM_STANDARDS = {
    "CT Scan": {"temp": (18, 22), "hum": (40, 60)},
    "USG": {"temp": (20, 24), "hum": (40, 60)},
    "R.Operator": {"temp": (20, 24), "hum": (40, 60)},
    "ESWL": {"temp": (20, 24), "hum": (40, 60)},
    "Panoramik": {"temp": (20, 24), "hum": (40, 60)},
    "Radiografi Umum": {"temp": (20, 24), "hum": (40, 60)}
}

ROOM_LIST = list(ROOM_STANDARDS.keys())
SHIFTS = ["P - Pagi (08.00)", "S - Sore (14.00)", "M - Malam (21.00)"]
STAFF_LIST = ["SL", "AG", "AY", "WT", "FF"]
MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

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

def get_logo_base64():
    logo_path = "Primaya Logo.png"
    if os.path.exists(logo_path):
        try:
            import base64
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            pass
    return None

def render_header(title):
    encoded = get_logo_base64()
    logo_html = f"<img src='data:image/png;base64,{encoded}' style='height:36px; object-fit:contain; background:white; padding:4px 10px; border-radius:6px; margin-right:15px;'>" if encoded else "<div style='background:white;color:#005580;padding:6px 12px;border-radius:6px;font-weight:bold;margin-right:15px;'>+ PRIMAYA</div>"
        
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

def page_dashboard():
    render_header("Dashboard Rangkuman Pencapaian Suhu & Kelembapan")
    col1, col2 = st.columns([2, 2])
    ruang = col1.selectbox("Pilih Ruangan Radiologi", ROOM_LIST)
    t = TODAY()
    m_idx = col2.selectbox("Pilih Bulan", range(1, 13), format_func=lambda x: MONTHS[x-1], index=t.month-1)
    
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
    records_evaluated, empty_slots, abnormal_slots = [], [], []
    
    for d in range(1, days_in_month + 1):
        cur_date = dt.date(t.year, m_idx, d)
        for s_code in ["P", "S", "M"]:
            if (d, s_code) in real_data:
                item = real_data[(d, s_code)]
                val_t = float(item["suhu"])
                is_abn = not (t_lo <= val_t <= t_hi)
                records_evaluated.append(1)
                if is_abn: abnormal_slots.append(f"Tanggal {d} Shift {s_code} (Suhu: {val_t}°C)")
            elif DUMMY() and cur_date <= t:
                val_t = round(rnd.uniform(t_lo - 0.5, t_hi + 0.5), 1)
                if rnd.random() < 0.08: val_t = t_hi + 1.5
                is_abn = not (t_lo <= val_t <= t_hi)
                records_evaluated.append(1)
                if is_abn: abnormal_slots.append(f"Tanggal {d} Shift {s_code} (Suhu: {val_t}°C)")
            else:
                if cur_date <= t: empty_slots.append(f"Tanggal {d} Shift {s_code}")

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
            for ab in abnormal_slots: st.markdown(f"- 🔴 {ab} *(Target: {t_lo}&ndash;{t_hi}°C)*")
        else: st.success("Tidak ada catatan suhu di luar batas standar pada periode ini.")
    with c2:
        st.markdown("### 📭 Tanggal & Shift Kosong (Belum Terisi)")
        if empty_slots:
            st.info("Berikut daftar slot waktu yang belum diinput datanya:")
            st.write(", ".join(empty_slots[:30]))
        else: st.success("Semua jadwal pemantauan terisi lengkap!")

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
        if not ok_t: st.warning(f"⚠ Perhatian: Suhu {suhu}°C berada di luar rentang standar ({t_lo}&ndash;{t_hi}°C).")
            
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

def page_download():
    render_header("Cetak / Unduh Formulir Resmi Suhu & Kelembapan Ruangan")
    col_f1, col_f2 = st.columns(2)
    selected_filter_room = col_f1.selectbox("Pilih Ruangan", ROOM_LIST)
    t = TODAY()
    sel_month = col_f2.selectbox("Pilih Bulan Laporan", range(1, 13), format_func=lambda x: MONTHS[x-1], index=t.month-1)
    
    st.markdown("### Preview Formulir Fisik Resmi Primaya Hospital (Landscape & Scrollable)")
    st.caption("Tabel dilengkapi horizontal scroll dengan lebar sel diperbesar agar titik dan angka kelembapan termuat sempurna.")
    
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
    
    temp_rows_html = ""
    for temp_val in range(32, 17, -1):
        row_cells = f"<td style='border:1px solid #b0c4de; padding:4px; text-align:center; font-weight:bold; background:#eef5fc; width:110px; height:26px; font-size:11px; white-space:nowrap;'>{temp_val}°C</td>"
        for d in range(1, 32):
            cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
            for s_code in ["P", "S", "M"]:
                dot_html = ""
                if d <= days_in_month:
                    val = None
                    if (d, s_code) in real_data:
                        val = float(real_data[(d, s_code)]["suhu"])
                    elif DUMMY() and cur_date <= t:
                        val = round(rnd.uniform(t_lo, t_hi), 1)
                        if rnd.random() < 0.05: val = t_hi + 1.5
                            
                    if val is not None and round(val) == temp_val:
                        color = "#d64545" if not (t_lo <= val <= t_hi) else "#111"
                        dot_html = f"<div style='width:7px; height:7px; background:{color}; border-radius:50%; margin:0 auto;'></div>"
                row_cells += f"<td style='border:1px solid #dcdcdc; padding:2px; text-align:center; width:34px; height:26px;'>{dot_html}</td>"
        row_cells += "<td style='border:1px solid #b0c4de; width:130px;'></td>"
        temp_rows_html += f"<tr>{row_cells}</tr>"
        
    hum_cells = "<td style='border:1px solid #b0c4de; padding:4px; font-weight:bold; background:#eef5fc; font-size:10px; height:28px;'>Kelembapan (%)</td>"
    for d in range(1, 32):
        cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
        for s_code in ["P", "S", "M"]:
            h_val = ""
            if d <= days_in_month:
                if (d, s_code) in real_data:
                    h_val = str(int(float(real_data[(d, s_code)]["kelembapan"])))
                elif DUMMY() and cur_date <= t:
                    h_val = str(int(round(rnd.uniform(45, 55), 0)))
            hum_cells += f"<td style='border:1px solid #dcdcdc; padding:2px; text-align:center; font-size:9px; width:34px; height:28px;'>{h_val}</td>"
    hum_cells += "<td style='border:1px solid #b0c4de;'></td>"
            
    staff_rows_html = ""
    for label_s, code_s in [("Nama (Pagi)", "P"), ("Nama (Siang)", "S"), ("Nama (Malam)", "M")]:
        st_cells = f"<td style='border:1px solid #b0c4de; padding:4px; font-weight:bold; background:#eef5fc; font-size:10px; height:28px;'>{label_s}</td>"
        for d in range(1, 32):
            cur_date = dt.date(t.year, sel_month, d) if d <= days_in_month else None
            for sc in ["P", "S", "M"]:
                st_val = ""
                if d <= days_in_month and sc == code_s:
                    if (d, code_s) in real_data:
                        st_val = real_data[(d, code_s)]['petugas']
                    elif DUMMY() and cur_date <= t:
                        st_val = STAFF_LIST[(d + (0 if code_s=='P' else 1 if code_s=='S' else 2)) % len(STAFF_LIST)]
                st_cells += f"<td style='border:1px solid #dcdcdc; padding:2px; text-align:center; font-size:9px; font-weight:bold; width:34px; height:28px;'>{st_val}</td>"
        st_cells += "<td style='border:1px solid #b0c4de;'></td>"
        staff_rows_html += f"<tr>{st_cells}</tr>"

    hdr_days = "<td rowspan='2' style='border:1px solid #b0c4de; background:#005580; color:white; font-weight:bold; padding:4px; font-size:10px; text-align:center; width:110px;'>Tanggal</td>"
    hdr_shifts = ""
    for d in range(1, 32):
        hdr_days += f"<td colspan='3' style='border:1px solid #b0c4de; background:#005580; color:white; font-weight:bold; text-align:center; font-size:10px; height:22px;'>{d}</td>"
        hdr_shifts += "<td style='border:1px solid #b0c4de; background:#cfe3f7; color:#111; text-align:center; font-size:8.5px; font-weight:bold; width:34px; height:20px;'>P</td><td style='border:1px solid #b0c4de; background:#cfe3f7; color:#111; text-align:center; font-size:8.5px; font-weight:bold; width:34px; height:20px;'>S</td><td style='border:1px solid #b0c4de; background:#cfe3f7; color:#111; text-align:center; font-size:8.5px; font-weight:bold; width:34px; height:20px;'>M</td>"
    hdr_days += "<td rowspan='2' style='border:1px solid #b0c4de; background:#005580; color:white; font-weight:bold; padding:4px; font-size:10px; text-align:center; width:130px;'>Keterangan</td>"

    ref_rooms_data = [
        ("Operasi", "20-26", "40-60"), ("Tindakan", "20-24", "40-60"),
        ("Rawat inap/jalan/isolasi/Bayi Normal", "22-24", "40-60"),
        ("Teknik/Ruang Panel/Mesin RO", "22-24", "40-60"),
        ("ICU/PICU/HCU/NICU/IGD", "22-26", "40-60"),
        ("Laboratorium/Radiologi/Farmasi", "20-24", "40-60"),
        ("Mesin Lift", "20-24", "40-60"), ("Dapur", "22-30", "40-60"),
        ("IGD", "22-26", "40-60"), ("Luka Bakar", "24-26", "40-60"),
        ("CSSD Steril", "20-24", "40-60"), ("Server/UPS", "20-24", "40-60"),
        ("Angiografi/Radioterapi", "20-24", "40-60")
    ]
    
    ref_th = "<td style='border:1px solid #005580; background:#cfe3f7; font-weight:bold; text-align:center; font-size:8.5px; padding:4px;'>Ruangan/Unit</td>"
    ref_suhu = "<td style='border:1px solid #b0c4de; background:#eef5fc; font-weight:bold; font-size:8.5px; padding:4px;'>Suhu (°C)</td>"
    ref_hum = "<td style='border:1px solid #b0c4de; background:#eef5fc; font-weight:bold; font-size:8.5px; padding:4px;'>Kelembapan (%)</td>"
    
    for r_name, t_val, h_val in ref_rooms_data:
        ref_th += f"<td style='border:1px solid #b0c4de; background:#eef5fc; font-size:8px; text-align:center; padding:3px;'><b>{r_name}</b></td>"
        ref_suhu += f"<td style='border:1px solid #b0c4de; font-size:8px; text-align:center; padding:3px;'>{t_val}</td>"
        ref_hum += f"<td style='border:1px solid #b0c4de; font-size:8px; text-align:center; padding:3px;'>{h_val}</td>"

    encoded_logo = get_logo_base64()
    logo_tag = f"<img src='data:image/png;base64,{encoded_logo}' style='height:38px; object-fit:contain;'>" if encoded_logo else "<div style='font-size:16px; font-weight:bold; color:#005580;'>PRIMAYA HOSPITAL</div>"

    print_html = f"""
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap');
        @page {{ size: landscape; margin: 8mm; }}
        body {{ font-family: 'Lexend', sans-serif; color: #111; margin: 0; padding: 0; background: #fff; }}
        .form-container {{ width: 100%; max-width: 1450px; margin: 0 auto; border: 2px solid #005580; padding: 14px; background: #fff; box-sizing: border-box; }}
        .header-top {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #005580; padding-bottom: 8px; margin-bottom: 8px; }}
        .hospital-title {{ font-size: 16px; font-weight: bold; color: #005580; letter-spacing: 0.5px; }}
        .form-title {{ text-align: right; font-size: 13px; font-weight: bold; color: #005580; line-height: 1.2; }}
        .meta-info {{ display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 8px; font-weight: bold; color: #333; }}
        
        /* Scrollable container styling */
        .table-scroll-wrapper {{
            width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            margin-bottom: 10px;
            border: 1px solid #b0c4de;
        }}
        .table-scroll-wrapper table {{
            border-collapse: collapse;
            width: max-content;
            table-layout: fixed;
        }}
        
        .ref-table-wrapper {{
            width: 100%;
            overflow-x: auto;
            margin-top: 8px;
            border: 1px solid #b0c4de;
        }}
        .ref-table-wrapper table {{
            border-collapse: collapse;
            width: max-content;
        }}

        .bottom-section {{ display: flex; justify-content: space-between; align-items: flex-start; margin-top: 10px; font-size: 9px; }}
        .notes {{ width: 75%; line-height: 1.4; color: #333; }}
        .signature-box {{ width: 22%; border: 1px solid #b0c4de; text-align: center; padding: 6px; height: 55px; display: flex; flex-direction: column; justify-content: space-between; font-weight: bold; font-size: 9.5px; }}
        .footer-bar {{ background: #005580; color: white; padding: 6px 12px; display: flex; justify-content: space-between; align-items: center; font-size: 9.5px; margin-top: 10px; border-radius: 4px; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
            .table-scroll-wrapper {{ overflow: visible; border: none; }}
            .ref-table-wrapper {{ overflow: visible; border: none; }}
        }}
    </style>
    </head>
    <body>
    <div class="form-container">
        <div class="header-top">
            <div class="hospital-title">FORMULIR DIGITAL SUHU, KELEMBAPAN, DAN TEKANAN RUANGAN</div>
            <div>{logo_tag}</div>
        </div>
        <div class="meta-info">
            <div>Bulan, Tahun : {MONTHS[sel_month-1].upper()} {t.year}</div>
            <div>Ruang / Unit : {selected_filter_room}</div>
        </div>
        
        <div class="table-scroll-wrapper">
            <table>
                <tr>{hdr_days}</tr>
                <tr>{hdr_shifts}</tr>
                {temp_rows_html}
                <tr>{hum_cells}</tr>
                {staff_rows_html}
            </table>
        </div>
        
        <div class="ref-table-wrapper">
            <table>
                <tr>{ref_th}</tr>
                <tr>{ref_suhu}</tr>
                <tr>{ref_hum}</tr>
            </table>
        </div>
        
        <div class="bottom-section">
            <div class="notes">
                <b>Catatan:</b><br>
                - P (Pagi) Pkl 08.00 Waktu Setempat, S (Sore) Pkl 14.00 Waktu Setempat, M (Malam) Pkl 21.00 Waktu Setempat.<br>
                - Titik Hitam (●) = Suhu Normal | Titik Merah (🔴) = Suhu di luar batas standar ({t_lo}&ndash;{t_hi}°C).<br>
                - Jika suhu dan kelembapan tidak sesuai dengan batasan normal, segera hubungi petugas maintenance.
            </div>
            <div class="signature-box">
                <div>Mengetahui<br>Koordinator Unit</div>
                <div style="margin-top: 15px;">( .................................................... )</div>
            </div>
        </div>

        <div style="display: flex; justify-content: space-between; font-size: 8.5px; margin-top: 8px; color: #555;">
            <div>Peraturan Menteri Kesehatan Republik Indonesia No. 40 Tahun 2022 Tentang Persyaratan Teknis Bangunan</div>
            <div><b>Form/PHG/GAD-11-1/Rev.03</b></div>
        </div>

        <div class="footer-bar">
            <div>🌐 www.primayahospital.com</div>
            <div>primayahospital</div>
        </div>
    </div>
    
    <div style="text-align: center; margin-top: 15px;" class="no-print">
        <button onclick="window.print()" style="background:#005580; color:white; border:none; padding:10px 24px; font-size:14px; font-weight:bold; border-radius:5px; cursor:pointer; font-family:'Lexend',sans-serif;">🖨 Cetak Formulir Landscape / Simpan ke PDF</button>
    </div>
    </body>
    </html>
    """
    
    components.html(print_html, height=750, scrolling=True)

with st.sidebar:
    st.markdown("### RADIOLOGI DEPARTMENT")
    st.caption("Monitoring Suhu & Kelembapan")
    st.markdown("---")
    menu = st.radio(
        "MENU UTAMA",
        [
            "1. Dashboard",
            "2. Input Suhu Harian",
            "3. Cetak & Unduh PDF",
        ],
        index=0,
    )
    st.markdown("---")
    st.date_input("Tanggal Simulasi", value=dt.date(2026, 9, 5), key="sim_today")
    st.checkbox("Tampilkan Data Dummy", value=True, key="use_dummy")
    st.caption("Form/PHG/GAD-11-1/Rev.03")

if menu == "1. Dashboard":
    page_dashboard()
elif menu == "2. Input Suhu Harian":
    page_input()
else:
    page_download()
