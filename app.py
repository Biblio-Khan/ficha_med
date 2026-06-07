import streamlit as st
import requests
import io
from docx import Document

# --- CONFIGURAÇÕES E ESTADO ---
st.set_page_config(page_title="BiblioKhan Editorial", page_icon="🩺", layout="centered")

if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []

# --- FUNÇÕES DE LÓGICA ---
def obter_entrada_autor(autor_str):
    if not autor_str: return "AUTOR NÃO INFORMADO"
    partes = [p.strip() for p in autor_str.split(',')]
    palavras = partes[0].split()
    return f"{palavras[-1].upper()}, {' '.join(palavras[:-1])}" if len(palavras) > 1 else partes[0].upper()

@st.cache_data(ttl=3600)
def buscar_descritores_mesh(termo_busca):
    if not termo_busca or len(termo_busca) < 3: return []
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo_busca.strip(), "match": "contains", "limit": 10, "type": "descriptor"}
    headers = {"User-Agent": "BiblioKhanMedicalBot/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        return [f"{item.get('resource', '').split('/')[-1]} | {item.get('label')}" for item in resp.json()] if resp.status_code == 200 else []
    except: return []

def gerar_docx(html_content, autor, titulo):
    doc = Document()
    doc.add_heading('Ficha Catalográfica', 0)
    doc.add_paragraph(f"Entrada: {autor} - {titulo}")
    doc.add_paragraph(html_content.replace('<p style="text-indent: 30px;">', '\n    ').replace('<p>', '\n'))
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- INTERFACE ---
st.title("🩺 BiblioKhan — Módulo de Saúde")

col1, col2 = st.columns(2)
with col1:
    titulo = st.text_input("Título:")
    autor = st.text_input("Autor:")
    cidade = st.text_input("Cidade:")
    editora = st.text_input("Editora:")
with col2:
    ano = st.text_input("Ano:")
    paginas = st.text_input("Páginas:")
    dimensoes = st.text_input("Dimensões:")
    tipo_class = st.selectbox("Classificação:", ["NLM", "CDD", "CDU"])
    num_class = st.text_input("Código de Classificação:")

st.write("---")
termo_mesh = st.text_input("Buscar Descritor MeSH:")
if st.button("Consultar NLM"):
    st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)

escolha = st.selectbox("Selecione o descritor:", ["-- Selecione --"] + st.session_state.opcoes_mesh)
subdivisao = st.text_input("Subdivisão do Assunto (Opcional, ex: -- História):")

# --- GERAÇÃO AACR2 ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    descritor = escolha.split(" | ")[1].strip() if " | " in escolha else ""
    assunto_principal = f"{descritor.capitalize()}{subdivisao.strip()}" if descritor else "Medicina"
    
    # Lógica de assuntos numerados
    assuntos_final = f"1. {assunto_principal}. 2. Saúde. I. Título."
    
    entrada_autor = obter_entrada_autor(autor)
    linha_titulo = f"{titulo} / {autor}"
    imprenta = f"{cidade or '[s.l.]'} : {editora or '[s.n.]'}, {ano or '[s.d.]'}."
    
    html_ficha = (
        f'<div style="border: 1px solid #000; padding: 20px; font-family: monospace;">'
        f'<p><b>{entrada_autor}.</b></p>'
        f'<p style="text-indent: 30px;">{linha_titulo}. – {imprenta}</p>'
        f'<p style="text-indent: 30px;">{paginas} ; {dimensoes}</p>'
        f'<p style="text-indent: 30px;">{assuntos_final}</p>'
        f'<div style="text-align: right;">{tipo_class}: {num_class}</div>'
        f'</div>'
    )
    
    st.markdown(html_ficha, unsafe_allow_html=True)
    st.download_button("📥 Baixar em Word (.docx)", data=gerar_docx(html_ficha, entrada_autor, titulo), 
                       file_name="ficha_catalografica.docx")
