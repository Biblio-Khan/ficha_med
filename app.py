import streamlit as st
import pandas as pd
import requests
import io
import os
import base64
from docx import Document
from docx.shared import Pt, Inches
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
    params = {"query": termo.strip(), "match": "contains", "limit": limite, "type": "descriptor"}
    
    try:
        resp = requests.get(url_lookup, params=params, timeout=10)
        if resp.status_code != 200 or not resp.json():
            return []

        resultados_completos = []
        
        for item in resp.json():
            descriptor_id = item.get('resource', '').split('/')[-1]
            termo_oficial = item.get('label', termo) 

            url_details = f"https://id.nlm.nih.gov/mesh/lookup/details?descriptor={descriptor_id}"
            resp_details = requests.get(url_details, timeout=10)
            
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

def get_ficha_data(titulo, autores, colaboradores, lista_assuntos):
    autores_v = [a for a in autores if a.strip()]
    entrada = formatar_entrada_autor(autores_v[0]) if autores_v else "AUTOR NÃO INFORMADO"
    sobrenome_letra = autores_v[0].split()[-1][0].upper() if autores_v else "A"
    cutter_id = calcular_cutter(autores_v[0]) if autores_v else "000"
    
    titulo_limpo = remover_artigos(titulo)
    primeira_letra_titulo = titulo_limpo[0].lower() if len(titulo_limpo) > 0 else "a"
    classificacao_cutter = f"{sobrenome_letra}{cutter_id}{primeira_letra_titulo}"
    
    assuntos_limpos = [a for a in lista_assuntos if isinstance(a, str) and a.strip()]
    assuntos = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(dict.fromkeys(assuntos_limpos))]
    
    entradas = ["I. Título."]
    romanos = ["II.", "III.", "IV.", "V."]
    for i, colab in enumerate(colaboradores):
        if colab["nome"]: entradas.append(f"{romanos[min(i, 3)]} {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")
    
    return entrada, classificacao_cutter, autores_v, assuntos + entradas

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

# Criação das Abas Principais
tab_principal, tab_cdd = st.tabs(["📋 Criar Fichas & Lote", "📖 Consultar Documento CDD"])

