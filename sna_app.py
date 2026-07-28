import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul SNA Interaktif", layout="wide")
st.title("Social Network Analysis (SNA) Kolaborasi Geospasial")
st.markdown("Unggah matriks, atur layout profesional, geser titik secara manual, dan klik untuk melihat efek garis menyala (glowing edges).")

# 1. FITUR UNGGAH FILE
file_sna = st.file_uploader("1. Unggah Data Matriks SNA (.xlsx / .csv)", type=["xlsx", "csv"])

if file_sna is not None:
    if file_sna.name.endswith('.xlsx'):
        df_awal = pd.read_excel(file_sna)
    else:
        df_awal = pd.read_csv(file_sna)
    st.success(f"File '{file_sna.name}' berhasil dimuat!")

    # 2. TABEL MATRIKS UTAMA
    st.write("**2. Tabel Matriks (Bisa diedit langsung)**")
    df_sna = st.data_editor(df_awal, num_rows="dynamic", use_container_width=True, key="matriks_utama")
    
    st.divider()
    kolom_semua = df_sna.columns.tolist()

    # 3. KONFIGURASI ANALISIS & TATA LETAK (LAYOUT)
    st.subheader("3. Konfigurasi Analisis & Pengaturan Layout Sosiogram")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        kolom_aktor = st.selectbox("Pilih Kolom Nama Instansi (Node):", kolom_semua)
    with col_c2:
        ambang_batas = st.slider("Ambang Batas Interaksi (Biner):", min_value=1, max_value=4, value=3, 
                                 help="Skor di bawah angka ini disaring menjadi 0 (terputus).")
    with col_c3:
        pilihan_layout = st.selectbox("Pola Tata Letak (Algoritma Posisi):", 
                                      ["Kamada-Kawai (Menyebar Merata)", "Circular (Melingkar Sempurna)", "Spring (Alami/Terpusat)", "Shell (Berlapis)"],
                                      help="Pilih pola dasar sosiogram. Anda tetap bisa menggeser titiknya secara manual nanti.")

    jarak_bentang = 0.5
    if pilihan_layout == "Spring (Alami/Terpusat)":
        jarak_bentang = st.slider("Atur Jarak Bentangan Jaringan (Spacing):", min_value=0.1, max_value=2.0, value=0.5, step=0.1)

    # Proses Matriks Biner
    df_matrix = df_sna.set_index(kolom_aktor).select_dtypes(include=['number'])
    if df_matrix.shape[0] == df_matrix.shape[1]:
        df_matrix.columns = df_matrix.index
        df_biner = (df_matrix >= ambang_batas).astype(int)
        G_temp = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
        daftar_node = list(G_temp.nodes())
    else:
        daftar_node = []

    st.divider()

    # 4. PENGATURAN KLASTER KUSTOM
    st.subheader("4. Pengaturan Nama Klaster & Penugasan Anggota")
    st.write("Ubah nama klaster pada tabel ini agar warna kelompok di sosiogram sesuai dengan keinginan Anda.")

    if "df_mapping_cache" not in st.session_state or len(st.session_state["df_mapping_cache"]) != len(daftar_node):
        default_mapping = []
        for node in daftar_node:
            n_lower = str(node).lower()
            if any(k in n_lower for k in ["bappeda", "diskominfotik", "kominfo"]):
                klaster_default = "Hub Sentral"
            elif any(k in n_lower for k in ["pupr", "bpbd", "dlhk", "dishub", "atr", "bpn"]):
                klaster_default = "Klaster Infrastruktur-Lingkungan"
            elif any(k in n_lower for k in ["pariwisata", "pertanian", "bps", "diskan", "disperindag"]):
                klaster_default = "Klaster Ekonomi-Pariwisata"
            else:
                klaster_default = "Simpul Lainnya"
            default_mapping.append({"Instansi": node, "Nama_Klaster": klaster_default})
        st.session_state["df_mapping_cache"] = pd.DataFrame(default_mapping)

    df_mapping_hasil = st.data_editor(st.session_state["df_mapping_cache"], use_container_width=True, key="tabel_mapping")

    st.divider()

    # 5. EKSEKUSI UTAMA (RENDER SOSIOGRAM)
    if st.button("Proses & Render Sosiogram Profesional", type="primary"):
        if df_matrix.shape[0] != df_matrix.shape[1]:
            st.error(f"🚨 Gagal: Matriks tidak simetris! Terdapat {df_matrix.shape[0]} baris dan {df_matrix.shape[1]} kolom.")
            st.stop()
            
        # Graf Utama
        G = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
        G.remove_edges_from(nx.selfloop_edges(G))
        
        # Kalkulasi Metrik (Interpretasi)
        kepadatan = nx.density(G)
        degree_cent = nx.degree_centrality(G)
        between_cent = nx.betweenness_centrality(G)
        closeness_cent = nx.closeness_centrality(G)
        isolates = list(nx.isolates(G))
        
        aktor_utama_degree = max(degree_cent, key=degree_cent.get)
        aktor_utama_between = max(between_cent, key=between_cent.get)
        aktor_utama_closeness = max(closeness_cent, key=closeness_cent.get)
        
        # Mapping Warna
        mapping_dict = dict(zip(df_mapping_hasil["Instansi"], df_mapping_hasil["Nama_Klaster"]))
        unik_klaster = df_mapping_hasil["Nama_Klaster"].unique().tolist()
        
        palet_warna = ['#d62728', '#1f77b4', '#ff7f0e', '#7f7f7f', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
        klaster_ke_warna = {klaster: palet_warna[i % len(palet_warna)] for i, klaster in enumerate(unik_klaster)}

        st.subheader("Peta Jejaring Interaktif Profesional")
        st.info("💡 **INTERAKSI:** (1) Titik akan disusun mengikuti Layout yang dipilih. (2) **Geser** titik manapun untuk memindahkannya permanen tanpa memantul. (3) **Klik** bola instansi untuk melihat efek **garis menyala merah (Glowing Edges)**.")

        # Menghitung Posisi Koordinat Menggunakan NetworkX
        if pilihan_layout == "Spring (Alami/Terpusat)":
            pos = nx.spring_layout(G, seed=42, k=jarak_bentang)
        elif pilihan_layout == "Kamada-Kawai (Menyebar Merata)":
            pos = nx.kamada_kawai_layout(G)
        elif pilihan_layout == "Circular (Melingkar Sempurna)":
            pos = nx.circular_layout(G)
        else:
            pos = nx.shell_layout(G)

        # Membangun Graf Visual (PyVis)
        net = Network(height='650px', width='100%', directed=True, bgcolor='#ffffff', font_color='black')
        
        # Menambahkan Node dengan koordinat tetap dari NetworkX
        for node in G.nodes():
            deg = degree_cent.get(node, 0)
            ukuran_node = int(deg * 50 + 20)
            
            klaster_node = mapping_dict.get(node, "Simpul Lainnya")
            warna_node = klaster_ke_warna.get(klaster_node, '#7f7f7f')
            
            tooltip_text = f"Instansi: {node}\nKlaster: {klaster_node}\nDegree Centrality: {deg:.2f}"
            
            # Koordinat dikalikan 600 agar bentangannya luas di layar
            x_coord = float(pos[node][0]) * 600
            y_coord = float(pos[node][1]) * 600
            
            net.add_node(
                str(node), 
                label=str(node), 
                title=tooltip_text, 
                size=ukuran_node, 
                color=warna_node,
                x=x_coord, 
                y=y_coord
            )

        # Menambahkan Edge (Garis)
        for edge in G.edges():
            net.add_edge(str(edge[0]), str(edge[1]), color='#d3d3d3', width=1.5)

        # Injeksi Pengaturan (Matikan fisika karet, Nyalakan efek Klik Glowing Merah)
        custom_options = """
        var options = {
          "nodes": {
            "borderWidth": 1.5,
            "borderWidthSelected": 4,
            "font": { "size": 14, "face": "arial" }
          },
          "edges": {
            "color": {
              "color": "#e0e0e0",
              "highlight": "#ff4b4b",
              "hover": "#ff4b4b"
            },
            "smooth": {
              "type": "continuous",
              "forceDirection": "none"
            },
            "selectionWidth": 4,
            "hoverWidth": 2
          },
          "interaction": {
            "hover": true,
            "selectConnectedEdges": true
          },
          "physics": {
            "enabled": false
          }
        }
        """
        net.set_options(custom_options)

        # Render HTML ke Streamlit
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_data = f.read()
                
        components.html(html_data, height=680)

        # LEGENDA WARNA
        st.write("**Keterangan Klaster Sosiogram:**")
        cols_legenda = st.columns(len(unik_klaster))
        for i, klaster in enumerate(unik_klaster):
            warna_hex = klaster_ke_warna[klaster]
            cols_legenda[i].markdown(f"<span style='color:{warna_hex}; font-size:20px;'>■</span> **{klaster}**", unsafe_allow_html=True)

        st.divider()
        
        # ==========================================
        # 6. LAPORAN INTERPRETASI HASIL LENGKAP
        # ==========================================
        st.subheader("📑 Laporan Analisis Deskriptif & Celah Hubungan Krusial")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Kepadatan (Density)", f"{kepadatan:.2f}")
        col_m2.metric("Sentralitas Tertinggi", aktor_utama_degree)
        col_m3.metric("Jembatan Data Utama", aktor_utama_between)
        col_m4.metric("Akses Tercepat (Closeness)", aktor_utama_closeness)

        tab1, tab2, tab3 = st.tabs(["💡 Evaluasi Umum & Sentralitas", "🌉 Analisis Celah & Ego Sektoral", "⚠️ Peringatan Simpul & Rekomendasi"])
        
        with tab1:
            st.markdown("### Ringkasan Metrik Sentralitas Aktor")
            st.write(f"1. **Dominasi Sentralitas Derajat (Degree Centrality):** **{aktor_utama_degree}** memegang simpul paling dominan dalam lalu lintas pertukaran data geospasial.")
            st.write(f"2. **Efisiensi Akses Informasi (Closeness Centrality):** **{aktor_utama_closeness}** memiliki kemampuan teoretis terbaik untuk mendistribusikan data ke seluruh instansi dengan jarak terpendek.")
            st.write(f"3. **Peran Mediasi (Betweenness Centrality):** **{aktor_utama_between}** bertindak sebagai penjaga gerbang (*gatekeeper*) atau jembatan utama yang mengontrol arus informasi antar klaster.")

        with tab2:
            st.markdown("### Analisis Celah Hubungan Krusial (*Structural Holes*)")
            st.write(f"Kepadatan jaringan sebesar **{kepadatan:.2f} ({(kepadatan*100):.1f}%)** menunjukkan bahwa struktur jaringan bersifat **jarang (*sparse*)**, di mana sebagian besar instansi sektoral tidak terhubung secara horizontal.")
            
            celah_krusial = []
            nodes_list_eval = list(G.nodes())
            for i in range(len(nodes_list_eval)):
                for j in range(i+1, len(nodes_list_eval)):
                    u = nodes_list_eval[i]
                    v = nodes_list_eval[j]
                    klaster_u = mapping_dict.get(u, "Lainnya")
                    klaster_v = mapping_dict.get(v, "Lainnya")
                    # Mendeteksi missing link jika mereka beda klaster teknis (mengabaikan Hub Sentral)
                    if klaster_u != klaster_v and klaster_u != "Hub Sentral" and klaster_v != "Hub Sentral":
                        if not G.has_edge(u, v) and not G.has_edge(v, u):
                            celah_krusial.append((u, v, klaster_u, klaster_v))
            
            if celah_krusial:
                st.warning(f"⚠️ **Ditemukan {len(celah_krusial)} Celah Hubungan Krusial (Missing Links Lintas Sektor):**")
                st.write("Berikut adalah pasangan instansi dari klaster berbeda yang **tidak memiliki jalur komunikasi langsung**, berpotensi menciptakan silo informasi:")
                
                for idx, (u, v, ku, kv) in enumerate(celah_krusial[:6]):
                    st.markdown(f"- **{u}** (*{ku}*) ❌ **{v}** (*{kv}*)")
                if len(celah_krusial) > 6:
                    st.caption(f"*...dan {len(celah_krusial) - 6} celah lintas sektor lainnya.*")
            else:
                st.success("✅ Tidak ditemukan celah struktural lintas klaster yang signifikan.")

        with tab3:
            st.markdown("### Identifikasi Simpul & Rekomendasi Kebijakan")
            if isolates:
                st.error(f"🚨 **Simpul Terisolasi (*Isolates*):** Instansi berikut tidak memiliki satupun koneksi aktif dalam matriks (Skor biner 0): **{', '.join(isolates)}**.")
            else:
                st.success("✅ Tidak ada simpul yang sepenuhnya terisolasi; semua instansi saling terhubung ke jaringan.")
            
            st.markdown("""
            **Rekomendasi Strategis Tata Kelola GCGM:**
            1. **Desentralisasi Akses Data:** Ketergantungan penuh pada *Hub Sentral* harus dikurangi dengan mengimplementasikan arsitektur *Web API* (Simpul Jaringan) bersama.
            2. **Pembangunan Jembatan Horizontal:** Menutup celah hubungan krusial antar instansi teknis agar koordinasi spasial tidak terus-menerus membebani Bappeda sebagai perantara.
            """)

else:
    st.info("Silakan unggah dataset matriks SNA Anda untuk memulai.")
