    standards = [
        ("Operasi", "20-26", "40-60"),
        ("Tindakan", "20-24", "40-60"),
        ("Radiologi", "20-24", "40-60"),
        ("Radioterapi/Kedokteran Nuklir", "20-24", "40-60"),
        ("Server/MCFA/Kontrol/UPS", "20-24", "40-60"),
        ("Genset/Trafo", "35-40", "40-60"),
    ]
    sw = table_w / len(standards)
    for i, (name, tr, hu) in enumerate(standards):
        xx = x0 + i*sw
        c.setFillColor(colors.HexColor("#dcecf8"))
        c.rect(xx, sy-18, sw, 18, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 4.0)
        c.drawCentredString(xx+sw/2, sy-5, name[:28])
        c.setFont("Helvetica", 4.0)
        c.drawCentredString(xx+sw/2, sy-10.5, f"Suhu (°C) {tr}")
        c.drawCentredString(xx+sw/2, sy-16, f"Kelembaban (%) {hu}")

    # Source / form number
    pdf_text(c, x0, sy-27,
             "Sumber: Permenkes No. 02 Tahun 2023; Permenkes No. 40 Tahun 2022; Permenkes No. 72 Tahun 2016; CDC 2003",
             4.2, False)
    pdf_text(c, right-100, sy-27, "Form/PHG/GAD-11-1/Rev.03", 4.2, True)

    # Footer bar
    fy = 32
    c.setFillColor(colors.HexColor("#00658b"))
    c.rect(x0, fy, table_w, 18, fill=1, stroke=0)
    pdf_text(c, x0+8, fy+6, "www.primayahospital.com   |   @primayahospital", 5, True, colors.white)

    c.save()
    buf.seek(0)
    return buf.getvalue()


# ============================================================
# DOWNLOAD
# ============================================================
def page_download():
    header("DOWNLOAD DATA")

    today = dt.date.today()
    c1, c2, c3 = st.columns([2, 1, 1])
    room = c1.selectbox("Ruangan", list(ROOM_STANDARDS.keys()), key="pdf_room")
    year = c2.number_input("Tahun", 2020, 2100, today.year, key="pdf_year")
    month = c3.selectbox(
        "Bulan",
        range(1, 13),
        index=today.month - 1,
        format_func=lambda x: MONTHS[x-1],
        key="pdf_month",
    )

    df = get_month_data(room, year, month)
    st.markdown(
        f"**Preview data:** {room} — {MONTHS[month-1]} {year} — "
        f"{len(df)} data tersimpan."
    )

    if not df.empty:
        preview = df[[
            "date", "shift", "temperature", "humidity", "staff",
            "status_temp", "status_hum"
        ]].copy()
        preview.columns = [
            "Tanggal", "Shift", "Suhu", "Kelembapan", "Petugas",
            "Status Suhu", "Status Kelembapan"
        ]
        st.dataframe(preview, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data pada periode ini. PDF tetap dapat dibuat sebagai formulir kosong.")

    pdf_bytes = build_pdf(room, year, month)
    filename = (
        f"Form_Suhu_Kelembapan_{room.replace(' ', '_')}_"
        f"{year}_{month:02d}.pdf"
    )

    st.download_button(
        "⬇️ DOWNLOAD PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "PDF dibuat dalam format A4 landscape dan mengikuti susunan formulir "
        "referensi: tanggal 1–31, shift P/S/M, grafik titik suhu, kelembapan, "
        "nama petugas, catatan, standar ruangan, dan footer."
    )


# ============================================================
# NAVIGATION - compatible with older Streamlit versions
# ============================================================
with st.sidebar:
    st.markdown("### PRIMAYA RADIOLOGY")
    st.caption("Monitoring Suhu & Kelembapan")
    st.markdown("---")
    menu = st.radio(
        "MENU",
        [
            "1. Dashboard",
            "2. Input Suhu Harian",
            "3. Download Data",
        ],
        index=0,
    )
    st.markdown("---")
    st.caption("Data tersimpan lokal pada:")
    st.code(ENTRY_FILE, language=None)
    st.caption("Form/PHG/GAD-11-1/Rev.03")

if menu == "1. Dashboard":
    page_dashboard()
elif menu == "2. Input Suhu Harian":
    page_input()
else:
    page_download()
