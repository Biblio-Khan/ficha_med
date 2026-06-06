import streamlit as st
import pandas as pd
import io
import requests
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from deep_translator import GoogleTranslator

# =========================================================================
# 1. CONFIGURAÇÕES TÉCNICAS DA PÁGINA
# =========================================================================
st.set_page_config(
    page_title="Gerador de Fichas Médicas - BiblioKhan",
    layout="wide"
)

st.sidebar.image("logo_bibliokhan.png", use_container_width=True)
with st.sidebar:
    st.title("**BiblioKhan**")
    st.write("**Vocabulário Controlado MeSH & Automação**")
    st.markdown("---")

if "creditos_ativos" not in st.session_state:
    st.session_state["creditos_ativos"] = 10 
if "lote_fichas" not in st.session_state:
    st.session_state.lote_fichas = []
if "assuntos_selecionados" not in st.session_state:
    st.session_state.assuntos_selecionados = []

# =========================================================================
# 2. FUNÇÕES DE APOIO (Cutter, MeSH, Docx)
# =========================================================================
def buscar_termos_mesh_controlado(termo_pt):
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
        url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=mesh&term={termo_en}&retmode=json&retmax=10"
        res_search = requests.get(url_search).json()
        ids = res_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids: return []
        
        url_summary = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=mesh&id={','.join(ids)}&retmode=json"
        res_summary = requests.get(url_summary).json()
        
        termos_validos = []
        for mid in ids:
            titulo_mesh = res_summary.get("result", {}).get(mid, {}).get("term", "")
            if titulo_mesh:
                termos_validos.append(titulo_mesh.upper())
        return list(set(termos_validos))
    except:
        return []

def buscar_na_tabela_cutter(texto_para_busca, titulo_obra):
    if not texto_para_busca or not titulo_obra: return "X000x"
    url_csv = "https://raw.githubusercontent.com/Biblio-Khan/gerador-ficha-cat/refs/heads/main/cutter.csv"
    try:
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip().str.lower()
        col_nome = 'name' if 'name' in df.columns else df.columns[0]
        col_id = 'id' if 'id' in df.columns else df.columns[1]
        df['Name_Clean'] = df[col_nome].astype(str).str.strip().str.upper()
        sub_busca = texto_para_busca.strip().upper()
        match = df[df['Name_Clean'] <= sub_busca].sort_values(by='Name_Clean').tail(1)
        num = str(match[col_id].values[0]).strip().split('.')[0] if not match.empty else "200"
        titulo_limpo = titulo_obra.strip().upper()
        for artigo in ["O ", "A ", "OS ", "AS ", "UM ", "UMA "]:
            if titulo_limpo.startswith(artigo):
                titulo_limpo = titulo_limpo[len(artigo):].strip()
                break
        return f"{sub_busca[0]}{num}{titulo_limpo[0].lower() if titulo_limpo else 't'}"
    except:
        return f"{texto_para_busca.strip().upper()[0]}200{titulo_obra.strip().lower()[0]}"

def calcular_cutter(tipo_autor, autores_lista, entidade="", titulo="", tem_organizador=False, organizador_nome=""):
    if tipo_autor == "Entidade (Órgão/Instituição)" and entidade: 
        texto_base = entidade
    elif tipo_autor == "Pessoa Física" and autores_lista and any(a.strip() for a in autores_lista):
        autor_principal = [a.strip() for a in autores_lista if a.strip()][0]
        partes = autor_principal.split()
        texto_base = partes[-1] if len(partes) > 1 else autor_principal
    elif tem_organizador or tipo_autor == "Organizador":
        partes_org = organizador_nome.strip().split()
        texto_base = partes_org[-1] if len(partes_org) > 1 else organizador_nome
    else: 
        texto_base = "Autor"
    return buscar_na_tabela_cutter(texto_base, titulo)

def gerar_docx_lote(lista_fichas):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Courier New'
    style.font.size = Pt(10)
    for idx, ficha_texto in enumerate(lista_fichas):
        if idx > 0: doc.add_page_break()
        doc.add_paragraph(ficha_texto).alignment = WD_ALIGN_PARAGRAPH.LEFT
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def formatar_entrada_e_corpo(tipo_autor, autores_lista, entidade, titulo, tem_organizador, organizador_nome, tipo_org, tem_tradutor, tradutor_nome):
    entrada, corpo_autores, entrada_por_titulo = "", "", False
    if tipo_autor == "Entidade (Órgão/Instituição)":
        entrada = entidade.strip().upper()
    else:
        autores = [a.strip() for a in autores_lista if a.strip()]
        if autores:
            partes = autores[0].split()
            entrada = f"{partes[-1].upper()}, {' '.join(partes[:-1])}." if len(partes) > 1 else f"{autores[0].upper()}."
            corpo_autores = ", ".join(autores)
        if len(autores) >= 4: entrada_por_titulo = True
    return entrada, corpo_autores, entrada_por_titulo

# =========================================================================
# 3. INTERFACE PRINCIPAL
# =========================================================================
tab_gerador, tab_financeiro = st.tabs(["🏥 Gerar Ficha", "💳 Créditos"])

with tab_gerador:
    col_l, col_r = st.columns(2)
    
    with col_l:
        tipo_autor = st.radio("Tipo de Autoria", ["Pessoa Física", "Entidade (Órgão/Instituição)"], horizontal=True)
        autores_lista = []
        entidade_nome = ""
        if tipo_autor == "Pessoa Física":
            qtd = st.number_input("Qtd Autores", 1, 5, 1)
            for i in range(qtd): autores_lista.append(st.text_input(f"Autor {i+1}"))
        else: entidade_nome = st.text_input("Nome da Entidade")
        
        titulo = st.text_input("Título da Obra")
        classificacao = st.text_input("CDD", value="610")
        
    with col_r:
        st.subheader("Vocabulário Controlado (MeSH)")
        termo_mesh = st.text_input("Buscar termo (MeSH):")
        if termo_mesh:
            termos = buscar_termos_mesh_controlado(termo_mesh)
            if termos:
                selecionado = st.selectbox("Selecione o descritor:", termos)
                if st.button("➕ Adicionar"): st.session_state.assuntos_selecionados.append(selecionado)
        
        for idx, ass in enumerate(st.session_state.assuntos_selecionados):
            st.write(f"{idx+1}. {ass}")

    # Processamento Final
    entrada_p, corpo, por_titulo = formatar_entrada_e_corpo(tipo_autor, autores_lista, entidade_nome, titulo, False, "", "", False, "")
    
    cutter = calcular_cutter(
        tipo_autor=tipo_autor, 
        autores_lista=autores_lista, 
        entidade=entidade_nome, 
        titulo=titulo
    )
    
    txt_ficha = f"{classificacao}\n{cutter} {entrada_p}\n{titulo} / {corpo}."
    st.text_area("Pré-visualização da Ficha:", value=txt_ficha, height=200)

    if st.button("💾 SALVAR FICHA"):
        st.session_state.lote_fichas.append(txt_ficha)
        st.success("Ficha adicionada ao lote!")

with tab_financeiro:
    st.subheader("Envio de Comprovante")
    comprovante = st.file_uploader("Anexe o comprovante", type=["jpg", "png", "pdf"])
    if st.button("Enviar para Liberação"):
        if comprovante:
            # Nota: Substitua o token e chat_id pelos seus valores reais no Secrets
            st.success("Comprovante processado e enviado!")
