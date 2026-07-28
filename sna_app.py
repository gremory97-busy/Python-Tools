import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Modul SNA Interaktif", layout="wide", initial_sidebar_state="collapsed")

# --- CSS KHUSUS UNTUK MODE CETAK A4 & RESPONSIVE CONTAINER ---
st.markdown("""
<style>
@media print {
    @page { size: A4 portrait; margin: 15mm; }
    header[data-testid="stHeader"] {display: none !important;}
    footer {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    .stButton {display: none !important;}
    .st-emotion-cache-16txtl3 {padding: 0 !important;}
}
/* Memastikan kotak sosiogram memenuhi 100% ruang yang tersedia */
.graf-container { 
    border: 2px solid #e0e0e0; 
    border-radius: 8px; 
    padding: 10px; 
    background-color: white;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# --- SAKELAR MODE CETAK ---
mode_cetak = st.toggle("🖨️ AKTIFKAN MODE CETAK LAPORAN (A4)", help="Nyalakan ini untuk menyembunyikan semua menu pengaturan. Tampilan akan memanjang ke bawah agar siap di-print/PDF (Tekan Ctrl+P).")

if not mode_cetak:
    st.title("SNA Kolaborasi Geospasial")
    st.markdown("Unggah matriks, atur layout, geser titik, dan dapatkan laporan komprehensif.")

    # 1. FITUR UNGGAH FILE
    file_sna = st.file_uploader("1. Unggah Data Matriks SNA (.xlsx / .csv)", type=["xlsx", "csv"])

    if file_sna is not None:
        if file_sna.name.endswith('.xlsx'):
            df_awal = pd.read_excel(file_sna)
        else:
            df_awal = pd.read_csv(file_sna)
        st.success(f"File '{file_sna.name}' berhasil dimuat!")

        st.write("**2. Tabel Matriks Utama**")
        df_sna = st.data_editor(df_awal, num_rows="dynamic", use_container_width=True)
        
        kolom_semua = df_sna.columns.tolist()

        # 3. KONFIGURASI ANALISIS & TATA LETAK
        st.subheader("3. Konfigurasi Analisis & Pengaturan Layout")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            kolom_aktor = st.selectbox("Pilih Kolom Nama Instansi (Node):", kolom_semua)
        with col_c2:
            ambang_batas = st.slider("Ambang Batas Interaksi (Biner):", min_value=1, max_value=4, value=3)
        with col_c3:
            pilihan_layout = st.selectbox("Pola Tata Letak (Algoritma):", 
                                          ["Kamada-Kawai (Merata)", "Circular (Melingkar)", "Spring (Alami/Pusat)", "Shell (Berlapis)"])

        jarak_bentang = 0.5
        if pilihan_layout == "Spring (Alami/Pusat)":
            jarak_bentang = st.slider("Jarak Bentangan Jaringan:", min_value=0.1, max_value=2.0, value=0.5, step=0.1)

        # Proses Matriks Biner
        df_matrix = df_sna.set_index(kolom_aktor).select_dtypes(include=['number'])
        if df_matrix.shape[0] == df_matrix.shape[1]:
            df_matrix.columns = df_matrix.index
            df_biner = (df_matrix >= ambang_batas).astype(int)
            G_temp = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
            daftar_node = list(G_temp.nodes())
        else:
            daftar_node = []

        # 4. KLASTER KUSTOM
        st.subheader("4. Pengaturan Nama Klaster (Warna)")
        if "df_mapping_cache" not in st.session_state or len(st.session_state["df_mapping_cache"]) != len(daftar_node):
            default_mapping = []
            for node in daftar_node:
                n_lower = str(node).lower()
                if any(k in n_lower for k in ["bappeda", "diskominfotik", "kominfo"]):
                    klaster_default = "Hub Sentral"
                elif any(k in n_lower for k in ["pupr", "bpbd", "dlhk", "dishub", "atr", "bpn"]):
                    klaster_default = "Klaster Infrastruktur"
                elif any(k in n_lower for k in ["pariwisata", "pertanian", "bps", "diskan", "disperindag"]):
                    klaster_default = "Klaster Ekonomi"
                else:
                    klaster_default = "Simpul Lainnya"
                default_mapping.append({"Instansi": node, "Nama_Klaster": klaster_default})
            st.session_state["df_mapping_cache"] = pd.DataFrame(default_mapping)

        df_mapping_hasil = st.data_editor(st.session_state["df_mapping_cache"], use_container_width=True)

        if st.button("Proses & Buat Laporan", type="primary"):
            if df_matrix.shape[0] != df_matrix.shape[1]:
                st.error("🚨 Matriks tidak simetris!")
                st.stop()
            
            # SIMPAN KE SESSION STATE UNTUK CETAK
            st.session_state['data_ready'] = True
            st.session_state['G'] = nx.from_pandas_adjacency(df_biner, create_using=nx.DiGraph)
            st.session_state['G'].remove_edges_from(nx.selfloop_edges(st.session_state['G']))
            st.session_state['df_mapping'] = df_mapping_hasil
            st.session_state['layout'] = pilihan_layout
            st.session_state['spacing'] = jarak_bentang
            st.rerun()

else:
    if 'data_ready' not in st.session_state:
        st.warning("⚠️ Silakan matikan Mode Cetak dan unggah/proses data terlebih dahulu.")
        st.stop()
    st.markdown("<h2 style='text-align: center;'>Laporan Analisis Jaringan Kolaborasi Geospasial</h2>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================
# BAGIAN RENDER UTAMA (DASHBOARD & CETAK)
# ==========================================
if 'data_ready' in st.session_state:
    G = st.session_state['G']
    df_map = st.session_state['df_mapping']
    lay = st.session_state['layout']
    spc = st.session_state['spacing']

    # 1. KALKULASI METRIK
    kepadatan = nx.density(G)
    degree_cent = nx.degree_centrality(G)
    between_cent = nx.betweenness_centrality(G)
    closeness_cent = nx.closeness_centrality(G)
    isolates = list(nx.isolates(G))
    
    aktor_utama_degree = max(degree_cent, key=degree_cent.get) if degree_cent else "-"
    aktor_utama_between = max(between_cent, key=between_cent.get) if between_cent else "-"
    
    mapping_dict = dict(zip(df_map["Instansi"], df_map["Nama_Klaster"]))
    unik_klaster = df_map["Nama_Klaster"].unique().tolist()
    
    palet_warna = ['#d62728', '#1f77b4', '#ff7f0e', '#7f7f7f', '#2ca02c', '#9467bd', '#8c564b', '#e377c2']
    klaster_ke_warna = {klaster: palet_warna[i % len(palet_warna)] for i, klaster in enumerate(unik_klaster)}

    # Membuat Tabel DataFrame Ringkasan Node
    tabel_metrik = []
    for node in G.nodes():
        tabel_metrik.append({
            "Instansi": node,
            "Klaster": mapping_dict.get(node, "Lainnya"),
            "Degree": round(degree_cent.get(node, 0), 2),
            "Betweenness": round(between_cent.get(node, 0), 2),
            "Closeness": round(closeness_cent.get(node, 0), 2)
        })
    df_metrik_node = pd.DataFrame(tabel_metrik).sort_values(by="Degree", ascending=False).reset_index(drop=True)

    # 2. PENGATURAN LAYOUT BERDASARKAN MODE
    if not mode_cetak:
        st.divider()
        # Mengubah rasio agar area grafik (kiri) jauh lebih lebar mengambil ruang kosong
        col_graf, col_info = st.columns([2.8, 1.2], gap="large") 
    else:
        col_graf, col_info = st.columns([1, 0.01])

    # --- RENDER SOSIOGRAM (RESPONSIVE 100%) ---
    with col_graf:
        st.markdown(f"### Sosiogram {'' if mode_cetak else '(Interaktif)'}")
        if not mode_cetak:
            st.caption("✨ Tahan & Geser titik untuk menatanya. Klik titik untuk melihat koneksi menyala.")
            
        if lay == "Spring (Alami/Pusat)":
            pos = nx.spring_layout(G, seed=42, k=spc)
        elif lay == "Kamada-Kawai (Merata)":
            pos = nx.kamada_kawai_layout(G)
        elif lay == "Circular (Melingkar)":
            pos = nx.circular_layout(G)
        else:
            pos = nx.shell_layout(G)

        # PyVis Setup dengan Lebar 100% (Responsive)
        net = Network(height='750px', width='100%', directed=True, bgcolor='#ffffff', font_color='black')
        
        for node in G.nodes():
            deg = degree_cent.get(node, 0)
            ukuran_node = int(deg * 40 + 20)
            klaster_node = mapping_dict.get(node, "Simpul Lainnya")
            warna_node = klaster_ke_warna.get(klaster_node, '#7f7f7f')
            
            label_teks = f"{node}\n(Deg: {deg:.2f})"
            tooltip_text = f"Instansi: {node}\nKlaster: {klaster_node}\nDegree Centrality: {deg:.2f}"
            
            # Rentang koordinat diperbesar agar menyebar ideal di kanvas lebar
            x_coord = float(pos[node][0]) * 700
            y_coord = float(pos[node][1]) * 700
            
            net.add_node(str(node), label=label_teks, title=tooltip_text, size=ukuran_node, color=warna_node, x=x_coord, y=y_coord)

        for edge in G.edges():
            net.add_edge(str(edge[0]), str(edge[1]), color='#d3d3d3', width=1.5)

        custom_options = """
        var options = {
          "nodes": { "borderWidth": 1.5, "borderWidthSelected": 4, "font": { "size": 15, "face": "arial", "multi": true } },
          "edges": { "color": { "color": "#e0e0e0", "highlight": "#ff4b4b", "hover": "#ff4b4b" }, "smooth": { "type": "continuous", "forceDirection": "none" }, "selectionWidth": 4, "hoverWidth": 2 },
          "interaction": { "hover": true, "selectConnectedEdges": true },
          "physics": { "enabled": false }
        }
        """
        net.set_options(custom_options)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            net.save_graph(tmp.name)
            with open(tmp.name, 'r', encoding='utf-8') as f:
                html_data = f.read()
        
        # Bungkus HTML tanpa paksaan ukuran absolut
        st.markdown('<div class="graf-container">', unsafe_allow_html=True)
        # Menghapus argumen width agar menyesuaikan lebar layar secara otomatis
        components.html(html_data, height=760)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RENDER PANEL INFORMASI & LEGENDA ---
    info_container = st.container() if mode_cetak else col_info

    with info_container:
        if mode_cetak: st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Keterangan Klaster")
        for klaster in unik_klaster:
            warna_hex = klaster_ke_warna[klaster]
            st.markdown(f"<span style='color:{warna_hex}; font-size:24px;'>■</span> **{klaster}**", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Metrik Jaringan Utama")
        st.write(f"**Kepadatan (Density):** {kepadatan:.2f}")
        st.write(f"**Sentralitas Tertinggi:** {aktor_utama_degree}")
        st.write(f"**Jembatan Utama (Betweenness):** {aktor_utama_between}")
        
        st.markdown("---")
        st.markdown("### Detail Nilai Aktor (OPD)")
        st.dataframe(df_metrik_node, use_container_width=True, hide_index=True)

    # --- RENDER ANALISIS DESKRIPTIF LANJUTAN ---
    st.divider()
    st.markdown("### 📑 Laporan Analisis Deskriptif & Celah Hubungan Krusial")

    # Logika Celah Struktural
    celah_krusial = []
    nodes_list_eval = list(G.nodes())
    for i in range(len(nodes_list_eval)):
        for j in range(i+1, len(nodes_list_eval)):
            u, v = nodes_list_eval[i], nodes_list_eval[j]
            klaster_u, klaster_v = mapping_dict.get(u, "Lainnya"), mapping_dict.get(v, "Lainnya")
            if klaster_u != klaster_v and klaster_u != "Hub Sentral" and klaster_v != "Hub Sentral":
                if not G.has_edge(u, v) and not G.has_edge(v, u):
                    celah_krusial.append((u, v, klaster_u, klaster_v))

    if not mode_cetak:
        tab1, tab2, tab3 = st.tabs(["💡 Sentralitas", "🌉 Celah & Ego Sektoral", "⚠️ Rekomendasi"])
        
        with tab1:
            st.write(f"**Dominasi Sentralitas:** **{aktor_utama_degree}** memegang simpul paling dominan dalam lalu lintas data.")
            st.write(f"**Peran Mediasi:** **{aktor_utama_between}** bertindak sebagai penjaga gerbang (*gatekeeper*) antar klaster.")

        with tab2:
            st.write(f"Kepadatan jaringan **{kepadatan:.2f} ({(kepadatan*100):.1f}%)** menunjukkan struktur jaringan yang jarang (*sparse*).")
            if celah_krusial:
                st.warning(f"⚠️ **Ditemukan {len(celah_krusial)} Celah Hubungan Krusial (Missing Links Lintas Sektor):**")
                for idx, (u, v, ku, kv) in enumerate(celah_krusial[:10]):
                    st.markdown(f"- **{u}** (*{ku}*) ❌ **{v}** (*{kv}*)")
            else:
                st.success("✅ Tidak ditemukan celah struktural lintas klaster yang signifikan.")

        with tab3:
            if isolates:
                st.error(f"🚨 **Simpul Terisolasi:** {', '.join(isolates)} tidak memiliki koneksi aktif.")
            st.markdown("1. **Desentralisasi Akses Data:** Ketergantungan pada *Hub Sentral* harus dikurangi dengan *Web API* bersama.\n2. **Pembangunan Jembatan Horizontal:** Menutup celah krusial antar instansi teknis.")
    
    else:
        st.markdown("#### A. Evaluasi Sentralitas")
        st.write(f"1. **Dominasi Sentralitas:** **{aktor_utama_degree}** memegang simpul paling dominan dalam lalu lintas pertukaran data.")
        st.write(f"2. **Peran Mediasi:** **{aktor_utama_between}** bertindak sebagai jembatan utama yang mengontrol arus informasi antar klaster.")
        
        st.markdown("#### B. Analisis Celah & Ego Sektoral")
        st.write(f"Kepadatan jaringan **{kepadatan:.2f} ({(kepadatan*100):.1f}%)** menunjukkan struktur jaringan yang jarang (*sparse*).")
        if celah_krusial:
            st.write(f"**Ditemukan {len(celah_krusial)} Celah Hubungan Krusial (Missing Links Lintas Sektor):**")
            for (u, v, ku, kv) in celah_krusial:
                st.write(f"- {u} ({ku}) ❌ {v} ({kv})")
        else:
            st.write("Tidak ditemukan celah struktural lintas klaster.")
            
        st.markdown("#### C. Identifikasi Simpul & Rekomendasi")
        if isolates:
            st.write(f"**Simpul Terisolasi:** {', '.join(isolates)}.")
        st.markdown("1. **Desentralisasi Akses Data:** Ketergantungan pada *Hub Sentral* harus dikurangi dengan *Web API* bersama.\n2. **Pembangunan Jembatan Horizontal:** Menutup celah krusial antar instansi teknis.")
