import streamlit as st
import pandas as pd
import requests
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

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

def remover_artigos(titulo):
    artigos = ["O ", "A ", "OS ", "AS ", "UM ", "UMA ", "THE ", "AN "]
    for art in artigos:
        if titulo.upper().startswith(art):
            return titulo[len(art):]
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
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo.strip(), "match": "contains", "limit": 10, "type": "descriptor"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        return [f"{i.get('resource', '').split('/')[-1]} | {i.get('label')}" for i in resp.json()] if resp.status_code == 200 else []
    except: return []

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

titulo = st.text_input("Título da obra:")
titulo_original = st.text_input("Título original (se traduzida):")
classe_principal = st.text_input("Classe principal (Ex: 610):")
volumes = st.text_input("Volume ou Edição:")
isbn = st.text_input("ISBN:")
paginas = st.text_input("Páginas:")
cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")

# Autores e Colaboradores
st.write("### 👥 Autores")
if st.button("➕ Adicionar Autor"): st.session_state.autores.append("")
for i, aut in enumerate(st.session_state.autores):
    c1, c2 = st.columns([8, 1])
    with c1: st.session_state.autores[i] = st.text_input(f"Autor {i+1}", value=aut, key=f"aut_{i}")
    with c2:
        if st.button("❌", key=f"del_aut_{i}") and len(st.session_state.autores) > 1:
            st.session_state.autores.pop(i); st.rerun()

st.write("### ✍️ Colaboradores")
if st.button("➕ Adicionar Colaborador"): st.session_state.colaboradores.append({"nome": "", "tipo": "trad."})
for i, colab in enumerate(st.session_state.colaboradores):
    c1, c2, c3 = st.columns([4, 3, 1])
    with c1: colab["nome"] = st.text_input("Nome", value=colab["nome"], key=f"colab_nome_{i}")
    with c2: colab["tipo"] = st.selectbox("Função", ["trad.", "org.", "comp."], key=f"colab_tipo_{i}")
    with c3:
        if st.button("❌", key=f"del_colab_{i}"): st.session_state.colaboradores.pop(i); st.rerun()

# MeSH
st.write("### 🔍 Pesquisa MeSH")
termo_mesh = st.text_input("Buscar Descritor MeSH:")
if st.button("Consultar NLM"): st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
escolha = st.selectbox("Selecione:", ["-- Escolha --"] + st.session_state.opcoes_mesh)
if st.button("Adicionar descritor à ficha"):
    if escolha != "-- Escolha --": st.session_state.lista_assuntos.append(escolha.split(" | ")[1].strip()); st.rerun()
st.write("#### Descritores Escolhidos:", ", ".join(list(dict.fromkeys(st.session_state.lista_assuntos))))

# --- LÓGICA DE DADOS ---
def get_ficha_data():
    autores_v = [a for a in st.session_state.autores if a.strip()]
    entrada = formatar_entrada_autor(autores_v[0]) if autores_v else "AUTOR NÃO INFORMADO"
    sobrenome_letra = autores_v[0].split()[-1][0].upper() if autores_v else "A"
    cutter_id = calcular_cutter(autores_v[0]) if autores_v else "000"
    primeira_letra_titulo = remover_artigos(titulo)[0].lower() if titulo else "a"
    classificacao_cutter = f"{sobrenome_letra}{cutter_id}{primeira_letra_titulo}"
    
    assuntos = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(dict.fromkeys(st.session_state.lista_assuntos))]
    entradas = ["I. Título."]
    romanos = ["II.", "III.", "IV.", "V."]
    for i, colab in enumerate(st.session_state.colaboradores):
        if colab["nome"]: entradas.append(f"{romanos[min(i, 3)]} {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")
    
    return entrada, classificacao_cutter, autores_v, assuntos + entradas

# --- PRÉ-VISUALIZAÇÃO ---
entrada, class_cutter, auts, lista_final = get_ficha_data()

# Preparando strings para não imprimir partes vazias caso o usuário não preencha
autores_str = ', '.join(auts) if len(auts) <= 3 else (auts[0] + ' et al.' if len(auts) > 0 else '')
volumes_str = f"{volumes} ; " if volumes else ""
titulo_original_str = f"\nTítulo original: {titulo_original}" if titulo_original else ""

# Visualização da ficha em TEXTO PURO (sem tags HTML)
ficha_texto = f"""{classe_principal}
{class_cutter}

{entrada}.
{titulo} / {autores_str}. – {cidade} : {editora}, {ano}.
{volumes_str}{paginas}.{titulo_original_str}
ISBN {isbn if isbn else "..."}

{' '.join(lista_final)}
"""

st.subheader("👁️ Pré-visualização")
st.text(ficha_texto)

# --- DOWNLOAD WORD ---
if st.button("📥 Gerar Documento Word"):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run(f"{classe_principal}\n{class_cutter}").bold = True
    doc.add_paragraph(f"{entrada}.\n{titulo} / {', '.join(auts)}...")
    doc.add_paragraph(f"{volumes} {paginas}")
    if titulo_original: doc.add_paragraph(f"Título original: {titulo_original}")
    doc.add_paragraph(f"ISBN {isbn}")
    doc.add_paragraph(" ".join(lista_final))
    bio = io.BytesIO()
    doc.save(bio)
    st.download_button("Baixar Agora", data=bio.getvalue(), file_name="ficha.docx")
