import streamlit as st
import pandas as pd
import io
import requests
from docx import Document

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="centered")

# Inicialização de Estados
if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = []
if 'autores' not in st.session_state: st.session_state.autores = [""]
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []
if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []

# --- FUNÇÕES ---
def formatar_entrada_autor(nome):
    partes = nome.strip().split()
    return f"{partes[-1].upper()}, {' '.join(partes[:-1])}" if len(partes) > 1 else nome.upper()

def calcular_cutter(nome_autor):
    try:
        df = pd.read_csv("cutter.csv")
        sobrenome = nome_autor.strip().split()[-1].upper()
        for i in range(len(sobrenome), 2, -1):
            tentativa = sobrenome[:i]
            res = df[df["Name"].str.upper() == tentativa]
            if not res.empty: return str(res.iloc[0]["ID"])
        return "????"
    except: return "ErroCutter"

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
classe_principal = st.text_input("Classe principal (Ex: 610):")
volumes = st.text_input("Volume ou Edição:")
isbn = st.text_input("ISBN:")
paginas = st.text_input("Páginas:")
cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")

# --- DINÂMICOS ---
st.write("### 👥 Autores")
for i, aut in enumerate(st.session_state.autores):
    c1, c2 = st.columns([8, 1])
    with c1: st.session_state.autores[i] = st.text_input(f"Autor {i+1}", value=aut, key=f"aut_{i}")
    with c2:
        if st.button("❌", key=f"del_aut_{i}") and len(st.session_state.autores) > 1:
            st.session_state.autores.pop(i); st.rerun()
if st.button("➕ Adicionar Autor"): st.session_state.autores.append(""); st.rerun()

st.write("### ✍️ Colaboradores")
if st.button("➕ Adicionar Colaborador"): st.session_state.colaboradores.append({"nome": "", "tipo": "trad."}); st.rerun()
for i, colab in enumerate(st.session_state.colaboradores):
    c1, c2, c3 = st.columns([4, 3, 1])
    with c1: colab["nome"] = st.text_input("Nome", value=colab["nome"], key=f"colab_nome_{i}")
    with c2: colab["tipo"] = st.selectbox("Função", ["trad.", "org.", "comp."], key=f"colab_tipo_{i}")
    with c3:
        if st.button("❌", key=f"del_colab_{i}"): st.session_state.colaboradores.pop(i); st.rerun()

# --- MESH E ASSUNTOS ---
st.write("### 🔍 Pesquisa MeSH")
termo_mesh = st.text_input("Buscar Descritor MeSH:")
if st.button("Consultar NLM"): st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
escolha = st.selectbox("Selecione:", ["-- Escolha --"] + st.session_state.opcoes_mesh)
if st.button("Adicionar descritor à ficha"):
    if escolha != "-- Escolha --": st.session_state.lista_assuntos.append(escolha.split(" | ")[1].strip()); st.rerun()

st.write("### 📝 Lista de Assuntos")
for i, ass in enumerate(st.session_state.lista_assuntos):
    c1, c2 = st.columns([8, 1])
    with c1: st.session_state.lista_assuntos[i] = st.text_input(f"Assunto {i+1}", value=ass, key=f"ass_{i}")
    with c2: 
        if st.button("❌", key=f"del_ass_{i}"): st.session_state.lista_assuntos.pop(i); st.rerun()

# --- GERAÇÃO FINAL ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    autores_v = [a for a in st.session_state.autores if a.strip()]
    entrada = formatar_entrada_autor(autores_v[0]) if len(autores_v) <= 3 else titulo.upper()
    cutter = calcular_cutter(autores_v[0]) if autores_v else "000"
    classificacao = f"{classe_principal} {autores_v[0].split()[-1][0].upper()}{cutter} {ano}"

    # Assuntos (Arábicos) + Título (I.) + Colaboradores (II...)
    lista_final = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(st.session_state.lista_assuntos)]
    lista_final.append("I. Título.")
    romanos_colab = ["II.", "III.", "IV.", "V."]
    for i, colab in enumerate(st.session_state.colaboradores):
        if colab["nome"]:
            lista_final.append(f"{romanos_colab[min(i, 3)]} {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")

    html_ficha = f"""
    <div style="border: 1px solid #000; padding: 20px; font-family: monospace;">
        <p><b>{entrada}.</b></p>
        <p style="text-indent: 30px;">{titulo} / {', '.join(autores_v) if len(autores_v) <= 3 else autores_v[0] + ' et al.'}. – {cidade} : {editora}, {ano}.</p>
        <p style="text-indent: 30px;">{volumes + ' ; ' if volumes else ''}{paginas}.</p>
        <p style="text-indent: 30px;">ISBN {isbn if isbn else "..."}</p>
        <p style="text-indent: 30px;">{' '.join(lista_final)}</p>
        <div style="text-align: right;">{classificacao}</div>
    </div>
    """
    st.markdown(html_ficha, unsafe_allow_html=True)
