import streamlit as st
import pandas as pd
import requests
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="wide")

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

# DIVISÃO DE COLUNAS (Esquerda para inputs, Direita para a ficha)
col_esq, col_dir = st.columns([1.5, 1], gap="large")

with col_esq:
    st.subheader("📚 Dados da Obra")
    
    # Linha 1: Títulos
    c_tit1, c_tit2 = st.columns(2)
    with c_tit1: titulo = st.text_input("Título da obra:")
    with c_tit2: titulo_original = st.text_input("Título original (se traduzida):")
    
    # Linha 2: Publicação
    c_pub1, c_pub2, c_pub3 = st.columns(3)
    with c_pub1: cidade = st.text_input("Cidade:")
    with c_pub2: editora = st.text_input("Editora:")
    with c_pub3: ano = st.text_input("Ano:")
    
    # Linha 3: Descrição Física e Classificação
    c_desc1, c_desc2, c_desc3, c_desc4 = st.columns(4)
    with c_desc1: volumes = st.text_input("Volume/Edição:")
    with c_desc2: paginas = st.text_input("Páginas:")
    with c_desc3: isbn = st.text_input("ISBN:")
    with c_desc4: classe_principal = st.text_input("Classe Principal (Ex: 610):")

    st.divider() # Linha divisória visual

    # Linha Nova: Coleção ou Série (Inserida acima de Colaboradores)
    colecao_serie = st.text_input("Coleção ou Série (Opcional):")

    # Linha 4: Responsabilidade (Autores e Colaboradores lado a lado)
    col_autores, col_colab = st.columns(2)
    
    with col_autores:
        st.write("### 👥 Autores")
        if st.button("➕ Adicionar Autor", use_container_width=True): st.session_state.autores.append("")
        for i, aut in enumerate(st.session_state.autores):
            c1, c2 = st.columns([8, 2])
            with c1: st.session_state.autores[i] = st.text_input(f"Autor {i+1}", value=aut, key=f"aut_{i}", label_visibility="collapsed")
            with c2:
                if st.button("❌", key=f"del_aut_{i}") and len(st.session_state.autores) > 1:
                    st.session_state.autores.pop(i); st.rerun()

    with col_colab:
        st.write("### ✍️ Colaboradores")
        if st.button("➕ Adicionar Colaborador", use_container_width=True): st.session_state.colaboradores.append({"nome": "", "tipo": "trad."})
        for i, colab in enumerate(st.session_state.colaboradores):
            c1, c2, c3 = st.columns([5, 3, 2])
            with c1: colab["nome"] = st.text_input("Nome", value=colab["nome"], key=f"colab_nome_{i}", label_visibility="collapsed")
            with c2: colab["tipo"] = st.selectbox("Função", ["trad.", "org.", "comp."], key=f"colab_tipo_{i}", label_visibility="collapsed")
            with c3:
                if st.button("❌", key=f"del_colab_{i}"): st.session_state.colaboradores.pop(i); st.rerun()

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

# --- ME SH E PRÉ-VISUALIZAÇÃO (COLUNA DA DIREITA) ---
with col_dir:
    # Linha 5: MeSH
    st.write("### 🔍 Pesquisa MeSH")
    c_mesh1, c_mesh2 = st.columns([3, 1])
    with c_mesh1:
        termo_mesh = st.text_input("Buscar Descritor MeSH:", label_visibility="collapsed", placeholder="Digite o termo MeSH aqui...")
    with c_mesh2:
        if st.button("Consultar NLM", use_container_width=True): st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
    
    c_mesh3, c_mesh4 = st.columns([3, 1])
    with c_mesh3:
        escolha = st.selectbox("Selecione:", ["-- Escolha --"] + st.session_state.opcoes_mesh, label_visibility="collapsed")
    with c_mesh4:
        if st.button("Adicionar à ficha", use_container_width=True):
            if escolha != "-- Escolha --": st.session_state.lista_assuntos.append(escolha.split(" | ")[1].strip()); st.rerun()
            
    st.caption("**Descritores Escolhidos:** " + (", ".join(list(dict.fromkeys(st.session_state.lista_assuntos))) if st.session_state.lista_assuntos else "Nenhum ainda."))

    st.divider() # Linha para separar a pesquisa da pré-visualização

    st.subheader("👁️ Pré-visualização")
    
    entrada, class_cutter, auts, lista_final = get_ficha_data()

    # Preparando strings para exibição oficial
    autores_str = ', '.join(auts) if len(auts) <= 3 else (auts[0] + ' et al.' if len(auts) > 0 else '')
    volumes_str = f"{volumes} ; " if volumes else ""
    titulo_original_str = f"\nTítulo original: {titulo_original}" if titulo_original else ""
    colecao_str = f" ({colecao_serie})" if colecao_serie else ""

    ficha_texto = f"""{classe_principal}
{class_cutter}

{entrada}.
{titulo} / {autores_str}. – {cidade} : {editora}, {ano}.
{volumes_str}{paginas}.{colecao_str}{titulo_original_str}
ISBN {isbn if isbn else "..."}

{' '.join(lista_final)}
"""

    # Exibe a ficha limpa dentro de uma caixa cinza com botão de copiar automático
    st.markdown(f"```text\n{ficha_texto}\n```")

    # --- DOWNLOAD WORD ---
    st.write("") 
    if st.button("📥 Gerar Documento Word", use_container_width=True):
        doc = Document()
        
        # Centraliza a tabela inteira na página do Word
        table = doc.add_table(rows=1, cols=1)
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        cell = table.cell(0, 0)
        table.columns[0].width = Inches(5.3)
        cell.width = Inches(5.3)
        
        linhas_ficha = ficha_texto.strip().split('\n')
        
        for idx, linha in enumerate(linhas_ficha):
            if idx == 0:
                p = cell.paragraphs[0]
            else:
                p = cell.add_paragraph()
                
            # Garante que o texto dentro da ficha fique perfeitamente à esquerda/justificado
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.15
            
            # Adiciona os recuos necessários para as linhas de catalogação
            if idx >= 3:
                p.paragraph_format.left_indent = Inches(0.5)
            
            run = p.add_run(linha)
            run.font.name = 'Arial'
            run.font.size = Pt(10)
            
            if idx in [0, 1]:
                run.bold = True
                
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button("Baixar Ficha Formatada", data=bio.getvalue(), file_name="ficha_catalografica.docx", use_container_width=True)