with tab_principal:
    col_esq, col_dir = st.columns([1.5, 1], gap="large")

    with col_esq:
        st.subheader("📚 Dados da Obra")
        
        c_tit1, c_tit2 = st.columns(2)
        with c_tit1: titulo = st.text_input("Título da obra:")
        with c_tit2: titulo_original = st.text_input("Título original (se traduzida):")
        
        c_pub1, c_pub2, c_pub3 = st.columns(3)
        with c_pub1: cidade = st.text_input("Cidade:")
        with c_pub2: editora = st.text_input("Editora:")
        with c_pub3: ano = st.text_input("Ano:")
        
        c_desc1, c_desc2, c_desc3, c_desc4 = st.columns(4)
        with c_desc1: volumes = st.text_input("Volume/Edição:")
        with c_desc2: paginas = st.text_input("Páginas:")
        with c_desc3: isbn = st.text_input("ISBN:")
        with c_desc4: classe_principal = st.text_input("Classe Principal (Ex: 610):")

        colecao_serie = st.text_input("Coleção ou Série (Opcional):")

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
            st.write("### ✍️ Colaboradores")
            if st.button("➕ Adicionar Colaborador", use_container_width=True): st.session_state.colaboradores.append({"nome": "", "tipo": "trad."})
            for i, colab in enumerate(st.session_state.colaboradores):
                c1, c2, c3 = st.columns([5, 3, 2])
                with c1: colab["nome"] = st.text_input("Nome", value=colab["nome"], key=f"colab_nome_{i}", label_visibility="collapsed")
                with c2: colab["tipo"] = st.selectbox("Função", ["trad.", "org.", "comp."], key=f"colab_tipo_{i}", label_visibility="collapsed")
                with c3:
                    if st.button("❌", key=f"del_colab_{i}"): st.session_state.colaboradores.pop(i); st.rerun()

    with col_dir:
        # --- SEÇÃO DE BUSCA MESH (NO TOPO) ---
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
                
                st.markdown(f"### 📍 Termo Autorizado: **{termo_escolhido['termo_oficial']}**")
                
                if termo_escolhido['sinonimos']:
                    with st.expander(f"📝 Ver sinônimos ({len(termo_escolhido['sinonimos'])} encontrados)"):
                        st.write("Estes termos referem-se ao termo selecionado:")
                        for s in termo_escolhido['sinonimos']:
                            st.markdown(f"- {s}")
                else:
                    st.info("Nenhum sinônimo direto encontrado para este termo.")
                
                col_add, col_mais = st.columns(2)
                with col_add:
                    if st.button("➕ Adicionar como Assunto", use_container_width=True):
                        st.session_state.lista_assuntos.append(termo_escolhido['termo_oficial'])
                        st.rerun()
                with col_mais:
                    if len(resultados) == st.session_state.mesh_limite:
                        if st.button("🔄 Buscar mais resultados", use_container_width=True):
                            st.session_state.mesh_limite += 5
                            st.rerun()
            else:
                st.warning("Termo não encontrado ou erro na conexão.")

        assuntos_validos = [str(a) for a in st.session_state.lista_assuntos if isinstance(a, str) and a]
        st.caption("**Assuntos Selecionados:** " + (", ".join(list(dict.fromkeys(assuntos_validos))) if assuntos_validos else "Nenhum ainda."))
        
        if st.button("🗑️ Limpar Assuntos"):
            st.session_state.lista_assuntos = []
            st.rerun()

        st.divider()

        # --- PRÉ-VISUALIZAÇÃO DE TEXTO ---
        st.subheader("👁️ Pré-visualização")
        
        entrada, class_cutter, auts, lista_final = get_ficha_data(
            titulo, 
            st.session_state.autores, 
            st.session_state.colaboradores, 
            st.session_state.lista_assuntos
        )

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

        st.markdown(f"```text\n{ficha_texto}\n```")
        st.write("") 

        # --- CONTROLES DO LOTE ---
        col_lote_add, col_lote_del = st.columns(2)
        
        with col_lote_add:
            if st.button("➕ Adicionar ao Lote", use_container_width=True):
                st.session_state.fichas_lote.append({
                    "classe_principal": classe_principal, "class_cutter": class_cutter, "entrada": entrada,
                    "titulo": titulo, "autores_str": autores_str, "cidade": cidade, "editora": editora, "ano": ano,
                    "volumes_str": volumes_str, "paginas": paginas, "colecao_str": colecao_str,
                    "titulo_original_str": titulo_original_str, "isbn": isbn, "lista_final": lista_final
                })
                st.success(f"Ficha salva! Total no lote: {len(st.session_state.fichas_lote)}")

        with col_lote_del:
            if st.button("🗑️ Limpar Todo o Lote", use_container_width=True):
                st.session_state.fichas_lote = []
                st.warning("O lote foi reiniciado e esvaziado.")
                st.rerun()

        if st.session_state.fichas_lote:
            st.write(f"📦 **Status do Lote:** {len(st.session_state.fichas_lote)} ficha(s) salva(s).")
            
            doc = Document()
            for idx, f in enumerate(st.session_state.fichas_lote):
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
                
                r0 = p0.add_run(f["classe_principal"])
                r0.font.name = 'Arial'
                r0.font.size = Pt(10)
                r0.bold = True
                
                p1 = cell.add_paragraph()
                p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p1.paragraph_format.space_after = Pt(0)
                p1.paragraph_format.line_spacing = 1.15
                p1.paragraph_format.tab_stops.add_tab_stop(Inches(0.7)) 
                
                r1_cutter = p1.add_run(f["class_cutter"])
                r1_cutter.font.name = 'Arial'
                r1_cutter.font.size = Pt(10)
                r1_cutter.bold = True
                
                p1.add_run("\t") 
                
                r1_ent = p1.add_run(f"{f['entrada']}.")
                r1_ent.font.name = 'Arial'
                r1_ent.font.size = Pt(10)
                
                p2 = cell.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p2.paragraph_format.space_after = Pt(0)
                p2.paragraph_format.line_spacing = 1.15
                p2.paragraph_format.left_indent = Inches(0.7) 
                
                corpo_linhas = [
                    f"{f['titulo']} / {f['autores_str']}. – {f['cidade']} : {f['editora']}, {f['ano']}.",
                    f"{f['volumes_str']}{f['paginas']}.{f['colecao_str']}{f['titulo_original_str'].strip()}",
                    f"ISBN {f['isbn'] if f['isbn'] else '...'}",
                    "",
                    ' '.join(f['lista_final'])
                ]
                
                r2 = p2.add_run("\n".join(corpo_linhas))
                r2.font.name = 'Arial'
                r2.font.size = Pt(10)
                
                if idx < len(st.session_state.fichas_lote) - 1:
                    doc.add_page_break()
                        
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button("📥 Baixar Fichas em Lote (.docx)", data=bio.getvalue(), file_name="lote_fichas_catalograficas.docx", use_container_width=True)

# --- ABA DE CONSULTA INDEPENDENTE (LEITURA DE PDF INTERNO) ---
with tab_cdd:
    st.subheader("📖 Documento Guia de Consulta")
    st.write("Consulte o PDF completo da classificação diretamente aqui dentro do sistema.")
    
    # Nome esperado do arquivo PDF do usuário
    pdf_nome_arquivo = "cdd_medica.pdf"
    
    if os.path.exists(pdf_nome_arquivo):
        try:
            # Leitura do arquivo PDF e conversão para string base64
            with open(pdf_nome_arquivo, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            # Incorporação do PDF usando uma tag iframe do HTML
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="900" style="border: 1px solid #ccc; border-radius: 5px;"></iframe>'
            
            # Renderização do componente de tela cheia para o PDF
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Erro ao carregar e processar o arquivo PDF: {e}")
    else:
        st.info("💡 **Como ativar o visualizador de consulta:**")
        st.markdown(f"""
        Para visualizar o seu documento aqui dentro, faça o seguinte:
        1. Pegue o seu arquivo Word/PDF de classificação.
        2. Certifique-se de salvá-lo com o formato **.pdf**.
        3. Nomeie o arquivo exatamente como: `{pdf_nome_arquivo}`
        4. Coloque-o **na mesma pasta** onde está este script do Python (`app.py`).
        
        Assim que você colocar o arquivo lá, ele carregará automaticamente nesta tela com todas as barras de rolagem e zoom!
        """)
