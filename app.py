import streamlit as st
import requests

# 🏛️ FUNÇÃO AUXILIAR 1: Formata o autor principal para o cabeçalho da ficha (Padrão ABNT/AACR2)
def obter_entrada_autor(autor_str):
    if not autor_str:
        return "AUTOR NÃO INFORMADO"
    
    autor_str = autor_str.strip()
    partes = [p.strip() for p in autor_str.split(',')]
    primeiro_autor = partes[0]
    
    if len(partes) > 1 and len(partes[0].split()) == 1:
        return f"{partes[0].upper()}, {partes[1]}"
        
    palavras = primeiro_autor.split()
    if len(palavras) > 1:
        sobrenome = palavras[-1].upper()
        nomes_proprios = " ".join(palavras[:-1])
        return f"{sobrenome}, {nomes_proprios}"
    
    return primeiro_autor.upper()


# 🏛️ FUNÇÃO AUXILIAR 2: Inverte nomes de colaboradores e deixa o sobrenome em MAIÚSCULO
def inverter_nome(nome_str):
    if not nome_str:
        return ""
    nome_str = nome_str.strip()
    partes = [p.strip() for p in nome_str.split(',')]
    if len(partes) > 1:
        return f"{partes[0].upper()}, {partes[1]}"
        
    palavras = nome_str.split()
    if len(palavras) > 1:
        sobrenome = palavras[-1].upper()
        resto = " ".join(palavras[:-1])
        return f"{sobrenome}, {resto}"
    return nome_str.upper()


# 🔬 FUNÇÃO DE INTEGRAÇÃO COM A API DA NATIONAL LIBRARY OF MEDICINE (NLM MeSH)
def buscar_descritores_mesh(termo_busca):
    if not termo_busca:
        return []
    
    # API Oficial de Sugestão de Descritores da NLM
    url_api_mesh = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {
        "label": termo_busca.strip(),
        "match": "contains",
        "limit": 10
    }
    headers = {
        "User-Agent": "BiblioKhanMedicalBot/1.0 (Contact: seu-email@exemplo.com)"
    }
    
    try:
        resposta = requests.get(url_api_mesh, params=params, headers=headers, timeout=5)
        if resposta.status_code == 200:
            dados_mesh = resposta.json()
            opcoes_formatadas = []
            
            for item in dados_mesh:
                label_ingles = item.get("label", "")
                resource_url = item.get("resource", "")
                # Extrai o ID único do MeSH (ex: D002309) a partir do link do recurso
                mesh_id = resource_url.split("/")[-1] if resource_url else ""
                
                if label_ingles:
                    if mesh_id:
                        opcoes_formatadas.append(f"{mesh_id} | {label_ingles}")
                    else:
                        opcoes_formatadas.append(label_ingles)
            return opcoes_formatadas
    except Exception:
        return []
    return []


# 🏛️ DICIONÁRIO DE MAPEAMENTO: Configura os textos CIP/ISBD para o corpo do título
MAPA_FUNCOES = {
    "Prefácio": {"texto": "prefácio de"},
    "Introdução": {"texto": "introdução de"},
    "Notas": {"texto": "notas de"},
    "Posfácio": {"texto": "posfácio de"},
    "Organização": {"texto": "organização de"},
    "Ilustração": {"texto": "ilustrações de"},
    "Coordenação": {"texto": "coordenação de"},
    "Revisão": {"texto": "revisão de"}
}


# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BiblioKhan Editorial - Módulo Médico", page_icon="🩺", layout="centered")

# Inicialização de todos os estados de sessão básicos
if 'titulo' not in st.session_state: st.session_state.titulo = ""
if 'titulo_original' not in st.session_state: st.session_state.titulo_original = ""
if 'autor' not in st.session_state: st.session_state.autor = ""
if 'tradutor' not in st.session_state: st.session_state.tradutor = ""
if 'editora' not in st.session_state: st.session_state.editora = ""
if 'ano' not in st.session_state: st.session_state.ano = ""
if 'paginas' not in st.session_state: st.session_state.paginas = ""
if 'dimensoes' not in st.session_state: st.session_state.dimensoes = ""
if 'cidade' not in st.session_state: st.session_state.cidade = ""
if 'assuntos' not in st.session_state: st.session_state.assuntos = ""
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []
if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []
if 'codigo_mesh_selecionado' not in st.session_state: st.session_state.codigo_mesh_selecionado = ""

