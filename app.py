import streamlit as st
import requests
import io
from docx import Document

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="centered")

if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []
if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = [""]

# --- FUNÇÕES ---
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

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

# ... (campos de título, autor, etc permanecem iguais) ...
titulo = st.text_input("Título:")
autor = st.text_input("Autor:")
cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")
paginas = st.text_input("Páginas:")
dimensoes = st.text_input("Dimensões:")
tipo_class = st.selectbox("Classificação:", ["NLM", "CDD", "CDU"])
num_class = st.text_input("Código de Classificação:")

st.write("---")
st.write("### 📝 Assuntos da Ficha")

# Gerenciamento dinâmico de assuntos
for i, assunto in enumerate(st.session_state.lista_assuntos):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.session_state.lista_assuntos[i] = st.text_input(f"Assunto {i+1}", value=assunto, key=f"assunto_{i}")
    with c2:
        if st.button("❌", key=f"del_{i}") and len(st.session_state.lista_assuntos) > 1:
            st.session_state.lista_assuntos.pop(i)
            st.rerun()

if st.button("➕ Adicionar Assunto"):
    st.session_state.lista_assuntos.append("")
    st.rerun()

# Busca MeSH para ajudar a preencher
st.write("---")
termo_mesh = st.text_input("Buscar Descritor MeSH para auxílio:")
if st.button("Consultar NLM"):
    st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)

escolha = st.selectbox("Descritor encontrado:", ["-- Selecione --"] + st.session_state.opcoes_mesh)
if st.button("Adicionar descritor selecionado aos assuntos"):
    if escolha != "-- Selecione --":
        desc = escolha.split(" | ")[1].strip()
        st.session_state.lista_assuntos[-1] = desc
        st.rerun()

# --- GERAÇÃO ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    # Montagem dos assuntos numerados
    assuntos_str = ""
    for idx, ass in enumerate(st.session_state.lista_assuntos):
        if ass.strip():
            assuntos_str += f"{idx+1}. {ass.strip().capitalize()}. "
    assuntos_str += "I. Título."
    
    entrada_autor = obter_entrada_autor(autor)
    linha_titulo = f"{titulo} / {autor}"
    imprenta = f"{cidade or '[s.l.]'} : {editora or '[s.n.]'}, {ano or '[s.d.]'}."
    
    html_ficha = (
        f'<div style="border: 1px solid #000; padding: 20px; font-family: monospace;">'
        f'<p><b>{entrada_autor}.</b></p>'
        f'<p style="text-indent: 30px;">{linha_titulo}. – {imprenta}</p>'
        f'<p style="text-indent: 30px;">{paginas} ; {dimensoes}</p>'
        f'<p style="text-indent: 30px;">{assuntos_str}</p>'
        f'<div style="text-align: right;">{tipo_class}: {num_class}</div>'
        f'</div>'
    )
    st.markdown(html_ficha, unsafe_allow_html=True)
