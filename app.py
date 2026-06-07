import streamlit as st
import requests
import io
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
volumes = st.text_input("Volume ou Edição (Ex: v. 2, 3. ed.):")
isbn = st.text_input("ISBN:")
eh_estrangeiro = st.checkbox("A obra é traduzida (título original diferente)?")
titulo_original = st.text_input("Título original:") if eh_estrangeiro else ""

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

cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")
paginas = st.text_input("Páginas:")
num_class = st.text_input("Código de Classificação:")

st.write("### 🔍 Pesquisa MeSH e Assuntos")
termo_mesh = st.text_input("Buscar Descritor MeSH:")
if st.button("Consultar NLM"): st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
escolha = st.selectbox("Selecione:", ["-- Escolha --"] + st.session_state.opcoes_mesh)
if st.button("Adicionar descritor à ficha"):
    if escolha != "-- Escolha --": st.session_state.lista_assuntos.append(escolha.split(" | ")[1].strip()); st.rerun()

for i, ass in enumerate(st.session_state.lista_assuntos):
    c1, c2 = st.columns([8, 1])
    with c1: st.session_state.lista_assuntos[i] = st.text_input(f"Assunto {i+1}", value=ass, key=f"ass_{i}")
    with c2: 
        if st.button("❌", key=f"del_ass_{i}"): st.session_state.lista_assuntos.pop(i); st.rerun()

# --- GERAÇÃO AACR2 ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    autores_v = [a for a in st.session_state.autores if a.strip()]
    
    # Entrada Principal
    if len(autores_v) == 0: entrada = "AUTOR NÃO INFORMADO"
    elif len(autores_v) <= 3: entrada = formatar_entrada_autor(autores_v[0])
    else: entrada = titulo.upper()
    
    # Assuntos e Entradas Secundárias (Lógica corrigida para numeração romana)
    lista_final = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(st.session_state.lista_assuntos)]
    romanos = ["I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX."]
    
    for colab in st.session_state.colaboradores:
        if colab["nome"]:
            nome_inv = formatar_entrada_autor(colab["nome"])
            idx_r = len(lista_final)
            lista_final.append(f"{romanos[idx_r]} {nome_inv} ({colab['tipo']}).")
    
    lista_final.append(f"{romanos[len(lista_final)]} Título.")
    
    # Descrição Física com ISBN
    desc_fisica = f"{volumes + ' ; ' if volumes else ''}{paginas}."
    
    html_ficha = f"""
    <div style="border: 1px solid #000; padding: 20px; font-family: monospace;">
        <p><b>{entrada}.</b></p>
        <p style="text-indent: 30px;">{titulo} / {', '.join(autores_v) if len(autores_v) <= 3 else autores_v[0] + ' et al.'}. – {cidade or '[s.l.]'} : {editora or '[s.n.]'}, {ano or '[s.d.]'}.</p>
        {'<p style="text-indent: 30px;">Título original: ' + titulo_original + '</p>' if eh_estrangeiro else ''}
        <p style="text-indent: 30px;">{desc_fisica}</p>
        <p style="text-indent: 30px;">ISBN {isbn if isbn else "..."}</p>
        <p style="text-indent: 30px;">{' '.join(lista_final)}</p>
        <div style="text-align: right;">{num_class}</div>
    </div>
    """
    st.markdown(html_ficha, unsafe_allow_html=True)
    
    # Exportação Word
    doc = Document()
    doc.add_paragraph("Ficha Catalográfica").bold = True
    doc.add_paragraph(html_ficha.replace('<p style="text-indent: 30px;">', '\n    ').replace('<p>', '\n').replace('<b>', '').replace('</b>', '').replace('</div>', '').replace('<div style="text-align: right;">', '\n'))
    bio = io.BytesIO()
    doc.save(bio)
    st.download_button("📥 Baixar em Word (.docx)", data=bio.getvalue(), file_name="ficha_catalografica.docx")