st.title("🩺 BiblioKhan — Módulo de Saúde & Medicina")
st.subheader("Gerador de Fichas Catalográficas com Integração NLM MeSH")
st.write("Assistente especializado para bibliotecas médicas, hospitais e publicações científicas.")

st.markdown("---")

# --- SEÇÃO 1: BUSCA POR ISBN ---
st.write("### 🔍 Preenchimento Automático por ISBN")
isbn_input = st.text_input("Digite o ISBN do livro (apenas números):")

if st.button("Buscar Dados do Livro", type="primary"):
    if isbn_input:
        isbn_limpo = isbn_input.replace("-", "").replace(".", "").replace(" ", "").strip()
        encontrou = False
        
        st.session_state.titulo = ""
        st.session_state.titulo_original = ""
        st.session_state.autor = ""
        st.session_state.tradutor = ""
        st.session_state.colaboradores = []
        st.session_state.editora = ""
        st.session_state.ano = ""
        st.session_state.paginas = ""
        st.session_state.dimensoes = ""
        st.session_state.cidade = ""
        st.session_state.assuntos = ""
        
        with st.spinner("Buscando na base nacional..."):
            try:
                url_brasil = f"https://brasilapi.com.br/api/isbn/v1/{isbn_limpo}"
                resposta_brasil = requests.get(url_brasil, timeout=5)
                if resposta_brasil.status_code == 200:
                    dados = resposta_brasil.json()
                    st.session_state.titulo = dados.get('title', '')
                    st.session_state.editora = dados.get('publisher', '')
                    st.session_state.ano = str(dados.get('year', ''))
                    
                    paginas_api = dados.get('page_count', dados.get('pages', ''))
                    st.session_state.paginas = f"{paginas_api} p." if paginas_api else ""
                    
                    autores = dados.get('authors', [])
                    st.session_state.autor = ", ".join(autores) if autores else ""
                    
                    subjs = dados.get('subjects', [])
                    if subjs:
                        texto_assuntos = ""
                        for idx, s in enumerate(subjs):
                            texto_assuntos += f"{idx+1}. {s.strip().capitalize()}. "
                        st.session_state.assuntos = f"{texto_assuntos}I. Título."
                    encontrou = True
            except Exception:
                pass

        if not encontrou:
            with st.spinner("Buscando na base global..."):
                try:
                    url_google = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
                    resposta_google = requests.get(url_google, timeout=5)
                    if resposta_google.status_code == 200:
                        dados_google = resposta_google.json()
                        if "items" in dados_google and len(dados_google["items"]) > 0:
                            info_livro = dados_google["items"][0]["volumeInfo"]
                            st.session_state.titulo = info_livro.get('title', '')
                            st.session_state.editora = info_livro.get('publisher', '')
                            data_pub = info_livro.get('publishedDate', '')
                            st.session_state.ano = data_pub[:4] if data_pub else ""
                            paginas_api = info_livro.get('pageCount', '')
                            st.session_state.paginas = f"{paginas_api} p." if paginas_api else ""
                            
                            autores = info_livro.get('authors', [])
                            st.session_state.autor = ", ".join(autores) if autores else ""
                            encontrou = True
                except Exception:
                    pass

        if encontrou:
            st.success("✅ Livro localizado! Revise ou complete as informações abaixo.")
        else:
            st.error("❌ ISBN não localizado. Digite as informações manualmente nos campos abaixo.")
                    
st.markdown("---")

# --- SEÇÃO 2: FORMULÁRIO COMPLETO E EDITÁVEL ---
st.write("### 📝 Informações da Publicação")

col_t1, col_t2 = st.columns(2)
with col_t1:
    titulo = st.text_input("Título da Edição Nacional:", value=st.session_state.titulo)
with col_t2:
    titulo_original = st.text_input("Título Original (Obra estrangeira):", value=st.session_state.titulo_original)

col_r1, col_r2 = st.columns(2)
with col_r1:
    autor = st.text_input("Autor(es) Principal(is):", value=st.session_state.autor)
with col_r2:
    tradutor = st.text_input("Nome do Tradutor(a) (Opcional):", value=st.session_state.tradutor)

# Seção Dinâmica de Colaboradores
st.write("#### ➕ Outros Créditos Opcionais (Introdução, Prefácio, Notas, etc.)")

