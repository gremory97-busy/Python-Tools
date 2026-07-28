import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul SNA Interaktif", layout="wide")
st.title("Social Network Analysis (SNA) Kolaborasi Geospasial")
st.markdown("Unggah matriks relasi Anda. Anda dapat menggeser (drag) titik-titik node secara manual pada sosiogram di bawah.")

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

    # 3. KONFIGURASI MATRIKS & AMBANG BATAS
    st.subheader("3. Konfigurasi Analisis & Transformasi Biner")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        kolom_aktor = st.selectbox("Pilih Kolom Nama Instansi (Node):", kolom_semua)
    with col_c2:
        ambang_batas = st.slider("Ambang Batas Interaksi (Biner):", min_value=1, max_value=4, value=3, 
                                 help="Nilai di bawah angka ini akan disaring menjadi 0 (garis diputus).")

    # Memproses Graf Sementara untuk Mendapatkan Daftar Node
    df_matrix = df_sna.set_index(kolom_aktor).select_dtypes(include=['number'])
    if df_matrix.shape[0] == df_matrix.shape[1]:
        df_matrix.columns = df_matrix.index
        df_biner = (df_matrix >= ambang_batas).astype(int)
        G_temp = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
        daftar_node = list(G_temp.nodes())
    else:
        daftar_node = []

    st.divider()

    # 4. PENGATURAN KLASTER KUSTOM (CUSTOM GROUPING)
    st.subheader("4. Pengaturan Nama Klaster & Penugasan Anggota")
    st.write("Tentukan nama klaster secara bebas pada tabel di bawah ini.")

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

    # 5. TOMBOL EKSEKUSI UTAMA
    if st.button("Proses & Render Sosiogram Interaktif", type="primary"):
        if df_matrix.shape[0] != df_matrix.shape[1]:
            st.error(f"🚨 Gagal: Matriks tidak simetris! Terdapat {df_matrix.shape[0]} baris dan {df_matrix.shape[1]} kolom.")
            st.stop()
            
        G = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
        G.remove_edges_from(nx.selfloop_edges(G))
        
        # Kalkulasi Metrik
        kepadatan = nx.density(G)
        degree_cent = nx.degree_centrality(G)
        between_cent = nx.betweenness_centrality(G)
        
        aktor_utama_degree = max(degree_cent, key=degree_cent.get)
        aktor_utama_between = max(between_cent, key=between_cent.get)
        
        mapping_dict = dict(zip(df_mapping_hasil["Instansi"], df_mapping_hasil["Nama_Klaster"]))
        unik_klaster = df_mapping_hasil["Nama_Klaster"].unique().tolist()
        
        palet_warna = ['#d62728', '#1f77b4', '#ff7f0e', '#7f7f7f', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
        klaster_ke_warna = {klaster: palet_warna[i % len(palet_warna)] for i, klaster in enumerate(unik_klaster)}

        st.subheader("Peta Jejaring Interaktif (Bisa Digeser Manual)")
        st.info("💡 **Petunjuk:** Anda dapat **mengklik dan menyeret (drag-and-drop)** lingkaran instansi mana saja menggunakan kursor mouse untuk mengatur tata letaknya secara manual.")

        # --- MEMBUANG GRAF MENGGUNAKAN PYVIS ---
        # Membuat objek network PyVis (directed=True agar ada panah arah hubungan)
        net = Network(height='650px', width='100%', directed=True, bgcolor='#ffffff', font_color='black')
        
        # Mengaktifkan fisika agar node bisa ditarik dan dilepas stabil
        net.repulsion(node_distance=150, central_gravity=0.3, spring_length=150)

        # Memasukkan Node ke PyVis
        for node in G.nodes():
            deg = degree_cent.get(node, 0)
            ukuran_node = int(deg * 50 + 20) # Ukuran proporsional
            
            klaster_node = mapping_dict.get(node, "Simpul Lainnya")
            warna_node = klaster_ke_warna.get(klaster_node, '#7f7f7f')
            
            tooltip_text = f"Instansi: {node}\\nKlaster: {klaster_node}\\nDegree Centrality: {deg:.2f}"
            
            net.add_node(
                str(node), 
                label=str(node), 
                title=tooltip_text, 
                size=ukuran_node, 
                color=warna_node
            )

        # Memasukkan Edge ke PyVis
        for edge in G.edges():
            net.add_edge(str(edge[0]), str(edge[1]), color='#888888', width=1.5)
# --- MEMBUANG GRAF MENGGUNAKAN PYVIS ---
        net = Network(height='650px', width='100%', directed=True, bgcolor='#ffffff', font_color='black')
        
        # Mengatur konfigurasi dasar
        net.repulsion(node_distance=150, central_gravity=0.3, spring_length=150)

        # Memasukkan Node ke PyVis
        for node in G.nodes():
            deg = degree_cent.get(node, 0)
            ukuran_node = int(deg * 50 + 20)
            
            klaster_node = mapping_dict.get(node, "Simpul Lainnya")
            warna_node = klaster_ke_warna.get(klaster_node, '#7f7f7f')
            
            tooltip_text = f"Instansi: {node}\\nKlaster: {klaster_node}\\nDegree Centrality: {deg:.2f}"
            
            net.add_node(
                str(node), 
                label=str(node), 
                title=tooltip_text, 
                size=ukuran_node, 
                color=warna_node,
                fixed=False # Memastikan node tetap bisa digeser
            )

        # Memasukkan Edge ke PyVis
        for edge in G.edges():
            net.add_edge(str(edge[0]), str(edge[1]), color='#888888', width=1.5)

        # ==========================================
        # MATIKAN FISIKA AGAR TIDAK MEMANTUL SEPERTI KARET
        # ==========================================
        net.toggle_physics(False)
        # ==========================================

        # Menyimpan dan merender HTML interaktif ke Streamlit
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_data = f.read()
                
        components.html(html_data, height=680)
        # Menyimpan dan merender HTML interaktif ke Streamlit
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
        
        # RINGKASAN METRIK
        st.subheader("📑 Ringkasan Metrik Utama")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Kepadatan (Density)", f"{kepadatan:.2f}")
        col_m2.metric("Sentralitas Tertinggi", aktor_utama_degree)
        col_m3.metric("Jembatan Data Utama", aktor_utama_between)

else:
    st.info("Silakan unggah dataset matriks SNA Anda untuk memulai.")
