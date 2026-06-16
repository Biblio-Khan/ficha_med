import streamlit as st
import pandas as pd
import requests
import io
from docx import Document
from docx.shared import Pt, Inches
from deep_translator import GoogleTranslator
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="wide")

# Inicialização de Estados
if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = []
if 'autores' not in st.session_state: st.session_state.autores = [""]
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []
if 'mesh_limite' not in st.session_state: st.session_state.mesh_limite = 5
if 'ultimo_termo' not in st.session_state: st.session_state.ultimo_termo = ""
if 'fichas_lote' not in st.session_state: st.session_state.fichas_lote = []

# --- FUNÇÕES ---
def traduzir_para_portugues(texto):
    """Traduz o termo do MeSH (inglês) para o português de forma automática."""
    try:
        return GoogleTranslator(source='en', target='pt').translate(texto)
    except:
        return texto

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
def buscar_descritores_mesh(termo, limite=5):
    url_lookup = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"label": termo.strip(), "match": "contains", "limit": limite}
    headers = {"User-Agent": "BiblioKhanMedicas/1.0 (Contato: seu-email@exemplo.com)"}
    
    try:
        resp = requests.get(url_lookup, params=params, headers=headers, timeout=10)
        if resp.status_code != 200 or not resp.json():
            return []

        resultados_completos = []
        for item in resp.json():
            descriptor_id = item.get('resource', '').split('/')[-1]
            termo_oficial = item.get('label', termo) 

            url_details = f"https://id.nlm.nih.gov/mesh/lookup/details?descriptor={descriptor_id}"
            resp_details = requests.get(url_details, headers=headers, timeout=10)
            
            sinonimos_encontrados = []
            if resp_details.status_code == 200:
                data = resp_details.json()
                termos_brutos = data.get('terms', []) + data.get('entryTerms', [])
                for t in termos_brutos:
                    s = t.get('label') or t.get('term') if isinstance(t, dict) else t
                    if s and isinstance(s, str) and s.lower() != termo_oficial.lower():
                        sinonimos_encontrados.append(s)
                sinonimos_encontrados = list(dict.fromkeys(sinonimos_encontrados))
                
            resultados_completos.append({
                "termo_oficial": termo_oficial,
                "sinonimos": sinonimos_encontrados
            })
        return resultados_completos
    except:
        return []

def get_ficha_data(titulo, autores, colaboradores, lista_assuntos, orientador="", coorientador=""):
    autores_v = [a for a in autores if a.strip()]
    entrada = formatar_entrada_autor(autores_v[0]) if autores_v else "AUTOR NÃO INFORMADO"
    sobrenome_letra = autores_v[0].split()[-1][0].upper() if autores_v else "A"
    cutter_id = calcular_cutter(autores_v[0]) if autores_v else "000"
    
    titulo_limpo = remover_artigos(titulo)
    primeira_letra_titulo = titulo_limpo[0].lower() if len(titulo_limpo) > 0 else "a"
    classificacao_cutter = f"{sobrenome_letra}{cutter_id}{primeira_letra_titulo}"
    
    assuntos_limpos = [a for a in lista_assuntos if isinstance(a, str) and a.strip()]
    assuntos = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(dict.fromkeys(assuntos_limpos))]
    
    # Geração dinâmica de algarismos romanos para as entradas secundárias
    romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    r_idx = 0
    
    entradas = [f"{romanos[r_idx]}. Título."]
    r_idx += 1
    
    if orientador.strip():
        entradas.append(f"{romanos[r_idx]}. {formatar_entrada_autor(orientador)}, orient.")
        r_idx += 1
        
    if coorientador.strip():
        entradas.append(f"{romanos[r_idx]}. {formatar_entrada_autor(coorientador)}, coorient.")
        r_idx += 1
        
    for colab in colaboradores:
        if colab["nome"].strip():
            entradas.append(f"{romanos[min(r_idx, len(romanos)-1)]}. {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")
            r_idx += 1
    
    return entrada, classificacao_cutter, autores_v, assuntos + entradas

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

col_esq, col_dir = st.columns([1.5, 1], gap="large")

