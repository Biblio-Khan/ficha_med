import streamlit as st
import pandas as pd
import requests
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="wide")

if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = []
if 'autores' not in st.session_state: st.session_state.autores = [""]
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []

# --- FUNÇÕES ---
def formatar_entrada_autor(nome):
    partes = nome.strip().split()
    return f"{partes[-1].upper()}, {' '.join(partes[:-1])}" if len(partes) > 1 else nome.upper()

def remover_artigos(titulo):
    artigos = ["O ", "A ", "OS ", "AS ", "UM ", "UMA ", "THE ", "AN "]
    for art in artigos:
        if titulo.upper().startswith(art): return titulo[len(art):]
    return titulo

def calcular_cutter(nome_autor):
    try:
        df = pd.read_csv("cutter.csv")
        sobrenome = nome_autor.strip().split()[-1].upper()
        for i in range(len(sobrenome), 2, -1):
            tentativa = sobrenome[:i]
            res = df[df["Name"].str.upper() == tentativa]
            if not res.empty: return str(res.iloc[0]["ID"])
        return "????"
    except: return "????"

@st.cache_data(ttl=3600)
def buscar_descritores_mesh(termo):
    url_lookup = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo.strip(), "match": "contains", "limit": 1, "type": "descriptor"}
    try:
        resp = requests.get(url_lookup, params=params, timeout=10)
        if resp.status_code != 200 or not resp.json(): return None
        descriptor_id = resp.json()[0].get('resource', '').split('/')[-1]
        
        url_details = f"https://id.nlm.nih.gov/mesh/lookup/details?descriptor={descriptor_id}"
        resp_details = requests.get(url_details, timeout=10)
        
        if resp_details.status_code == 200:
            data = resp_details.json()
            return {
                "termo_oficial": data.get('label'),
                "sinonimos": [item.get('term') for item in data.get('entryTerms', [])]
            }
        return None
    except: return None

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")
col_esq, col_dir = st.columns([1.5, 1], gap="large")

with col_esq:
    st.subheader("📚 Dados da Obra")
    c_tit1, c_tit2 = st.columns(2)
    with c_tit1: titulo = st.text_input("Título da obra:")
    with c_tit2: titulo_original = st.text_input("Título original:")
    c_pub1, c_pub2, c_pub3 = st.columns(3)
    with c_pub1: cidade = st.text_input("Cidade:")
    with c_pub2: editora = st.text_input("Editora:")
    with c_pub3: ano = st.text_input("Ano:")
    c_desc1, c_desc2, c_desc3, c_desc4 = st.columns(4)
    with c_desc1: volumes = st.text_input("Volume/Edição:")
    with c_desc2: paginas = st.text_input("Páginas:")
    with c_desc3: isbn = st.text_input("ISBN:")
    with c_desc4: classe_principal = st.text_input("Classe Principal (Ex: 610):")
    colecao_serie = st.text_input("Coleção ou Série:")

    # --- BUSCA MESH ---
    termo_busca = st.text_input("Buscar termo no MeSH:")
    if termo_busca:
        resultado = buscar_descritores_mesh(termo_busca)
        if resultado:
            st.markdown(f"### 📍 Termo Autorizado: **{resultado['termo_oficial']}**")
            if resultado['sinonimos']:
                with st.expander("📝 Ver sinônimos"):
                    for s in resultado['sinonimos']: st.markdown(f"- {s}")
            if st.button("➕ Adicionar como Assunto"):
                st.session_state.lista_assuntos.append(resultado['termo_oficial'])
                st.rerun()
        else: st.warning("Termo não encontrado.")

    st.caption("**Assuntos:** " + (", ".join(list(dict.fromkeys(st.session_state.lista_assuntos))) if st.session_state.lista_assuntos else "Nenhum."))

# --- LÓGICA E DOWNLOAD ---
# (Aqui você mantém a função get_ficha_data e a parte de geração do Word que você já tinha)
    st.divider()

    st.subheader("👁️ Pré-visualização")
    
    entrada, class_cutter, auts, lista_final = get_ficha_data()

    # Preparando strings
    autores_str = ', '.join(auts) if len(auts) <= 3 else (auts[0] + ' et al.' if len(auts) > 0 else '')
    volumes_str = f"{volumes} ; " if volumes else ""
    titulo_original_str = f"\nTítulo original: {titulo_original}" if titulo_original else ""
    colecao_str = f" ({colecao_serie})" if colecao_serie else ""

    # Espaçamento manual aqui para simular visualmente na tela do Streamlit
    ficha_texto = f"""{classe_principal}
{class_cutter}       {entrada}.
             {titulo} / {autores_str}. – {cidade} : {editora}, {ano}.
             {volumes_str}{paginas}.{colecao_str}{titulo_original_str}
             ISBN {isbn if isbn else "..."}

             {' '.join(lista_final)}
"""

    # Exibe a ficha na tela
    st.markdown(f"```text\n{ficha_texto}\n```")

    # --- DOWNLOAD WORD ---
    st.write("") 
    if st.button("📥 Gerar Documento Word", use_container_width=True):
        doc = Document()
        
        # Cria e centraliza a tabela na página do Word
        table = doc.add_table(rows=1, cols=1)
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        cell = table.cell(0, 0)
        table.columns[0].width = Inches(5.3)
        cell.width = Inches(5.3)
        
        # --- PARÁGRAFO 1: Classe (CDD/CDU) ---
        p0 = cell.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.line_spacing = 1.15
        
        r0 = p0.add_run(classe_principal)
        r0.font.name = 'Arial'
        r0.font.size = Pt(10)
        r0.bold = True
        
        # --- PARÁGRAFO 2: Cutter e Entrada (Autor) na MESMA LINHA ---
        p1 = cell.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = 1.15
        # Define o espaçamento exato da tabulação (Tab) onde começará o nome
        p1.paragraph_format.tab_stops.add_tab_stop(Inches(0.7)) 
        
        r1_cutter = p1.add_run(class_cutter)
        r1_cutter.font.name = 'Arial'
        r1_cutter.font.size = Pt(10)
        r1_cutter.bold = True
        
        p1.add_run("\t") # Pula para a marcação de 0.7 polegadas
        
        r1_ent = p1.add_run(f"{entrada}.")
        r1_ent.font.name = 'Arial'
        r1_ent.font.size = Pt(10)
        
        # --- PARÁGRAFO 3: Restante das informações indentadas embaixo ---
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = 1.15
        # Recuo global de 0.7 polegadas, empurrando todo o texto da descrição para debaixo do Autor
        p2.paragraph_format.left_indent = Inches(0.7) 
        
        corpo_linhas = [
            f"{titulo} / {autores_str}. – {cidade} : {editora}, {ano}.",
            f"{volumes_str}{paginas}.{colecao_str}{titulo_original_str}",
            f"ISBN {isbn if isbn else '...'}",
            "",
            ' '.join(lista_final)
        ]
        
        r2 = p2.add_run("\n".join(corpo_linhas))
        r2.font.name = 'Arial'
        r2.font.size = Pt(10)
                
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button("Baixar Ficha Formatada", data=bio.getvalue(), file_name="ficha_catalografica.docx", use_container_width=True)
