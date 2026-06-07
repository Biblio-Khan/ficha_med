import streamlit as st
import requests
import io
from docx import Document

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="centered")

if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = []
if 'autores' not in st.session_state: st.session_state.autores = [""]
if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []

# --- FUNÇÕES ---
def formatar_entrada_autor(nome):
    partes = nome.strip().split()
    return f"{partes[-1].upper()}, {' '.join(partes[:-1])}" if len(partes) > 1 else nome.upper()

@st.cache_data(ttl=3600)
def buscar_descritores_mesh(termo):
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo.strip(), "match": "contains", "limit": 10, "type": "descriptor"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        return [f"{i.get('resource', '').split('/')[-1]} | {i.get('label')}" for i in resp.json()] if resp.status_code == 200 else []
    except: return []

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

titulo = st.text_input("Título da obra:")

st.write("### 👥 Autores")
for i, aut in enumerate(st.session_state.autores):
    c1, c2 = st.columns([8, 1])
    with c1:
        st.session_state.autores[i] = st.text_input(f"Autor {i+1}", value=aut, key=f"aut_{i}")
    with c2:
        if st.button("❌", key=f"del_aut_{i}") and len(st.session_state.autores) > 1:
            st.session_state.autores.pop(i); st.rerun()
if st.button("➕ Adicionar Autor"): st.session_state.autores.append(""); st.rerun()

# (Campos de Publicação e Assuntos...)
cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")
paginas = st.text_input("Páginas:")
num_class = st.text_input("Código de Classificação:")

st.write("### 🔍 Pesquisa MeSH e Assuntos")
termo_mesh = st.text_input("Buscar Descritor MeSH:")
if st.button("Consultar NLM"): st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
escolha = st.selectbox("Selecione:", ["-- Escolha --"] + st.session_state.opcoes_mesh)
if st.button("Adicionar descritor"):
    if escolha != "-- Escolha --": st.session_state.lista_assuntos.append(escolha.split(" | ")[1].strip()); st.rerun()

for i, ass in enumerate(st.session_state.lista_assuntos):
    c1, c2 = st.columns([8, 1])
    with c1: st.session_state.lista_assuntos[i] = st.text_input(f"Assunto {i+1}", value=ass, key=f"ass_{i}")
    with c2: 
        if st.button("❌", key=f"del_ass_{i}"): st.session_state.lista_assuntos.pop(i); st.rerun()

# --- GERAÇÃO AACR2 ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    autores_validos = [a for a in st.session_state.autores if a.strip()]
    num_autores = len(autores_validos)
    
    # Lógica de Entrada Principal
    if num_autores == 0:
        entrada = "AUTOR NÃO INFORMADO"
        resp = ""
    elif num_autores <= 3:
        entrada = formatar_entrada_autor(autores_validos[0])
        resp = ", ".join(autores_validos)
    else:
        entrada = titulo.upper()
        resp = f"{autores_validos[0]} et al."
    
    assuntos_str = " ".join([f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(st.session_state.lista_assuntos)]) + " I. Título."
    imprenta = f"{cidade or '[s.l.]'} : {editora or '[s.n.]'}, {ano or '[s.d.]'}."
    
    html_ficha = f"""
    <div style="border: 1px solid #000; padding: 20px; font-family: monospace;">
        <p><b>{entrada}.</b></p>
        <p style="text-indent: 30px;">{titulo} / {resp}. – {imprenta}</p>
        <p style="text-indent: 30px;">{paginas}.</p>
        <p style="text-indent: 30px;">{assuntos_str}</p>
        <div style="text-align: right;">CDU: {num_class}</div>
    </div>
    """
    st.markdown(html_ficha, unsafe_allow_html=True)