with col_esq:
    st.subheader("📚 Dados da Obra")
    
    c_tit1, c_tit2 = st.columns(2)
    with c_tit1: titulo = st.text_input("Título da obra:")
    with c_tit2: titulo_original = st.text_input("Título original (se traduzida):")
    
    c_pub1, c_pub2, c_pub3 = st.columns(3)
    with c_pub1: cidade = st.text_input("Cidade:")
    with c_pub2: editora = st.text_input("Editora/Instituição de Defesa:")
    with c_pub3: ano = st.text_input("Ano:")
    
    c_desc1, c_desc2, c_desc3 = st.columns(3)
    with c_desc1: volumes = st.text_input("Volume/Edição:")
    with c_desc2: paginas = st.text_input("Páginas (Ex: 150 p.):")
    with c_desc3: isbn = st.text_input("ISBN (deixar vazio para teses):")
    
    c_class1, c_class2 = st.columns(2)
    with c_class1: classe_principal = st.text_input("Classe Principal DDC/CDU (Ex: 610):")
    with c_class2: classe_nlm = st.text_input("Classificação NLM (Ex: WG 140):")

    colecao_serie = st.text_input("Coleção ou Série (Opcional):")

    # --- SEÇÃO DE TRABALHOS ACADÉMICOS ---
    st.write("### 🎓 Trabalho Académico (Teses e Dissertações)")
    e_trabalho_academico = st.checkbox("Esta obra é uma Tese, Dissertação ou Monografia de Residência?")
    
    grau_academico = "Nenhum"
    area_concentracao = ""
    instituicao = ""
    orientador = ""
    coorientador = ""
    
    if e_trabalho_academico:
        c_acad1, c_acad2 = st.columns(2)
        with c_acad1:
            grau_academico = st.selectbox("Grau Académico:", [
                "Nenhum", "Dissertação (Mestrado)", "Tese (Doutorado)", 
                "Tese (Livre-Docência)", "Monografia (Residência Médica)", "Monografia (Especialização)"
            ])
        with c_acad2:
            area_concentracao = st.text_input("Área de Concentração (Ex: Cardiologia):")
            
        instituicao = st.text_input("Faculdade/Instituição (Ex: Faculdade de Medicina, Universidade de São Paulo):")
        
        c_ori1, c_ori2 = st.columns(2)
        with c_ori1: orientador = st.text_input("Nome do Orientador(a):")
        with c_ori2: coorientador = st.text_input("Nome do Coorientador(a) (Opcional):")

    st.divider()

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
        st.write("### ✍️ Colaboradores Extensão")
        if st.button("➕ Adicionar Colaborador", use_container_width=True): st.session_state.colaboradores.append({"nome": "", "tipo": "trad."})
        for i, colab in enumerate(st.session_state.colaboradores):
            c1, c2, c3 = st.columns([5, 3, 2])
            with c1: colab["nome"] = st.text_input("Nome", value=colab["nome"], key=f"colab_nome_{i}", label_visibility="collapsed")
            with c2: colab["tipo"] = st.selectbox("Função", ["trad.", "org.", "comp."], key=f"colab_tipo_{i}", label_visibility="collapsed")
            with c3:
                if st.button("❌", key=f"del_colab_{i}"): st.session_state.colaboradores.pop(i); st.rerun()

