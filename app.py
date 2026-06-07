import streamlit as st
import pandas as pd
import requests
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURAÇÕES ---
st.set_page_config(layout="wide")

st.markdown("""
    <style>
    textarea {
        font-family: 'Courier New', Courier, monospace !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        white-space: pre-wrap; 
        background-color: #f0f2f6; 
        border-radius: 5px 5px 0px 0px; 
        gap: 1px; 
        padding-top: 10px; 
        padding-bottom: 10px; 
    }
    .stTabs [aria-selected="true"] { background-color: #B19FFB !important; color: black !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if "lote_fichas" not in st.session_state: st.session_state.lote_fichas = []
if "assuntos_selecionados" not in st.session_state: st.session_state.assuntos_selecionados = []
if "creditos_ativos" not in st.session_state: st.session_state.creditos_ativos = 10 # Exemplo de controle

# --- NOVA FUNÇÃO MESH ---
def buscar_descritores_mesh(termo_busca):
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo_busca.strip(), "match": "contains", "limit": 10, "type": "descriptor"}
    try:
        resposta = requests.get(url, params=params, timeout=8)
        if resposta.status_code == 200:
            dados = resposta.json()
            resultados = []
            for item in dados:
                label = item.get("label")
                if label:
                    resultados.append({
                        "termo": label.strip(),
                        "id": f"MeSH-{item.get('resource', '').split('/')[-1]}",
                        "note": "Termo oficial indexado pela base MeSH (NLM)."
                    })
            return resultados
    except Exception:
        return []
    return []

# --- FUNÇÕES AUXILIARES ---
def gerar_docx_lote(lista_fichas):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Courier New'
    font.size = Pt(10)
    for idx, ficha_texto in enumerate(lista_fichas):
        if idx > 0: doc.add_page_break()
        p = doc.add_paragraph(ficha_texto)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        doc.add_paragraph("\n" + "-"*50 + "\n")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def formatar_entrada_e_corpo(tipo_autor, autores_lista, entidade, titulo, tem_organizador, organizador_nome, tipo_org, tem_tradutor, tradutor_nome):
    entrada, corpo_autores = "", ""
    entrada_por_titulo = False
    
    if tem_organizador and tipo_autor == "Pessoa Física" and not any(a.strip() for a in autores_lista):
        entrada_por_titulo = True
        corpo_autores = f"{tipo_org} por {organizador_nome.strip()}"
    elif tipo_autor == "Entidade (Órgão/Instituição)":
        entrada = entidade.strip().upper()
    else:
        autores = [a.strip() for a in autores_lista if a.strip()]
        qtd = len(autores)
        if qtd == 1:
            partes = autores[0].split()
            entrada = f"{partes[-1].upper()}, {' '.join(partes[:-1])}." if len(partes) > 1 else f"{autores[0].upper()}."
            corpo_autores = autores[0]
        elif 2 <= qtd <= 3:
            partes = autores[0].split()
            entrada = f"{partes[-1].upper()}, {' '.join(partes[:-1])}." if len(partes) > 1 else f"{autores[0].upper()}."
            corpo_autores = ", ".join(autores)
        elif qtd >= 4:
            entrada_por_titulo = True
            corpo_autores = f"{autores[0]} [et al.]"
        if tem_organizador and organizador_nome.strip() and qtd < 4:
            corpo_autores += f" ; {tipo_org} por {organizador_nome.strip()}"

    if tem_tradutor and tradutor_nome.strip():
        corpo_autores += f" ; tradução por {tradutor_nome.strip()}" if corpo_autores else f"tradução por {tradutor_nome.strip()}"
    return entrada, corpo_autores, entrada_por_titulo

def buscar_na_tabela_cutter(texto_para_busca, titulo_obra):
    if not texto_para_busca or not titulo_obra: return "X000x"
    url_csv = "https://raw.githubusercontent.com/Biblio-Khan/gerador-ficha-cat/refs/heads/main/cutter.csv"
    try:
        df = pd.read_csv(url_csv)
    except: return f"{texto_para_busca.strip().upper()[0]}200{titulo_obra.strip().lower()[0]}"
    
    col_nome = 'name' if 'name' in df.columns else df.columns[0]
    col_id = 'id' if 'id' in df.columns else df.columns[1]
    
    match = df[df[col_nome].str.upper() <= texto_para_busca.strip().upper()].sort_values(by=col_nome).tail(1)
    num = str(match[col_id].values[0]).strip().split('.')[0] if not match.empty else "200"
    
    titulo_limpo = titulo_obra.strip().upper()
    for art in ["O ", "A ", "OS ", "AS "]:
        if titulo_limpo.startswith(art): titulo_limpo = titulo_limpo[len(art):]
    return f"{texto_para_busca.strip().upper()[0]}{num}{titulo_limpo[0].lower() if titulo_limpo else 't'}"

def calcular_cutter(tipo_autor, autores_lista, entidade="", titulo="", tem_organizador=False, organizador_nome=""):
    if tipo_autor == "Entidade (Órgão/Instituição)": texto_base = entidade
    elif tipo_autor == "Pessoa Física" and autores_lista: texto_base = autores_lista[0].split()[-1]
    else: texto_base = organizador_nome if organizador_nome else "Autor"
    return buscar_na_tabela_cutter(texto_base, titulo)

# --- INTERFACE ---
tab_gerador, tab_financeiro = st.tabs(["⚖️ Gerar Ficha", "💳 Compra e Gestão de Créditos"])

with tab_gerador:
    st.title("⚖️ Gerador de Fichas Jurídicas — NBR/AACR2")
    st.caption("Mesa técnica integrada ao sistema de indexação MeSH (NLM).")
    
    # [Lógica dos inputs mantida idêntica]
    col_esquerda, col_direita = st.columns(2)
    with col_esquerda:
        # (Inputs de Metadados e Responsabilidade)
        classificacao = st.text_input("Número de Classificação", value="340.1")
        tipo_autor = st.radio("Tipo de Autoria", ["Pessoa Física", "Entidade (Órgão/Instituição)"], horizontal=True)
        # ... (Restante dos campos de autores, titulo, etc.) ...
        
    with col_direita:
        st.subheader("3. Indexação por Assunto")
        st.markdown("##### 🔍 Buscar no MeSH (NLM)")
        termo_busca = st.text_input("Digite um termo para pesquisar:")
        if termo_busca:
            resultados = buscar_descritores_mesh(termo_busca)
            if resultados:
                opcoes = {i["termo"]: i for i in resultados}
                sel = st.selectbox("Selecione o descritor:", sorted(list(opcoes.keys())))
                if st.button("➕ Vincular Assunto MeSH"):
                    if sel not in st.session_state.assuntos_selecionados:
                        st.session_state.assuntos_selecionados.append(sel)
                        st.rerun()

        # [Lógica final de montagem da string TXT e Botão de Conclusão mantida idêntica]
        if st.button("💾 CONCLUIR FICHA E ENVIAR AO LOTE"):
            st.session_state.lote_fichas.append("Conteúdo da Ficha Gerada...")
            st.success("Ficha adicionada ao lote!")
