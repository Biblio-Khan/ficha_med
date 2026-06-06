import streamlit as st
import pandas as pd
import io
import requests
import datetime
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import firebase_admin
from firebase_admin import credentials, auth
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator  # <--- Nova biblioteca de tradução

# =========================================================================
# 1. CONFIGURAÇÕES TÉCNICAS DA PÁGINA & INICIALIZAÇÃO SEGURA DO FIREBASE
# =========================================================================

# =========================================================================
# 1. CONFIGURAÇÕES TÉCNICAS DA PÁGINA & INICIALIZAÇÃO SEGURA DO FIREBASE
# =========================================================================

st.set_page_config(
    page_title="Gerador de Fichas Médicas - PubMed Hub",
    page_icon="logo_bibliokhan.ico",
    layout="wide"
)

st.sidebar.image("logo_bibliokhan.png", use_container_width=True)

with st.sidebar:
    st.title("**BiblioKhan**")
    st.write("**Inteligência e Automação para Bibliotecas da Saúde**")
    st.write("bibliokhancontato@gmail.com")
    st.markdown("---")

if not firebase_admin._apps:
    try:
        # Cria uma cópia limpa dos secrets do Firebase
        firebase_secrets = dict(st.secrets["firebase"])
        
        # Coleta e limpa a private key de impurezas de formatação
        p_key = firebase_secrets["private_key"].strip()
        
        # Remove aspas duplicadas nas pontas caso tenha sido colada com aspas normais
        if p_key.startswith('"') and p_key.endswith('"'):
            p_key = p_key[1:-1]
            
        # Corrige quebras de linha literais '\\n' para quebras reais '\n'
        p_key = p_key.replace("\\n", "\n")
        
        # Devolve a chave devidamente tratada para o dicionário
        firebase_secrets["private_key"] = p_key
        
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Erro crítico nas credenciais do Firebase: {str(e)}")

# =========================================================================
# 🌟 RECARGA AUTOMÁTICA EM BACKEND
# =========================================================================
def tratar_url_google_sheets(url):
    url = url.strip()
    if "?" in url and not "docs.google.com" in url:
        url = url.split("?")[0]
        
    if "/edit" in url:
        url = url.split("/edit")[0] + "/export?format=csv"
    elif "/pubhtml" in url:
        url = url.split("/pubhtml")[0] + "/pub?output=csv"
    elif not url.endswith("/export?format=csv") and "docs.google.com" in url:
        if url.endswith("/"):
            url = url + "export?format=csv"
        else:
            url = url + "/export?format=csv"
            
    import time
    nocache_param = f"&nocache={int(time.time())}"
    url += nocache_param
    return url

def carregar_creditos_planilha(url_planilha):
    try:
        url_tratada = tratar_url_google_sheets(url_planilha)
        df = pd.read_csv(url_tratada)
        return df
    except Exception as e:
        st.error(f"Erro ao acessar os dados da planilha: {e}")
        return None

def atualizar_saldo_usuario(email_usuario):
    try:
        url_planilha = st.secrets["URL_PLANILHA"]
        df = carregar_creditos_planilha(url_planilha)
        
        if df is not None:
            df.columns = df.columns.str.strip().str.lower()
            
            if 'token' in df.columns and 'creditos' in df.columns:
                df['token'] = df['token'].astype(str).str.strip().str.upper()
                email_chave = email_usuario.strip().upper()
                
                if email_chave in df['token'].values:
                    saldo = int(df.loc[df['token'] == email_chave, 'creditos'].values[0])
                    st.session_state["creditos_ativos"] = saldo
                else:
                    st.error("❌ O e-mail de login NÃO foi encontrado na coluna 'token'.")
                    st.session_state["creditos_ativos"] = 0
            else:
                st.error("❌ Erro crítico: A planilha precisa das colunas 'token' e 'creditos'.")
                st.session_state["creditos_ativos"] = 0
    except Exception as e:
        st.error(f"❌ Erro na sincronização de saldo: {e}")
        st.session_state["creditos_ativos"] = 0

# =========================================================================
# 2. SISTEMA DE AUTENTICAÇÃO
# =========================================================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if "creditos_ativos" not in st.session_state:
    st.session_state["creditos_ativos"] = 0

if st.session_state["logado"]:
    with st.sidebar:
        if st.session_state["creditos_ativos"] > 0:
            st.success(f"Saldo Atual: {st.session_state['creditos_ativos']} fichas")
        else:
            st.error("💳 Sem créditos ativos")