for i, colab in enumerate(st.session_state.colaboradores):
    c_nome, c_func, c_btn = st.columns([2, 1.5, 0.4])
    with c_nome:
        colab['nome'] = st.text_input(f"Nome do Colaborador {i+1}", value=colab['nome'], key=f"colab_nome_{i}")
    with c_func:
        opcoes = list(MAPA_FUNCOES.keys())
        idx_atual = opcoes.index(colab['funcao']) if colab['funcao'] in opcoes else 0
        colab['funcao'] = st.selectbox(f"Função do Colaborador {i+1}", options=opcoes, index=idx_atual, key=f"colab_func_{i}")
    with c_btn:
        st.write("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("❌", key=f"colab_del_{i}"):
            st.session_state.colaboradores.pop(i)
            st.rerun()

if st.button("➕ Adicionar Colaborador", type="secondary"):
    st.session_state.colaboradores.append({"nome": "", "funcao": "Prefácio"})
    st.rerun()

st.write("") 

col_pub1, col_pub2, col_pub3 = st.columns([2, 2, 1])
with col_pub1:
    cidade = st.text_input("Cidade de Publicação:", value=st.session_state.cidade, placeholder="Ex: São Paulo")
with col_pub2:
    editora = st.text_input("Editora:", value=st.session_state.editora)
with col_pub3:
    ano = st.text_input("Ano:", value=st.session_state.ano)

col1, col2 = st.columns(2)
with col1:
    paginas = st.text_input("Número de Páginas:", value=st.session_state.paginas, placeholder="Ex: 250 p.")
    dimensoes = st.text_input("Dimensões do Livro:", value=st.session_state.dimensoes, placeholder="Ex: 23")
with col2:
    tipo_classificacao = st.selectbox("Sistema de Classificação:", ["NLM (Medicina)", "CDD", "CDU"])
    
    # 🎛️ INTEGRAÇÃO INTERNACIONAL COM A API DA NATIONAL LIBRARY OF MEDICINE
    st.write("**🔍 Assistente de Vocabulário Controlado (MeSH/NLM)**")
    st.caption("Insira o termo em inglês para consultar a base global médica.")
    
    col_busca1, col_busca2 = st.columns([3, 1])
    with col_busca1:
        termo_mesh = st.text_input("Termo Médico (Ex: Cardiology, Diabetes):", placeholder="Cardiology", label_visibility="collapsed")
    with col_busca2:
        executar_busca_mesh = st.button("Consultar NLM")
        
    if executar_busca_mesh and termo_mesh:
        with st.spinner("A consultar os servidores da NLM nos EUA..."):
            st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
            if not st.session_state.opcoes_mesh:
                st.warning("Nenhum descritor oficial encontrado para este termo.")
    
    # Se encontrar descritores, mostra a lista para o utilizador escolher
    if st.session_state.opcoes_mesh:
        escolha_mesh = st.selectbox("Selecione o descritor oficial:", ["-- Escolha um termo validado --"] + st.session_state.opcoes_mesh)
        if escolha_mesh != "-- Escolha um termo validado --":
            if " | " in escolha_mesh:
                # Salva o código ID do MeSH (ex: D002309)
                st.session_state.codigo_mesh_selecionado = escolha_mesh.split("|")[0].strip()
            else:
                st.session_state.codigo_mesh_selecionado = escolha_mesh

    # Campo final do número de classificação (preenchido manualmente ou via clique da API)
    num_classificacao = st.text_input(f"Código de Classificação ({tipo_classificacao}):", value=st.session_state.codigo_mesh_selecionado, placeholder="Ex: WZ 100 ou 616.12")

assuntos = st.text_area("Assuntos e Fichas Secundárias (Editável):", value=st.session_state.assuntos, placeholder="Ex: 1. Cardiologia. 2. Doenças Cardiovasculares. I. Título.")

st.markdown("---")

# --- SEÇÃO 3: MOTOR DE GERAÇÃO BLINDADO ---
if st.button("🚀 Gerar Ficha CIP Oficial", type="secondary"):
    if not titulo or not autor:
        st.error("Erro: O preenchimento do Título e do Autor é obrigatório.")
    else:
        st.success("Ficha Catalográfica médica gerada com sucesso!")
        
        entrada_autor_formatada = obter_entrada_autor(autor)
        cidade_str = cidade.strip() if cidade else "[s.l.]"
        editora_str = editora.strip() if editora else "[s.n.]"
        ano_str = ano.strip() if ano else "[s.d.]"
        isbn_str = isbn_input.strip() if isbn_input else "Não informado"
        num_class_str = num_classificacao.strip() if num_classificacao else "WZ 100"
        
        pag_raw = paginas.strip()
        dim_raw = dimensoes.strip()
        partes_fisicas = []
        
        if pag_raw:
            partes_fisicas.append(pag_raw)
            
        if dim_raw:
            if not (dim_raw.endswith("cm") or dim_raw.endswith("cm.")):
                dim_raw += " cm."
            elif dim_raw.endswith("cm"):
                dim_raw += "."
            partes_fisicas.append(dim_raw)
            
        html_linha_fisica = ""
        if partes_fisicas:
            linha_fisica_formatada = " ; ".join(partes_fisicas)
            html_linha_fisica = f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px;">{linha_fisica_formatada}</p>'
        
        linha_titulo_resposabilidade = f"{titulo.strip()} / {autor.strip()}"
        
        if tradutor.strip():
            linha_titulo_resposabilidade += f" ; tradução de {tradutor.strip()}"
            
        for colab in st.session_state.colaboradores:
            nome_c = colab['nome'].strip()
            func_c = colab['funcao']
            if nome_c and func_c in MAPA_FUNCOES:
                texto_conector = MAPA_FUNCOES[func_c]["texto"]
                linha_titulo_resposabilidade += f" ; {texto_conector} {nome_c}"
                
        linha_titulo_resposabilidade += f". &ndash; {cidade_str} : {editora_str}, {ano_str}."
        
        html_titulo_original = ""
        if titulo_original.strip():
            html_titulo_original = f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px;">Título original: {titulo_original.strip()}</p>'
            
        assuntos_str = assuntos.strip() if assuntos else "1. Medicina. I. Título."
        romanos_lista = ["I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X."]
        
        def obter_proximo_romano(texto_atual):
            idx = 0
            for i, r in enumerate(romanos_lista):
                if r in texto_atual:
                    idx = i + 1
            return romanos_lista[idx] if idx < len(romanos_lista) else "X."

        if tradutor.strip():
            nome_inv_trad = inverter_nome(tradutor)
            if nome_inv_trad.lower() not in assuntos_str.lower() and tradutor.strip().lower() not in assuntos_str.lower():
                romano_disponivel = obter_proximo_romano(assuntos_str)
                if not assuntos_str.endswith('.'): assuntos_str += "."
                assuntos_str += f" {romano_disponivel} {nome_inv_trad} (trad.)."

        for colab in st.session_state.colaboradores:
            nome_c = colab['nome'].strip()
            if nome_c:
                nome_inv_colab = inverter_nome(nome_c)
                if nome_inv_colab.lower() not in assuntos_str.lower() and nome_c.lower() not in assuntos_str.lower():
                    romano_disponivel = obter_proximo_romano(assuntos_str)
                    if not assuntos_str.endswith('.'): assuntos_str += "."
                    assuntos_str += f" {romano_disponivel} {nome_inv_colab}."

        if not assuntos_str.endswith('.'):
            assuntos_str += "."

        html_ficha = (
            f'<div style="border: 1px solid #000; padding: 25px; font-family: \'Courier New\', Courier, monospace; font-size: 13px; background-color: #fff; color: #000; max-width: 550px; margin: 20px auto; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); line-height: 1.5;">'
            f'<p style="text-align: center; margin-top: 0; margin-bottom: 25px; font-weight: bold; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Dados Internacionais de Catalogação na Publicação (CIP)</p>'
            f'<div style="margin-left: 50px; text-align: left; padding-right: 20px;">'
            f'<p style="margin: 0 0 6px 0; padding: 0;">{entrada_autor_formatada}.</p>'
            f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px; text-align: justify;">{linha_titulo_resposabilidade}</p>'
            f'{html_linha_fisica}'
            f'{html_titulo_original}'
            f'<p style="margin: 0 0 12px 0; padding: 0; text-indent: 30px;">ISBN {isbn_str}</p>'
            f'<p style="margin: 0; padding: 0; text-indent: 30px; text-align: justify;">{assuntos_str}</p>'
            f'</div>'
            f'<div style="margin-top: 30px; border-top: 1px solid #000; padding-top: 8px; display: flex; justify-content: flex-end; font-size: 12px; padding-left: 50px; padding-right: 50px;">'
            f'<span>{tipo_classificacao}: {num_class_str}</span>'
            f'</div>'
            f'</div>'
        )
        
        st.markdown(html_ficha, unsafe_allow_html
import streamlit as st
import requests

# 🏛️ FUNÇÃO AUXILIAR 1: Formata o autor principal para o cabeçalho da ficha (Padrão ABNT/AACR2)
def obter_entrada_autor(autor_str):
    if not autor_str:
        return "AUTOR NÃO INFORMADO"
    
    autor_str = autor_str.strip()
    partes = [p.strip() for p in autor_str.split(',')]
    primeiro_autor = partes[0]
    
    if len(partes) > 1 and len(partes[0].split()) == 1:
        return f"{partes[0].upper()}, {partes[1]}"
        
    palavras = primeiro_autor.split()
    if len(palavras) > 1:
        sobrenome = palavras[-1].upper()
        nomes_proprios = " ".join(palavras[:-1])
        return f"{sobrenome}, {nomes_proprios}"
    
    return primeiro_autor.upper()


# 🏛️ FUNÇÃO AUXILIAR 2: Inverte nomes de colaboradores e deixa o sobrenome em MAIÚSCULO
def inverter_nome(nome_str):
    if not nome_str:
        return ""
    nome_str = nome_str.strip()
    partes = [p.strip() for p in nome_str.split(',')]
    if len(partes) > 1:
        return f"{partes[0].upper()}, {partes[1]}"
        
    palavras = nome_str.split()
    if len(palavras) > 1:
        sobrenome = palavras[-1].upper()
        resto = " ".join(palavras[:-1])
        return f"{sobrenome}, {resto}"
    return nome_str.upper()


# 🔬 FUNÇÃO DE INTEGRAÇÃO COM A API DA NATIONAL LIBRARY OF MEDICINE (NLM MeSH)
def buscar_descritores_mesh(termo_busca):
    if not termo_busca:
        return []
    
    # API Oficial de Sugestão de Descritores da NLM
    url_api_mesh = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {
        "label": termo_busca.strip(),
        "match": "contains",
        "limit": 10
    }
    headers = {
        "User-Agent": "BiblioKhanMedicalBot/1.0 (Contact: seu-email@exemplo.com)"
    }
    
    try:
        resposta = requests.get(url_api_mesh, params=params, headers=headers, timeout=5)
        if resposta.status_code == 200:
            dados_mesh = resposta.json()
            opcoes_formatadas = []
            
            for item in dados_mesh:
                label_ingles = item.get("label", "")
                resource_url = item.get("resource", "")
                # Extrai o ID único do MeSH (ex: D002309) a partir do link do recurso
                mesh_id = resource_url.split("/")[-1] if resource_url else ""
                
                if label_ingles:
                    if mesh_id:
                        opcoes_formatadas.append(f"{mesh_id} | {label_ingles}")
                    else:
                        opcoes_formatadas.append(label_ingles)
            return opcoes_formatadas
    except Exception:
        return []
    return []


# 🏛️ DICIONÁRIO DE MAPEAMENTO: Configura os textos CIP/ISBD para o corpo do título
MAPA_FUNCOES = {
    "Prefácio": {"texto": "prefácio de"},
    "Introdução": {"texto": "introdução de"},
    "Notas": {"texto": "notas de"},
    "Posfácio": {"texto": "posfácio de"},
    "Organização": {"texto": "organização de"},
    "Ilustração": {"texto": "ilustrações de"},
    "Coordenação": {"texto": "coordenação de"},
    "Revisão": {"texto": "revisão de"}
}


# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BiblioKhan Editorial - Módulo Médico", page_icon="🩺", layout="centered")

# Inicialização de todos os estados de sessão básicos
if 'titulo' not in st.session_state: st.session_state.titulo = ""
if 'titulo_original' not in st.session_state: st.session_state.titulo_original = ""
if 'autor' not in st.session_state: st.session_state.autor = ""
if 'tradutor' not in st.session_state: st.session_state.tradutor = ""
if 'editora' not in st.session_state: st.session_state.editora = ""
if 'ano' not in st.session_state: st.session_state.ano = ""
if 'paginas' not in st.session_state: st.session_state.paginas = ""
if 'dimensoes' not in st.session_state: st.session_state.dimensoes = ""
if 'cidade' not in st.session_state: st.session_state.cidade = ""
if 'assuntos' not in st.session_state: st.session_state.assuntos = ""
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []
if 'opcoes_mesh' not in st.session_state: st.session_state.opcoes_mesh = []
if 'codigo_mesh_selecionado' not in st.session_state: st.session_state.codigo_mesh_selecionado = ""

st.title("🩺 BiblioKhan — Módulo de Saúde & Medicina")
st.subheader("Gerador de Fichas Catalográficas com Integração NLM MeSH")
st.write("Assistente especializado para bibliotecas médicas, hospitais e publicações científicas.")

st.markdown("---")

# --- SEÇÃO 1: BUSCA POR ISBN ---
st.write("### 🔍 Preenchimento Automático por ISBN")
isbn_input = st.text_input("Digite o ISBN do livro (apenas números):")

if st.button("Buscar Dados do Livro", type="primary"):
    if isbn_input:
        isbn_limpo = isbn_input.replace("-", "").replace(".", "").replace(" ", "").strip()
        encontrou = False
        
        st.session_state.titulo = ""
        st.session_state.titulo_original = ""
        st.session_state.autor = ""
        st.session_state.tradutor = ""
        st.session_state.colaboradores = []
        st.session_state.editora = ""
        st.session_state.ano = ""
        st.session_state.paginas = ""
        st.session_state.dimensoes = ""
        st.session_state.cidade = ""
        st.session_state.assuntos = ""
        
        with st.spinner("Buscando na base nacional..."):
            try:
                url_brasil = f"https://brasilapi.com.br/api/isbn/v1/{isbn_limpo}"
                resposta_brasil = requests.get(url_brasil, timeout=5)
                if resposta_brasil.status_code == 200:
                    dados = resposta_brasil.json()
                    st.session_state.titulo = dados.get('title', '')
                    st.session_state.editora = dados.get('publisher', '')
                    st.session_state.ano = str(dados.get('year', ''))
                    
                    paginas_api = dados.get('page_count', dados.get('pages', ''))
                    st.session_state.paginas = f"{paginas_api} p." if paginas_api else ""
                    
                    autores = dados.get('authors', [])
                    st.session_state.autor = ", ".join(autores) if autores else ""
                    
                    subjs = dados.get('subjects', [])
                    if subjs:
                        texto_assuntos = ""
                        for idx, s in enumerate(subjs):
                            texto_assuntos += f"{idx+1}. {s.strip().capitalize()}. "
                        st.session_state.assuntos = f"{texto_assuntos}I. Título."
                    encontrou = True
            except Exception:
                pass

        if not encontrou:
            with st.spinner("Buscando na base global..."):
                try:
                    url_google = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
                    resposta_google = requests.get(url_google, timeout=5)
                    if resposta_google.status_code == 200:
                        dados_google = resposta_google.json()
                        if "items" in dados_google and len(dados_google["items"]) > 0:
                            info_livro = dados_google["items"][0]["volumeInfo"]
                            st.session_state.titulo = info_livro.get('title', '')
                            st.session_state.editora = info_livro.get('publisher', '')
                            data_pub = info_livro.get('publishedDate', '')
                            st.session_state.ano = data_pub[:4] if data_pub else ""
                            paginas_api = info_livro.get('pageCount', '')
                            st.session_state.paginas = f"{paginas_api} p." if paginas_api else ""
                            
                            autores = info_livro.get('authors', [])
                            st.session_state.autor = ", ".join(autores) if autores else ""
                            encontrou = True
                except Exception:
                    pass

        if encontrou:
            st.success("✅ Livro localizado! Revise ou complete as informações abaixo.")
        else:
            st.error("❌ ISBN não localizado. Digite as informações manualmente nos campos abaixo.")
                    
st.markdown("---")

# --- SEÇÃO 2: FORMULÁRIO COMPLETO E EDITÁVEL ---
st.write("### 📝 Informações da Publicação")

col_t1, col_t2 = st.columns(2)
with col_t1:
    titulo = st.text_input("Título da Edição Nacional:", value=st.session_state.titulo)
with col_t2:
    titulo_original = st.text_input("Título Original (Obra estrangeira):", value=st.session_state.titulo_original)

col_r1, col_r2 = st.columns(2)
with col_r1:
    autor = st.text_input("Autor(es) Principal(is):", value=st.session_state.autor)
with col_r2:
    tradutor = st.text_input("Nome do Tradutor(a) (Opcional):", value=st.session_state.tradutor)

# Seção Dinâmica de Colaboradores
st.write("#### ➕ Outros Créditos Opcionais (Introdução, Prefácio, Notas, etc.)")

for i, colab in enumerate(st.session_state.colaboradores):
    c_nome, c_func, c_btn = st.columns([2, 1.5, 0.4])
    with c_nome:
        colab['nome'] = st.text_input(f"Nome do Colaborador {i+1}", value=colab['nome'], key=f"colab_nome_{i}")
    with c_func:
        opcoes = list(MAPA_FUNCOES.keys())
        idx_atual = opcoes.index(colab['funcao']) if colab['funcao'] in opcoes else 0
        colab['funcao'] = st.selectbox(f"Função do Colaborador {i+1}", options=opcoes, index=idx_atual, key=f"colab_func_{i}")
    with c_btn:
        st.write("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("❌", key=f"colab_del_{i}"):
            st.session_state.colaboradores.pop(i)
            st.rerun()

if st.button("➕ Adicionar Colaborador", type="secondary"):
    st.session_state.colaboradores.append({"nome": "", "funcao": "Prefácio"})
    st.rerun()

st.write("") 

col_pub1, col_pub2, col_pub3 = st.columns([2, 2, 1])
with col_pub1:
    cidade = st.text_input("Cidade de Publicação:", value=st.session_state.cidade, placeholder="Ex: São Paulo")
with col_pub2:
    editora = st.text_input("Editora:", value=st.session_state.editora)
with col_pub3:
    ano = st.text_input("Ano:", value=st.session_state.ano)

col1, col2 = st.columns(2)
with col1:
    paginas = st.text_input("Número de Páginas:", value=st.session_state.paginas, placeholder="Ex: 250 p.")
    dimensoes = st.text_input("Dimensões do Livro:", value=st.session_state.dimensoes, placeholder="Ex: 23")
with col2:
    tipo_classificacao = st.selectbox("Sistema de Classificação:", ["NLM (Medicina)", "CDD", "CDU"])
    
    # 🎛️ INTEGRAÇÃO INTERNACIONAL COM A API DA NATIONAL LIBRARY OF MEDICINE
    st.write("**🔍 Assistente de Vocabulário Controlado (MeSH/NLM)**")
    st.caption("Insira o termo em inglês para consultar a base global médica.")
    
    col_busca1, col_busca2 = st.columns([3, 1])
    with col_busca1:
        termo_mesh = st.text_input("Termo Médico (Ex: Cardiology, Diabetes):", placeholder="Cardiology", label_visibility="collapsed")
    with col_busca2:
        executar_busca_mesh = st.button("Consultar NLM")
        
    if executar_busca_mesh and termo_mesh:
        with st.spinner("A consultar os servidores da NLM nos EUA..."):
            st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)
            if not st.session_state.opcoes_mesh:
                st.warning("Nenhum descritor oficial encontrado para este termo.")
    
    # Se encontrar descritores, mostra a lista para o utilizador escolher
    if st.session_state.opcoes_mesh:
        escolha_mesh = st.selectbox("Selecione o descritor oficial:", ["-- Escolha um termo validado --"] + st.session_state.opcoes_mesh)
        if escolha_mesh != "-- Escolha um termo validado --":
            if " | " in escolha_mesh:
                # Salva o código ID do MeSH (ex: D002309)
                st.session_state.codigo_mesh_selecionado = escolha_mesh.split("|")[0].strip()
            else:
                st.session_state.codigo_mesh_selecionado = escolha_mesh

    # Campo final do número de classificação (preenchido manualmente ou via clique da API)
    num_classificacao = st.text_input(f"Código de Classificação ({tipo_classificacao}):", value=st.session_state.codigo_mesh_selecionado, placeholder="Ex: WZ 100 ou 616.12")

assuntos = st.text_area("Assuntos e Fichas Secundárias (Editável):", value=st.session_state.assuntos, placeholder="Ex: 1. Cardiologia. 2. Doenças Cardiovasculares. I. Título.")

st.markdown("---")

# --- SEÇÃO 3: MOTOR DE GERAÇÃO BLINDADO ---
if st.button("🚀 Gerar Ficha CIP Oficial", type="secondary"):
    if not titulo or not autor:
        st.error("Erro: O preenchimento do Título e do Autor é obrigatório.")
    else:
        st.success("Ficha Catalográfica médica gerada com sucesso!")
        
        entrada_autor_formatada = obter_entrada_autor(autor)
        cidade_str = cidade.strip() if cidade else "[s.l.]"
        editora_str = editora.strip() if editora else "[s.n.]"
        ano_str = ano.strip() if ano else "[s.d.]"
        isbn_str = isbn_input.strip() if isbn_input else "Não informado"
        num_class_str = num_classificacao.strip() if num_classificacao else "WZ 100"
        
        pag_raw = paginas.strip()
        dim_raw = dimensoes.strip()
        partes_fisicas = []
        
        if pag_raw:
            partes_fisicas.append(pag_raw)
            
        if dim_raw:
            if not (dim_raw.endswith("cm") or dim_raw.endswith("cm.")):
                dim_raw += " cm."
            elif dim_raw.endswith("cm"):
                dim_raw += "."
            partes_fisicas.append(dim_raw)
            
        html_linha_fisica = ""
        if partes_fisicas:
            linha_fisica_formatada = " ; ".join(partes_fisicas)
            html_linha_fisica = f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px;">{linha_fisica_formatada}</p>'
        
        linha_titulo_resposabilidade = f"{titulo.strip()} / {autor.strip()}"
        
        if tradutor.strip():
            linha_titulo_resposabilidade += f" ; tradução de {tradutor.strip()}"
            
        for colab in st.session_state.colaboradores:
            nome_c = colab['nome'].strip()
            func_c = colab['funcao']
            if nome_c and func_c in MAPA_FUNCOES:
                texto_conector = MAPA_FUNCOES[func_c]["texto"]
                linha_titulo_resposabilidade += f" ; {texto_conector} {nome_c}"
                
        linha_titulo_resposabilidade += f". &ndash; {cidade_str} : {editora_str}, {ano_str}."
        
        html_titulo_original = ""
        if titulo_original.strip():
            html_titulo_original = f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px;">Título original: {titulo_original.strip()}</p>'
            
        assuntos_str = assuntos.strip() if assuntos else "1. Medicina. I. Título."
        romanos_lista = ["I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X."]
        
        def obter_proximo_romano(texto_atual):
            idx = 0
            for i, r in enumerate(romanos_lista):
                if r in texto_atual:
                    idx = i + 1
            return romanos_lista[idx] if idx < len(romanos_lista) else "X."

        if tradutor.strip():
            nome_inv_trad = inverter_nome(tradutor)
            if nome_inv_trad.lower() not in assuntos_str.lower() and tradutor.strip().lower() not in assuntos_str.lower():
                romano_disponivel = obter_proximo_romano(assuntos_str)
                if not assuntos_str.endswith('.'): assuntos_str += "."
                assuntos_str += f" {romano_disponivel} {nome_inv_trad} (trad.)."

        for colab in st.session_state.colaboradores:
            nome_c = colab['nome'].strip()
            if nome_c:
                nome_inv_colab = inverter_nome(nome_c)
                if nome_inv_colab.lower() not in assuntos_str.lower() and nome_c.lower() not in assuntos_str.lower():
                    romano_disponivel = obter_proximo_romano(assuntos_str)
                    if not assuntos_str.endswith('.'): assuntos_str += "."
                    assuntos_str += f" {romano_disponivel} {nome_inv_colab}."

        if not assuntos_str.endswith('.'):
            assuntos_str += "."

        html_ficha = (
            f'<div style="border: 1px solid #000; padding: 25px; font-family: \'Courier New\', Courier, monospace; font-size: 13px; background-color: #fff; color: #000; max-width: 550px; margin: 20px auto; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); line-height: 1.5;">'
            f'<p style="text-align: center; margin-top: 0; margin-bottom: 25px; font-weight: bold; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Dados Internacionais de Catalogação na Publicação (CIP)</p>'
            f'<div style="margin-left: 50px; text-align: left; padding-right: 20px;">'
            f'<p style="margin: 0 0 6px 0; padding: 0;">{entrada_autor_formatada}.</p>'
            f'<p style="margin: 0 0 6px 0; padding: 0; text-indent: 30px; text-align: justify;">{linha_titulo_resposabilidade}</p>'
            f'{html_linha_fisica}'
            f'{html_titulo_original}'
            f'<p style="margin: 0 0 12px 0; padding: 0; text-indent: 30px;">ISBN {isbn_str}</p>'
            f'<p style="margin: 0; padding: 0; text-indent: 30px; text-align: justify;">{assuntos_str}</p>'
            f'</div>'
            f'<div style="margin-top: 30px; border-top: 1px solid #000; padding-top: 8px; display: flex; justify-content: flex-end; font-size: 12px; padding-left: 50px; padding-right: 50px;">'
            f'<span>{tipo_classificacao}: {num_class_str}</span>'
            f'</div>'
            f'</div>'
        )
        
        st.markdown(html_ficha, unsafe_allow_html=true)
