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

# --- FUNÇÕES ---
def formatar_entrada_autor(nome):
    partes = nome.strip().split()
    return f"{partes[-1].upper()}, {' '.join(partes[:-1])}" if len(partes) > 1 else nome.upper()

def remover_artigos(titulo):
    if not titulo: return ""
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
    # 1. Busca inicial para pegar o ID e o Termo Oficial
    url_lookup = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"query": termo.strip(), "match": "contains", "limit": 1, "type": "descriptor"}
    
    try:
        resp = requests.get(url_lookup, params=params, timeout=10)
        if resp.status_code != 200 or not resp.json():
            return None

        # Pegamos o ID e o Label diretamente do primeiro resultado (mais seguro)
        primeiro_resultado = resp.json()[0]
        descriptor_id = primeiro_resultado.get('resource', '').split('/')[-1]
        termo_oficial = primeiro_resultado.get('label', termo) 

        # 2. Busca de detalhes APENAS para pegar os sinônimos
        url_details = f"https://id.nlm.nih.gov/mesh/lookup/details?descriptor={descriptor_id}"
        resp_details = requests.get(url_details, timeout=10)
        
        sinonimos = []
        if resp_details.status_code == 200:
            data = resp_details.json()
            sinonimos = [item.get('term') for item in data.get('entryTerms', []) if item.get('term')]
            
        return {
            "termo_oficial": termo_oficial,
            "sinonimos": sinonimos
        }
    except:
        return None

# Função corrigida para receber as variáveis de tela
def get_ficha_data(titulo, autores, colaboradores, lista_assuntos):
    autores_v = [a for a in autores if a.strip()]
    entrada = formatar_entrada_autor(autores_v[0]) if autores_v else "AUTOR NÃO INFORMADO"
    sobrenome_letra = autores_v[0].split()[-1][0].upper() if autores_v else "A"
    cutter_id = calcular_cutter(autores_v[0]) if autores_v else "000"
    
    titulo_limpo = remover_artigos(titulo)
    primeira_letra_titulo = titulo_limpo[0].lower() if len(titulo_limpo) > 0 else "a"
    classificacao_cutter = f"{sobrenome_letra}{cutter_id}{primeira_letra_titulo}"
    
    assuntos = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(dict.fromkeys(lista_assuntos))]
    entradas = ["I. Título."]
    romanos = ["II.", "III.", "IV.", "V."]
    for i, colab in enumerate(colaboradores):
        if colab["nome"]: entradas.append(f"{romanos[min(i, 3)]} {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")
    
    return entrada, classificacao_cutter, autores_v, assuntos + entradas

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

# DIVISÃO DE COLUNAS
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

    colecao_serie = st.text_input("Coleção ou Série (Opcional):")

    st.divider()

    # Linha 4: Responsabilidade
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

    st.divider()

    # --- INTEGRAÇÃO MESH ---
    st.subheader("🔍 Assuntos e Indexação (MeSH)")
    termo_busca = st.text_input("Buscar termo no MeSH para o Assunto:")
    if termo_busca:
        resultado = buscar_descritores_mesh(termo_busca)
        
        if resultado:
            st.success("Termo localizado no banco MeSH")
            
            # Exibição clara: Autorizado vs Sinônimos
            st.markdown(f"### 📍 Termo Autorizado: **{resultado['termo_oficial']}**")
            
            if resultado['sinonimos']:
                with st.expander("📝 Ver sinônimos (Entry Terms)"):
                    st.write("Estes termos referem-se ao termo autorizado acima:")
                    for s in resultado['sinonimos']:
                        st.markdown(f"- {s}")
            
            if st.button("➕ Adicionar como Assunto"):
                st.session_state.lista_assuntos.append(resultado['termo_oficial'])
                st.rerun()
        else:
            st.warning("Termo não encontrado ou erro na conexão.")

   # Trava de segurança: Filtra apenas assuntos que sejam texto válido
    assuntos_validos = [str(a) for a in st.session_state.lista_assuntos if a]
    
    st.caption("**Assuntos Selecionados:** " + (", ".join(list(dict.fromkeys(assuntos_validos))) if assuntos_validos else "Nenhum ainda."))
    
    if st.button("🗑️ Limpar Assuntos"):
        st.session_state.lista_assuntos = []
        st.rerun()
with col_dir:
    st.subheader("👁️ Pré-visualização")
    
    # Chamada corrigida passando os parâmetros
    entrada, class_cutter, auts, lista_final = get_ficha_data(
        titulo, 
        st.session_state.autores, 
        st.session_state.colaboradores, 
        st.session_state.lista_assuntos
    )

    # Preparando strings
    autores_str = ', '.join(auts) if len(auts) <= 3 else (auts[0] + ' et al.' if len(auts) > 0 else '')
    volumes_str = f"{volumes} ; " if volumes else ""
    titulo_original_str = f"\n             Título original: {titulo_original}" if titulo_original else ""
    colecao_str = f" ({colecao_serie})" if colecao_serie else ""

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
        
        table = doc.add_table(rows=1, cols=1)
        table.style = 'Table Grid'
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        cell = table.cell(0, 0)
        table.columns[0].width = Inches(5.3)
        cell.width = Inches(5.3)
        
        p0 = cell.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.line_spacing = 1.15
        
        r0 = p0.add_run(classe_principal)
        r0.font.name = 'Arial'
        r0.font.size = Pt(10)
        r0.bold = True
        
        p1 = cell.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = 1.15
        p1.paragraph_format.tab_stops.add_tab_stop(Inches(0.7)) 
        
        r1_cutter = p1.add_run(class_cutter)
        r1_cutter.font.name = 'Arial'
        r1_cutter.font.size = Pt(10)
        r1_cutter.bold = True
        
        p1.add_run("\t") 
        
        r1_ent = p1.add_run(f"{entrada}.")
        r1_ent.font.name = 'Arial'
        r1_ent.font.size = Pt(10)
        
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = 1.15
        p2.paragraph_format.left_indent = Inches(0.7) 
        
        corpo_linhas = [
            f"{titulo} / {autores_str}. – {cidade} : {editora}, {ano}.",
            f"{volumes_str}{paginas}.{colecao_str}{titulo_original_str.strip()}",
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
