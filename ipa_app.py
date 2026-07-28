import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul IPA", layout="wide")
st.title("Importance-Performance Analysis (IPA)")
st.markdown("Unggah dataset matriks Kinerja dan Kepentingan Anda. Pastikan baris hanya berisi data responden (hapus baris 'Total' atau 'Rata-rata' di tabel interaktif jika ada).")

# 1. FITUR UNGGAH FILE
file_ipa = st.file_uploader("1. Unggah Data IPA (.xlsx / .csv)", type=["xlsx", "csv"])

if file_ipa is not None:
    if file_ipa.name.endswith('.xlsx'):
        df_awal = pd.read_excel(file_ipa)
    else:
        df_awal = pd.read_csv(file_ipa)
    st.success(f"File '{file_ipa.name}' berhasil dimuat!")

    # 2. TABEL INTERAKTIF
    st.write("**2. Tabel Data Interaktif**")
    st.caption("Tips: Jika di bagian bawah tabel Anda terdapat baris 'Total Skor' atau 'Rata-rata', silakan blok baris tersebut dan tekan tombol 'Delete' di keyboard agar tidak mengganggu perhitungan rata-rata otomatis sistem.")
    df_ipa = st.data_editor(df_awal, num_rows="dynamic", use_container_width=True)
    
    st.divider()

    # MENGAMBIL HANYA KOLOM ANGKA
    kolom_angka = df_ipa.select_dtypes(include=['number']).columns.tolist()

    # 3. PEMETAAN KOLOM BERPASANGAN
    st.subheader("3. Pemetaan Variabel Kuadran (Berpasangan)")
    st.write("Pilih secara berurutan: semua kolom Kinerja (X), lalu semua kolom Kepentingan (Y). Pastikan jumlah dan urutannya sama.")
    
    col_m1, col_m2 = st.columns(2)
    kinerja_cols = col_m1.multiselect("Pilih SEMUA Kolom Skor Kinerja (Sumbu X):", kolom_angka)
    kepentingan_cols = col_m2.multiselect("Pilih SEMUA Kolom Skor Kepentingan (Sumbu Y):", kolom_angka)

    # 4. TOMBOL EKSEKUSI
    if st.button("Proses Analisis IPA", type="primary"):
        # Validasi jumlah kolom
        if len(kinerja_cols) == 0 or len(kepentingan_cols) == 0:
            st.error("Gagal diproses! Pilih minimal satu pasang kolom Kinerja dan Kepentingan.")
        elif len(kinerja_cols) != len(kepentingan_cols):
            st.error(f"Gagal diproses! Jumlah kolom tidak seimbang (Anda memilih {len(kinerja_cols)} Kinerja dan {len(kepentingan_cols)} Kepentingan).")
        else:
            # Merakit ulang tabel melebar menjadi tabel memanjang di memori sistem
            indikator_names = []
            kinerja_means = []
            kepentingan_means = []
            
            for i in range(len(kinerja_cols)):
                # Membersihkan nama kolom secara otomatis untuk dijadikan label grafik
                nama_mentah = kinerja_cols[i]
                nama_bersih = nama_mentah.replace("Kinerja", "").replace("(X)", "").replace("-", "").strip()
                if not nama_bersih:
                    nama_bersih = f"Indikator {i+1}"
                    
                indikator_names.append(nama_bersih)
                kinerja_means.append(df_ipa[kinerja_cols[i]].mean())
                kepentingan_means.append(df_ipa[kepentingan_cols[i]].mean())
                
            # Membuat dataframe baru khusus untuk Plotly
            df_plot = pd.DataFrame({
                'Indikator': indikator_names,
                'Kinerja': kinerja_means,
                'Kepentingan': kepentingan_means
            })
            
            # Menentukan titik potong silang sumbu
            mean_x = df_plot['Kinerja'].mean()
            mean_y = df_plot['Kepentingan'].mean()
            
            st.divider()
            
            # 5. VISUALISASI KUADRAN KARTESIUS
            fig_ipa = px.scatter(df_plot, x='Kinerja', y='Kepentingan', text='Indikator')
            fig_ipa.add_hline(y=mean_y, line_dash="dot", line_color="red", annotation_text="Rata-rata Kepentingan")
            fig_ipa.add_vline(x=mean_x, line_dash="dot", line_color="red", annotation_text="Rata-rata Kinerja")
            fig_ipa.update_traces(textposition='top center', marker=dict(size=12, color='royalblue'))
            fig_ipa.update_layout(height=600, title="Diagram Kuadran Prioritas Kebijakan")
            
            st.plotly_chart(fig_ipa, use_container_width=True)
            
            # 6. INTERPRETASI CERDAS
            st.subheader("Rekomendasi Kebijakan Berdasarkan Kuadran")
            
            kuadran_1 = df_plot[(df_plot['Kinerja'] < mean_x) & (df_plot['Kepentingan'] > mean_y)]['Indikator'].tolist()
            kuadran_2 = df_plot[(df_plot['Kinerja'] >= mean_x) & (df_plot['Kepentingan'] > mean_y)]['Indikator'].tolist()
            kuadran_3 = df_plot[(df_plot['Kinerja'] < mean_x) & (df_plot['Kepentingan'] <= mean_y)]['Indikator'].tolist()
            kuadran_4 = df_plot[(df_plot['Kinerja'] >= mean_x) & (df_plot['Kepentingan'] <= mean_y)]['Indikator'].tolist()
            
            col_q1, col_q2 = st.columns(2)
            col_q3, col_q4 = st.columns(2)
            
            with col_q1:
                st.error(f"🚨 **Kuadran I (Prioritas Utama)**\n\nKinerja rendah, kepentingan tinggi:\n- " + "\n- ".join(kuadran_1) if kuadran_1 else "🚨 **Kuadran I (Prioritas Utama)**\n\n- (Kosong)")
            with col_q2:
                st.success(f"🌟 **Kuadran II (Pertahankan Prestasi)**\n\nKinerja tinggi, kepentingan tinggi:\n- " + "\n- ".join(kuadran_2) if kuadran_2 else "🌟 **Kuadran II (Pertahankan Prestasi)**\n\n- (Kosong)")
            with col_q3:
                st.warning(f"⚠️ **Kuadran III (Prioritas Rendah)**\n\nKinerja rendah, kepentingan rendah:\n- " + "\n- ".join(kuadran_3) if kuadran_3 else "⚠️ **Kuadran III (Prioritas Rendah)**\n\n- (Kosong)")
            with col_q4:
                st.info(f"💡 **Kuadran IV (Berlebihan)**\n\nKinerja tinggi, kepentingan rendah:\n- " + "\n- ".join(kuadran_4) if kuadran_4 else "💡 **Kuadran IV (Berlebihan)**\n\n- (Kosong)")
else:
    st.info("Silakan unggah dataset IPA Anda untuk memulai.")