with col_dir:
    # --- SEÇÃO DE BUSCA MESH ---
    st.subheader("🔍 Assuntos e Indexação (MeSH)")
    termo_busca = st.text_input("Buscar termo no MeSH para o Assunto:")
    
    if termo_busca:
        if termo_busca != st.session_state.ultimo_termo:
            st.session_state.ultimo_termo = termo_busca
            st.session_state.mesh_limite = 5
            
        resultados = buscar_descritores_mesh(termo_busca, st.session_state.mesh_limite)
        
        if resultados:
            st.success(f"Mostrando até {st.session_state.mesh_limite} termos no banco MeSH.")
            opcoes_nomes = [r["termo_oficial"] for r in resultados]
            escolha = st.selectbox("Selecione o termo mais adequado:", opcoes_nomes)
            termo_escolhido = next(r for r in resultados if r["termo_oficial"] == escolha)
            
            st.markdown(f"### 📍 Termo Autorizado (En): **{termo_escolhido['termo_oficial']}**")
            
            if termo_escolhido['sinonimos']:
                with st.expander(f"📝 Ver sinônimos ({len(termo_escolhido['sinonimos'])} encontrados)"):
                    st.write("Estes termos referem-se ao termo selecionado:")
                    for s in termo_escolhido['sinonimos']: st.markdown(f"- {s}")
            
            qualificadores_comuns = [
                "Nenhum", "anatomia & histologia", "cirurgia", "citologia", "diagnóstico", 
                "dietoterapia", "efeitos adversos", "enfermagem", "enzimologia", "epidemiologia", 
                "ética", "etiologia", "farmacologia", "fisiologia", "fisiopatologia", 
                "genética", "imunologia", "lesões", "metabolismo", "microbiologia", 
                "mortalidade", "patologia", "prevenção & controle", "psicologia", 
                "radiografia", "reabilitação", "sangue", "terapia", "transplante", "urina"
            ]
            qualificador_escolhido = st.selectbox("Adicionar qualificador específico (Opcional):", qualificadores_comuns)
            
            col_add, col_mais = st.columns(2)
            with col_add:
                if st.button("➕ Adicionar como Assunto", use_container_width=True):
                    termo_em_portugues = traduzir_para_portugues(termo_escolhido['termo_oficial']).capitalize()
                    if qualificador_escolhido != "Nenhum":
                        termo_em_portugues = f"{termo_em_portugues} / {qualificador_escolhido}"
                        
                    if termo_em_portugues not in st.session_state.lista_assuntos:
                        st.session_state.lista_assuntos.append(termo_em_portugues)
                    st.rerun()
            with col_mais:
                if len(resultados) == st.session_state.mesh_limite:
                    if st.button("🔄 Buscar mais resultados", use_container_width=True):
                        st.session_state.mesh_limite += 5
                        st.rerun()

    st.write("### 📋 Assuntos Selecionados")
    if not st.session_state.lista_assuntos:
        st.caption("Nenhum assunto selecionado ainda.")
    else:
        for i, assunto in enumerate(st.session_state.lista_assuntos):
            c_assunto, c_del_assunto = st.columns([8, 2])
            with c_assunto: st.markdown(f"• {assunto}")
            with c_del_assunto:
                if st.button("❌", key=f"del_assunto_{i}"):
                    st.session_state.lista_assuntos.pop(i); st.rerun()

    st.divider()

    # --- PRÉ-VISUALIZAÇÃO DE TEXTO ---
    st.subheader("👁️ Pré-visualização")
    
    entrada, class_cutter, auts, lista_final = get_ficha_data(
        titulo, st.session_state.autores, st.session_state.colaboradores, st.session_state.lista_assuntos,
        orientador, coorientador
    )

    autores_str = ', '.join(auts) if len(auts) <= 3 else (auts[0] + ' et al.' if len(auts) > 0 else '')
    volumes_str = f"{volumes} ; " if volumes else ""
    titulo_original_str = f"\n             Título original: {titulo_original}" if titulo_original else ""
    colecao_str = f" ({colecao_serie})" if colecao_serie else ""

    # Construção da Nota de Tese formatada pelas normas ABNT
    nota_tese_str = ""
    if grau_academico != "Nenhum":
        area_str = f" em {area_concentracao}" if area_concentracao.strip() else ""
        inst_str = f" – {instituicao}" if面 instituicao.strip() else ""
        nota_tese_str = f"\n             {grau_academico}{area_str}{inst_str}, {cidade}, {ano}."

    bloco_classificacao = []
    if classe_nlm.strip(): bloco_classificacao.append(classe_nlm.strip())
    if classe_principal.strip(): bloco_classificacao.append(classe_principal.strip())
    
    linhas_class_str = "\n".join(bloco_classificacao)
    bloco_esquerdo_top = f"{linhas_class_str}\n{class_cutter}" if linhas_class_str else class_cutter

    ficha_texto = f"""{bloco_esquerdo_top}       {entrada}.
             {titulo} / {autores_str}. – {cidade} : {editora}, {ano}.
             {volumes_str}{paginas}.{colecao_str}{nota_tese_str}{titulo_original_str}
             ISBN {isbn if isbn else "..."}

             {' '.join(lista_final)}
"""

    st.markdown(f"```text\n{ficha_texto}\n```")

    # --- CONTROLES DO LOTE ---
    col_lote_add, col_lote_del = st.columns(2)
    
    with col_lote_add:
        if st.button("➕ Adicionar ao Lote", use_container_width=True):
            st.session_state.fichas_lote.append({
                "classe_nlm": classe_nlm.strip(), "classe_principal": classe_principal.strip(), 
                "class_cutter": class_cutter, "entrada": entrada, "titulo": titulo, "autores_str": autores_str, 
                "cidade": city := cidade, "editora": editora, "ano": ano, "volumes_str": volumes_str, "paginas": paginas, 
                "colecao_str": colecao_str, "nota_tese_str": nota_tese_str.strip(), "titulo_original_str": titulo_original_str, "isbn": isbn, "lista_final": lista_final
            })
            st.success(f"Ficha salva! Total no lote: {len(st.session_state.fichas_lote)}")

    with col_lote_del:
        if st.button("🗑️ Limpar Todo o Lote", use_container_width=True):
            st.session_state.fichas_lote = []
            st.rerun()

    # Geração do ficheiro DOCX
    if st.session_state.fichas_lote:
        doc = Document()
        for idx, f in enumerate(st.session_state.fichas_lote):
            table = doc.add_table(rows=1, cols=1)
            table.style = 'Table Grid'
            table.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell = table.cell(0, 0)
            table.columns[0].width = Inches(5.3)
            cell.width = Inches(5.3)
            
            p_topo = cell.paragraphs[0]
            p_topo.paragraph_format.space_after = Pt(0)
            p_topo.paragraph_format.line_spacing = 1.15
            
            classes_linhas = []
            if f["classe_nlm"]: classes_linhas.append(f["classe_nlm"])
            if f["classe_principal"]: classes_linhas.append(f["classe_principal"])
            
            if classes_linhas:
                r_classes = p_topo.add_run("\n".join(classes_linhas))
                r_classes.font.name = 'Arial'; r_classes.font.size = Pt(10); r_classes.bold = True
                p_cutter_entrada = cell.add_paragraph()
            else:
                p_cutter_entrada = p_topo
                
            p_cutter_entrada.paragraph_format.space_after = Pt(0)
            p_cutter_entrada.paragraph_format.line_spacing = 1.15
            p_cutter_entrada.paragraph_format.tab_stops.add_tab_stop(Inches(0.7)) 
            
            r_cutter = p_cutter_entrada.add_run(f["class_cutter"])
            r_cutter.font.name = 'Arial'; r_cutter.font.size = Pt(10); r_cutter.bold = True
            p_cutter_entrada.add_run("\t") 
            
            r_ent = p_cutter_entrada.add_run(f"{f['entrada']}.")
            r_ent.font.name = 'Arial'; r_ent.font.size = Pt(10)
            
            p_corpo = cell.add_paragraph()
            p_corpo.paragraph_format.space_after = Pt(0)
            p_corpo.paragraph_format.line_spacing = 1.15
            p_corpo.paragraph_format.left_indent = Inches(0.7) 
            
            corpo_linhas = [
                f"{f['titulo']} / {f['autores_str']}. – {f['cidade']} : {f['editora']}, {f['ano']}.",
                f"{f['volumes_str']}{f['paginas']}.{f['colecao_str']}"
            ]
            if f["nota_tese_str"]:
                corpo_linhas.append(f["nota_tese_str"])
            if f["titulo_original_str"].strip():
                corpo_linhas.append(f["titulo_original_str"].strip())
                
            corpo_linhas.append(f"ISBN {f['isbn'] if f['isbn'] else '...'}")
            corpo_linhas.append("")
            corpo_linhas.append(' '.join(f['lista_final']))
            
            r_corpo = p_corpo.add_run("\n".join(corpo_linhas))
            r_corpo.font.name = 'Arial'; r_corpo.font.size = Pt(10)
            
            if idx < len(st.session_state.fichas_lote) - 1:
                doc.add_page_break()
                    
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button("📥 Baixar Fichas em Lote (.docx)", data=bio.getvalue(), file_name="lote_fichas_catalograficas.docx", use_container_width=True)
