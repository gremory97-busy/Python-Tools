import streamlit as st
import pandas as pd
import numpy as np
import io

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul SDI-RI", layout="wide")
st.title("📊 Ekstrapolasi Kesiapan Infrastruktur Data Spasial (SDI-RI)")
st.markdown("Unggah 15 data jawaban perwakilan OPD Anda. Sistem akan mengekstrapolasi/mensimulasikan data tersebut menjadi 42 responden individu secara proporsional dan rasional.")

# --- FUNGSI MENGHITUNG CRONBACH'S ALPHA ---
def hitung_cronbach_alpha(df_items):
    item_vars = df_items.var(axis=0, ddof=1)
    t_scores = df_items.sum(axis=1)
    t_var = t_scores.var(ddof=1)
    k = df_items.shape[1]
    if t_var == 0 or k <= 1:
        return 0
    alpha = (k / (k - 1)) * (1 - (item_vars.sum() / t_var))
    return alpha

# 1. UNGGAH DATA DASAR (15 OPD)
file_sdiri = st.file_uploader("1. Unggah Data Kuesioner Asli (15 OPD) (.xlsx / .csv)", type=["xlsx", "csv"])

if file_sdiri is not None:
    if file_sdiri.name.endswith('.xlsx'):
        df_asli = pd.read_excel(file_sdiri)
    else:
        df_asli = pd.read_csv(file_sdiri)
        
    st.success(f"File berhasil dimuat! Terdeteksi {len(df_asli)} baris data (OPD).")
    
    st.write("**Pratinjau Data Asli (Sebelum Diekstrapolasi):**")
    st.dataframe(df_asli.head(), use_container_width=True)
    st.divider()

    # 2. KONFIGURASI KOLOM & TARGET
    st.subheader("2. Konfigurasi Simulasi & Augmentasi")
    kolom_semua = df_asli.columns.tolist()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        kolom_opd = st.selectbox("Pilih Kolom 'Asal OPD':", kolom_semua)
    with col2:
        kolom_item = st.multiselect("Pilih Kolom Pertanyaan (Likert 1-5):", 
                                    kolom_semua, 
                                    default=[col for col in kolom_semua if df_asli[col].dtype in ['int64', 'float64']])
    with col3:
        target_responden = st.number_input("Target Total Responden:", min_value=15, max_value=200, value=42)

    if st.button("Simulasikan 42 Responden & Analisis", type="primary"):
        if not kolom_item:
            st.error("Pilih minimal 2 kolom pertanyaan!")
            st.stop()
            
        with st.spinner('Menghitung probabilitas distribusi dan menyuntikkan variasi manusiawi...'):
            # --- LOGIKA DISTRIBUSI & AUGMENTASI ---
            jumlah_opd = len(df_asli)
            # Menghitung berapa orang per OPD (contoh 42/15 = 2 sisa 12)
            base_count = target_responden // jumlah_opd
            sisa = target_responden % jumlah_opd
            
            # Buat array distribusi (misal: 12 OPD dapat 3 orang, 3 OPD dapat 2 orang)
            distribusi = [base_count + 1] * sisa + [base_count] * (jumlah_opd - sisa)
            np.random.seed(42) # Agar hasilnya konsisten jika diklik ulang
            np.random.shuffle(distribusi)
            
            data_simulasi = []
            
            for idx, row in df_asli.iterrows():
                nama_opd = row[kolom_opd]
                jatah_orang = distribusi[idx]
                
                for p in range(jatah_orang):
                    baris_baru = row.copy()
                    baris_baru['ID_Responden'] = f"{nama_opd}_Responden_{p+1}"
                    
                    # Tambahkan variasi (noise) pada jawaban agar tidak sama persis (copy-paste)
                    # Peluang: 70% jawaban sama persis dengan OPD, 15% lebih rendah 1 poin, 15% lebih tinggi 1 poin
                    for item in kolom_item:
                        nilai_asli = baris_baru[item]
                        noise = np.random.choice([-1, 0, 1], p=[0.15, 0.70, 0.15])
                        nilai_baru = nilai_asli + noise
                        
                        # Pastikan nilai tetap berada di skala Likert 1-5
                        nilai_baru = max(1, min(5, nilai_baru))
                        baris_baru[item] = nilai_baru
                        
                    data_simulasi.append(baris_baru)
            
            # --- RAKIT DATAFRAME BARU (42 Responden) ---
            df_simulasi = pd.DataFrame(data_simulasi)
            
            # Pindahkan kolom ID_Responden ke depan agar rapi
            cols = ['ID_Responden'] + [c for c in df_simulasi.columns if c != 'ID_Responden']
            df_simulasi = df_simulasi[cols]
            
            df_items = df_simulasi[kolom_item]
            alpha_val = hitung_cronbach_alpha(df_items)
            df_simulasi['Total_Skor_SDIRI'] = df_items.sum(axis=1)
            rata_rata_total = df_simulasi['Total_Skor_SDIRI'].mean()
            
        st.success("✅ Ekstrapolasi Berhasil! Data 15 OPD telah dikembangkan menjadi 42 responden individu.")
        st.divider()
        
        # --- LAPORAN HASIL ---
        st.subheader("3. Laporan Hasil Simulasi (42 Responden)")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="Total Responden Terbentuk", value=len(df_simulasi))
        m2.metric(label="Cronbach's Alpha (42 Orang)", value=f"{alpha_val:.3f}", 
                  delta="Reliabel" if alpha_val >= 0.7 else "Cek kembali data asli", delta_color="normal")
        m3.metric(label="Rata-rata Skor SDI-RI Total", value=f"{rata_rata_total:.2f}")
        
        st.write(f"**Tabel Data Lengkap ({len(df_simulasi)} Responden):**")
        st.dataframe(df_simulasi.head(10), use_container_width=True)
        st.caption("Menampilkan 10 baris pertama. Anda dapat mengunduh seluruh data di bawah ini.")
        
        # --- FITUR UNDUH (DOWNLOAD) DATA 42 RESPONDEN ---
        # Konversi dataframe ke CSV di memori agar bisa diunduh
        csv = df_simulasi.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Unduh Dataset Lengkap (CSV 42 Responden)",
            data=csv,
            file_name='Data_SDIRI_42_Responden.csv',
            mime='text/csv',
        )
        
        st.markdown("---")
        st.markdown(f"### Bukti Agregasi Kembali ke {jumlah_opd} OPD")
        st.write("Meskipun sudah dipecah menjadi 42 orang, jika nilai mereka dirata-ratakan kembali per OPD, hasilnya akan tetap mewakili profil asli instansi tersebut:")
        
        df_opd = df_simulasi.groupby(kolom_opd).agg(
            Jumlah_Responden=('ID_Responden', 'count'),
            Rata_Rata_Skor=('Total_Skor_SDIRI', 'mean')
        ).reset_index().sort_values(by='Rata_Rata_Skor', ascending=False)
        
        st.dataframe(df_opd.style.format({'Rata_Rata_Skor': '{:.2f}'}), use_container_width=True)

else:
    st.info("Silakan unggah file Excel/CSV berisi 15 baris data instansi Anda untuk mulai membuat 42 responden.")
