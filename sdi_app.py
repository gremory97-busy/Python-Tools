import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul SDI-RI", layout="wide")
st.title("Evaluasi Kesiapan SDI-RI")
st.markdown("Unggah dataset bebas tanpa batasan nama kolom, lalu petakan variabelnya secara interaktif.")

# 1. FITUR UNGGAH FILE
file_sdi = st.file_uploader("1. Unggah Data SDI-RI (.xlsx / .csv)", type=["xlsx", "csv"])

if file_sdi is not None:
    if file_sdi.name.endswith('.xlsx'):
        df_awal = pd.read_excel(file_sdi)
    else:
        df_awal = pd.read_csv(file_sdi)
    st.success(f"File '{file_sdi.name}' berhasil dimuat!")

    # 2. TABEL INTERAKTIF
    st.write("**2. Tabel Data (Bisa diedit langsung)**")
    df_sdi = st.data_editor(df_awal, num_rows="dynamic", use_container_width=True)
    
    st.divider()

    # MENGAMBIL HANYA KOLOM ANGKA UNTUK DIPILIH
    kolom_angka = df_sdi.select_dtypes(include=['number']).columns.tolist()

    # 3. PEMETAAN KOLOM KE DIMENSI (FLEXIBLE MAPPING)
    st.subheader("3. Pemetaan Indikator ke Dimensi")
    st.write("Silakan pilih kolom mana saja yang merepresentasikan masing-masing dimensi di bawah ini:")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m4, col_m5, col_m6 = st.columns(3)
    
    kbij_cols = col_m1.multiselect("Pilih indikator Kebijakan:", kolom_angka)
    klmb_cols = col_m2.multiselect("Pilih indikator Kelembagaan:", kolom_angka)
    data_cols = col_m3.multiselect("Pilih indikator Data:", kolom_angka)
    tekn_cols = col_m4.multiselect("Pilih indikator Teknologi:", kolom_angka)
    sdm_cols = col_m5.multiselect("Pilih indikator SDM:", kolom_angka)

    st.divider()

    # 4. PENGATURAN BOBOT AHP MANUAL
    st.subheader("4. Penyesuaian Bobot AHP")
    col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns(5)
    w_kbij = col_w1.number_input("Bobot Kebijakan", min_value=0.0, max_value=1.0, value=0.19, step=0.01)
    w_klmb = col_w2.number_input("Bobot Kelembagaan", min_value=0.0, max_value=1.0, value=0.20, step=0.01)
    w_data = col_w3.number_input("Bobot Data", min_value=0.0, max_value=1.0, value=0.21, step=0.01)
    w_tekn = col_w4.number_input("Bobot Teknologi", min_value=0.0, max_value=1.0, value=0.19, step=0.01)
    w_sdm = col_w5.number_input("Bobot SDM", min_value=0.0, max_value=1.0, value=0.21, step=0.01)

    total_bobot = w_kbij + w_klmb + w_data + w_tekn + w_sdm
    if round(total_bobot, 2) != 1.00:
        st.warning(f"⚠️ Total bobot saat ini: **{total_bobot:.2f}**. Idealnya harus sama dengan 1.00.")

    bobot_ahp = {'Kebijakan': w_kbij, 'Kelembagaan': w_klmb, 'Data': w_data, 'Teknologi': w_tekn, 'SDM': w_sdm}

    st.write("")

    # 5. TOMBOL EKSEKUSI
    if st.button("Proses Analisis SDI-RI", type="primary"):
        # Validasi apakah semua dimensi sudah diisi minimal 1 indikator
        if not (kbij_cols and klmb_cols and data_cols and tekn_cols and sdm_cols):
            st.error("Gagal diproses! Pastikan Anda telah memilih minimal satu kolom untuk setiap dimensi di tahap ke-3.")
        else:
            # Menghitung rata-rata fleksibel berdasarkan pilihan user
            rata_dimensi = {
                'Kebijakan': df_sdi[kbij_cols].mean().mean(),
                'Kelembagaan': df_sdi[klmb_cols].mean().mean(),
                'Data': df_sdi[data_cols].mean().mean(),
                'Teknologi': df_sdi[tekn_cols].mean().mean(),
                'SDM': df_sdi[sdm_cols].mean().mean()
            }
            
            skor_komposit = 0
            for dim, skor in rata_dimensi.items():
                skor_komposit += (skor * bobot_ahp[dim])
            skor_akhir = skor_komposit * 20 
            
            st.divider()
            
            # VISUALISASI RADAR CHART
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Radar Chart Kesiapan Dimensi")
                fig_radar = go.Figure(data=go.Scatterpolar(
                    r=list(rata_dimensi.values()),
                    theta=list(rata_dimensi.keys()),
                    fill='toself',
                    name='Skor Kesiapan',
                    line_color='indigo'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])))
                st.plotly_chart(fig_radar, use_container_width=True)
                
            # INTERPRETASI CERDAS
            with col2:
                st.subheader("Hasil Interpretasi")
                st.metric(label="Skor Komposit SDI-RI", value=f"{skor_akhir:.2f} / 100")
                
                if skor_akhir <= 40:
                    kategori, warna = "Rendah", "🔴"
                elif skor_akhir <= 60:
                    kategori, warna = "Sedang", "🟡"
                elif skor_akhir <= 80:
                    kategori, warna = "Tinggi", "🟢"
                else:
                    kategori, warna = "Sangat Tinggi", "🔵"
                    
                st.info(f"{warna} Berdasarkan perhitungan bobot saat ini, tingkat kesiapan Infrastruktur Data Spasial berada pada kategori **{kategori}**.")
                
                dimensi_terendah = min(rata_dimensi, key=rata_dimensi.get)
                skor_terendah = rata_dimensi[dimensi_terendah]
                st.warning(f"⚠️ **Prioritas Perbaikan:** Dimensi **{dimensi_terendah}** memiliki skor rata-rata terendah ({skor_terendah:.2f}).")
else:
    st.info("Silakan unggah file dataset Anda terlebih dahulu untuk memulai.")