if not st.session_state["logado"]:
    st.markdown("# 🔒 Área do Cliente - Módulo Médico")
    with st.form("login_form"):
        email_input = st.text_input("E-mail de Usuário").strip()
        senha_input = st.text_input("Senha de Acesso", type="password").strip()
        botao_entrar = st.form_submit_button("Entrar no Sistema")
        if botao_entrar and email_input and senha_input:
            if verificar_login_firebase(email_input, senha_input):
                st.rerun()
else:
    # --- INTERFACE FLUXO PRINCIPAL ---
    st.markdown("""
        <style>
        textarea { font-family: 'Courier New', Courier, monospace !important; }
        .stTabs [aria-selected="true"] { background-color: #B19FFB !important; color: black !important; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

    if "lote_fichas" not in st.session_state:
        st.session_state.lote_fichas = []

    if "assuntos_selecionados" not in st.session_state:
        st.session_state.assuntos_selecionados = []

    # =========================================================================
    # 🔄 NOVA FUNÇÃO: BUSCA TRADUZIDA NA API DO PUBMED
    # =========================================================================
    def buscar_pubmed_com_traducao(termo_pt):
        try:
            # 1. Traduz o termo digitado em PT para EN (Língua nativa do PubMed)
            termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
            
            # 2. Executa a busca (esearch) para pegar os IDs dos artigos
            url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={termo_en}&retmode=json&retmax=5"
            res_search = requests.get(url_search).json()
            id_list = res_search.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return []
                
            # 3. Executa o sumário (esummary) para obter os títulos e metadados
            ids_formatados = ",".join(id_list)
            url_summary = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_formatados}&retmode=json"
            res_summary = requests.get(url_summary).json()
            detalhes = res_summary.get("result", {})
            
            resultados_finais = []
            for pmid in id_list:
                artigo = detalhes.get(pmid, {})
                titulo_artigo = artigo.get("title", "Sem título informado")
                resultados_finais.append({
                    "termo": titulo_artigo,
                    "id": f"PMID-{pmid}"
                })
            return resultados_finais
        except Exception as e:
            st.error(f"Erro na comunicação com o PubMed: {e}")
            return []

    def gerar_docx_lote(lista_fichas):
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Courier New'
        style.font.size = Pt(10)
        for idx, ficha_texto in enumerate(lista_fichas):
            if idx > 0: doc.add_page_break()
            doc.add_paragraph(ficha_texto).alignment = WD_ALIGN_PARAGRAPH.LEFT
            doc.add_paragraph("\n" + "-"*50 + "\n")
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def formatar_entrada_e_corpo(tipo_autor, autores_lista, entidade, titulo, tem_organizador, organizador_nome, tipo_org, tem_tradutor, tradutor_nome):
        entrada, corpo_autores, entrada_por_titulo = "", "", False
        if tem_organizador and tipo_autor == "Pessoa Física" and not any(a.strip() for a in autores_lista):
            entrada_por_titulo = True
            corpo_autores = f"{tipo_org} por {organizador_nome.strip()}"
        elif tipo_autor == "Entidade (Órgão/Instituição)":
            entrada = entidade.strip().upper()
            corpo_autores = ""
        else:
            autores = [a.strip() for a in autores_lista if a.strip()]
            qtd = len(autores)
            if qtd == 1:
                partes = autores[0].split()
                entrada = f"{partes[-1].upper()}, {' '.join(partes[:-1])}." if len(partes) > 1 else f"{autores[0].upper()}."
                corpo_autores = autores[0]
            elif 2 <= qtd <= 3:
                partes = autores[0].split()
                entrada = f"{partes[-1].upper()}, {' '.join(partes[:-1])}." if len(partes) > 1 else f"{autores[0].upper()}."
                corpo_autores = ", ".join(autores)
            elif qtd >= 4:
                entrada_por_titulo = True
                corpo_autores = f"{autores[0]} [et al.]"
            if tem_organizador and organizador_nome.strip() and qtd < 4:
                corpo_autores += f" ; {tipo_org} por {organizador_nome.strip()}"
        if tem_tradutor and tradutor_nome.strip():
            corpo_autores += f" ; tradução por {tradutor_nome.strip()}" if corpo_autores else f"tradução por {tradutor_nome.strip()}"
        return entrada, corpo_autores, entrada_por_titulo

    def buscar_na_tabela_cutter(texto_para_busca, titulo_obra):
        if not texto_para_busca or not titulo_obra: return "X000x"
        url_csv = "https://raw.githubusercontent.com/Biblio-Khan/gerador-ficha-cat/refs/heads/main/cutter.csv"
        try:
            df = pd.read_csv(url_csv)
            df.columns = df.columns.str.strip().str.lower()
            col_nome = 'name' if 'name' in df.columns else df.columns[0]
            col_id = 'id' if 'id' in df.columns else df.columns[1]
            df['Name_Clean'] = df[col_nome].astype(str).str.strip().str.upper()
            sub_busca = texto_para_busca.strip().upper()
            match = df[df['Name_Clean'] <= sub_busca].sort_values(by='Name_Clean').tail(1)
            num = str(match[col_id].values[0]).strip().split('.')[0] if not match.empty else "200"
            titulo_limpo = titulo_obra.strip().upper()
            for artigo in ["O ", "A ", "OS ", "AS ", "UM ", "UMA "]:
                if titulo_limpo.startswith(artigo):
                    titulo_limpo = titulo_limpo[len(artigo):].strip()
                    break
            return f"{sub_busca[0]}{num}{titulo_limpo[0].lower() if titulo_limpo else 't'}"
        except:
            return f"{texto_para_busca.strip().upper()[0]}200{titulo_obra.strip().lower()[0]}"

    def calcular_cutter(tipo_autor, autores_lista, entidade="", titulo="", tem_organizador=False, organizador_nome=""):
        if tipo_autor == "Entidade (Órgão/Instituição)" and entidade: texto_base = entidade
        elif tipo_autor == "Pessoa Física" and autores_lista and any(a.strip() for a in autores_lista):
            autor_principal = [a.strip() for a in autores_lista if a.strip()][0]
            partes = autor_principal.split()
            texto_base = partes[-1] if len(partes) > 1 else autor_principal
        elif tem_organizador or tipo_autor == "Organizador":
            partes_org = organizador_nome.strip().split()
            texto_base = partes_org[-1] if len(partes_org) > 1 else organizador_nome
        else: texto_base = "Autor"
        return buscar_na_tabela_cutter(texto_base, titulo)

    tab_gerador, tab_financeiro = st.tabs(["🏥 Gerar Ficha Médica", "💳 Compra e Gestão de Créditos"])

    with tab_gerador:
        if st.session_state["creditos_ativos"] <= 0:
            st.warning("🔒 O painel de salvamento está bloqueado. Adquira créditos.")

        st.title("🏥 Gerador de Fichas Médicas — Integração PubMed")
        st.markdown("---")
        
        container_lote = st.container()
        with container_lote:
            col_lote_1, col_lote_2 = st.columns([2, 1])
            qtd_fichas = len(st.session_state.lote_fichas)
            col_lote_1.subheader(f"📦 Lote de Trabalho Atual: {qtd_fichas} Ficha(s)")
            if qtd_fichas > 0:
                col_lote_2.download_button("📥 Baixar Lote Completo (.DOCX)", data=gerar_docx_lote(st.session_state.lote_fichas), file_name="lote_fichas.docx")
                if col_lote_2.button("🗑️ Limpar Lote"):
                    st.session_state.lote_fichas = []
                    st.rerun()

        st.markdown("---")
        col_esquerda, col_direita = st.columns(2)

        with col_esquerda:
            st.subheader("1. Metadados & Responsabilidade")
            classificacao = st.text_input("Número de Classificação (CDD ou CDU)", value="610")
            tipo_autor = st.radio("Tipo de Autoria Principal", ["Pessoa Física", "Entidade (Órgão/Instituição)"], horizontal=True)
            autores_lista = []
            entidade_nome = ""
            
            if tipo_autor == "Pessoa Física":
                qtd_autores_input = st.number_input("Quantidade de autores", min_value=0, max_value=10, value=1)
                for i in range(int(qtd_autores_input)):
                    autores_lista.append(st.text_input(f"Autor {i+1} (Nome Sobrenome)", key=f"autor_{i}"))
            else:
                entidade_nome = st.text_input("Nome da Entidade")
                
            titulo = st.text_input("Título da Obra Médica")
            
            st.markdown("---")
            col_resp_1, col_resp_2 = st.columns(2)
            with col_resp_1:
                tem_organizador = st.checkbox("Possui Organizador?")
                organizador_nome, tipo_org, abreviatura_org = "", "", ""
                if tem_organizador:
                    papel = st.selectbox("Função:", ["Organizador", "Coordenador"])
                    organizador_nome = st.text_input("Nome do Responsável")
                    tipo_org, abreviatura_org = ("organizado", "org.") if papel == "Organizador" else ("coordenado", "coord.")
            with col_resp_2:
                tem_tradutor = st.checkbox("Possui Tradutor?")
                tradutor_nome = st.text_input("Nome do Tradutor") if tem_tradutor else ""

            st.markdown("---")
            st.subheader("2. Publicação & Descrição Física")
            edicao = st.text_input("Edição", value="1. ed.")
            editora = st.text_input("Editora")
            cidade = st.text_input("Cidade", value="São Paulo")
            ano = st.text_input("Ano", value="2026")
            paginas = st.text_input("Páginas", value="180")
            tem_colecao = st.checkbox("Faz parte de Coleção?")
            colecao_nome = st.text_input("Nome da Coleção") if tem_colecao else ""
            isbn = st.text_input("ISBN")
            suporte = st.radio("Suporte", ["Impresso", "Digital"], horizontal=True)
            url_acesso = st.text_input("URL / DOI") if suporte == "Digital" else ""

        with col_direita:
            st.subheader("3. Indexação por Assunto (PubMed)")
            # =========================================================================
            # 🔄 UI ATUALIZADA: BUSCA PUBMED EM PORTUGUÊS
            # =========================================================================
            st.markdown("##### 🧬 Pesquisar Literatura Científica no PubMed (Digite em Português)")
            termo_busca_pt = st.text_input("Buscar termo médico ou patologia:")
            
            if termo_busca_pt:
                with st.spinner("Traduzindo e consultando os servidores do PubMed..."):
                    resultados_pubmed = buscar_pubmed_com_traducao(termo_busca_pt)
                
                if resultados_pubmed:
                    st.success(f"Artigos localizados com sucesso!")
                    mapeamento_opcoes = {f"{item['termo']} ({item['id']})": item['termo'] for item in resultados_pubmed}
                    artigo_selecionado = st.selectbox("Selecione o artigo para usar como assunto/referência:", list(mapeamento_opcoes.keys()))
                    
                    if st.button("➕ Vincular Artigo Selecionado"):
                        termo_final = mapeamento_opcoes[artigo_selecionado]
                        if termo_final not in st.session_state.assuntos_selecionados:
                            st.session_state.assuntos_selecionados.append(termo_final)
                            st.rerun()
                else:
                    st.warning("Nenhum artigo correspondente encontrado no PubMed.")

            st.markdown("##### ✍️ Adicionar Assunto Manualmente")
            assunto_manual = st.text_input("Digite um assunto customizado:")
            if st.button("➕ Vincular Assunto Manual"):
                if assunto_manual.strip() and assunto_manual.strip() not in st.session_state.assuntos_selecionados:
                    st.session_state.assuntos_selecionados.append(assunto_manual.strip())
                    st.rerun()

            if st.session_state.assuntos_selecionados:
                st.write("**Assuntos Vinculados:**")
                for idx, ass in enumerate(st.session_state.assuntos_selecionados):
                    col_assunto, col_excluir = st.columns([9, 1])
                    col_assunto.write(f"{idx+1}. {ass}")
                    if col_excluir.button("❌", key=f"rm_{idx}"):
                        st.session_state.assuntos_selecionados.pop(idx)
                        st.rerun()

            st.markdown("---")
            st.subheader("4. Fechamento da Ficha")
            
            entrada_principal, responsabilidade, entrada_por_titulo = formatar_entrada_e_corpo(
                tipo_autor, autores_lista, entidade_nome, titulo, tem_organizador, organizador_nome, tipo_org, tem_tradutor, tradutor_nome
            )
            cutter = calcular_cutter(tipo_autor, autores_lista, entidade_nome, titulo, tem_organizador, organizador_nome)
            dgm = " [recurso eletrônico]" if suporte == "Digital" else ""
            desc_fisica = f"1 recurso online ({paginas} f.) " if suporte == "Digital" else f"{paginas} f."
            bloco_colecao = f" ({colecao_nome.strip()})" if tem_colecao and colecao_nome.strip() else ""
            nota_acesso = f"\n            Modo de acesso: {url_acesso}" if suporte == "Digital" and url_acesso else ""
            isbn_bloco = f"\n            ISBN {isbn}" if isbn.strip() else ""
            
            string_assuntos = " ".join([f"{i+1}. {ass}" for i, ass in enumerate(st.session_state.assuntos_selecionados)])
            rastreabilidade = ""
            romanos = ["I", "II", "III", "IV"]
            r_idx = 0
            if not entrada_por_titulo: 
                rastreabilidade += f" {romanos[r_idx]}. Título."
                r_idx += 1
            if tem_organizador and organizador_nome.strip():
                partes_org = organizador_nome.strip().split()
                rastreabilidade += f" {romanos[r_idx]}. {partes_org[-1].upper()}, {' '.join(partes_org[:-1])}, {abreviatura_org}."
                r_idx += 1

            if entrada_por_titulo:
                txt_ficha = f"{classificacao}\n{cutter}   {titulo.strip()}{dgm} / {responsabilidade}. – {edicao} – {cidade} : {editora}, {ano}.\n            {desc_fisica}.{bloco_colecao}{nota_acesso}{isbn_bloco}\n            \n            {string_assuntos}{rastreabilidade}"
            else:
                txt_ficha = f"{classificacao}\n{cutter}   {entrada_principal}\n            {titulo.strip()}{dgm} / {responsabilidade}. – {edicao} – {cidade} : {editora}, {ano}.\n            {desc_fisica}.{bloco_colecao}{nota_acesso}{isbn_bloco}\n            \n            {string_assuntos}{rastreabilidade}"
                    
            st.text_area("Visualização Normativa", value=txt_ficha, height=240)
            
            if st.button("💾 CONCLUIR FICHA E ENVIAR AO LOTE", disabled=st.session_state["creditos_ativos"] <= 0):
                if titulo.strip():
                    with st.spinner("Processando débito na aba creditos_med..."):
                        try:
                            url_script = st.secrets["URL_SCRIPT_GOOGLE"]
                            # =========================================================================
                            # 🔄 ALTERAÇÃO: PAYLOAD AGORA DIRECIONA EXPLICITAMENTE PARA 'creditos_med'
                            # =========================================================================
                            payload = {
                                "email": st.session_state["usuario_atual"],
                                "acao": "descontar",
                                "aba": "creditos_med"  # Seu script do Google lerá este parâmetro
                            }
                            resposta_google = requests.post(url_script, json=payload, timeout=15)
                            
                            if resposta_google.status_code == 200 and resposta_google.json().get("status") == "sucesso":
                                st.session_state.lote_fichas.append(txt_ficha)
                                st.session_state["creditos_ativos"] -= 1
                                st.session_state.assuntos_selecionados = []
                                st.success("✅ Ficha salva! Crédito debitado da aba creditos_med.")
                                st.rerun()
                            else:
                                st.error("❌ Falha ao computar saldo. Verifique seu script na planilha.")
                        except Exception as e:
                            st.error(f"❌ Erro de conexão: {e}")

    with tab_financeiro:
        st.header("💳 Gestão Financeira e Saldo (Módulo Médico)")
        if st.button("Atualizar meu Saldo"):
            atualizar_saldo_usuario(st.session_state["usuario_atual"])
            st.rerun()

        st.markdown("---")
        st.subheader("📩 Envio de Comprovante")
        with st.form("pix_form_med"):
            st.text_input("E-mail de Cadastro", value=st.session_state["usuario_atual"], disabled=True)
            pacote_escolhido = st.selectbox("Pacote de créditos:", ["30 Fichas (R$ 70,00)", "60 Fichas (R$ 160,00)", "100 Fichas (R$ 240,00)"])
            comprovante = st.file_uploader("Anexe o comprovante", type=["jpg", "png", "jpeg", "pdf"])
            
            if st.form_submit_button("Enviar para Liberação de Saldo Médica"):
                if comprovante:
                    try:
                        tg_token = st.secrets["TELEGRAM_BOT_TOKEN_MED"]
                        tg_chat = st.secrets["TELEGRAM_CHAT_ID_MED"]
                        texto_notificacao = f"🏥 *COMPROVANTE MÉDICO COLETADO!*\n\n📧 *User:* {st.session_state['usuario_atual']}\n💰 *Pacote:* {pacote_escolhido}\n📌 *Alvo:* Aba creditos_med"
                        
                        requests.post(f"https://api.telegram.org/bot{tg_token}/sendPhoto", data={"chat_id": tg_chat, "caption": texto_notificacao, "parse_mode": "Markdown"}, files={"photo": comprovante.getvalue()}, timeout=15)
                        st.success("✅ Comprovante enviado para análise do setor médico!")
                    except Exception as e: st.error(f"Erro: {e}")
