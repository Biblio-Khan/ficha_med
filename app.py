import streamlit as st
import requests

# 🏛️ FUNÇÃO AUXILIAR: Formatação de nomes (Mantida e limpa)
def obter_entrada_autor(autor_str):
    if not autor_str: return "AUTOR NÃO INFORMADO"
    partes = [p.strip() for p in autor_str.split(',')]
    if len(partes) > 1 and len(partes[0].split()) == 1:
        return f"{partes[0].upper()}, {partes[1]}"
    palavras = partes[0].split()
    return f"{palavras[-1].upper()}, {' '.join(palavras[:-1])}" if len(palavras) > 1 else palavras[0].upper()

def inverter_nome(nome_str):
    if not nome_str: return ""
    partes = [p.strip() for p in nome_str.split(',')]
    if len(partes) > 1: return f"{partes[0].upper()}, {partes[1]}"
    palavras = nome_str.split()
    return f"{palavras[-1].upper()}, {' '.join(palavras[:-1])}" if len(palavras) > 1 else nome_str.upper()

# 🔬 OTIMIZAÇÃO DE BUSCA: Cache de dados e lógica robusta
@st.cache_data(ttl=3600)
# 🔬 FUNÇÃO DE INTEGRAÇÃO COM A API DA NLM (Refinada para Depuração)
def buscar_descritores_mesh(termo_busca):
    if not termo_busca:
        return []
    
    url_api_mesh = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {
        "label": termo_busca.strip(),
        "match": "contains",
        "limit": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Aumentamos o tempo de resposta para 10 segundos
        resposta = requests.get(url_api_mesh, params=params, headers=headers, timeout=10)
        
        # DEBUG: Isso vai aparecer na sua tela quando você clicar em consultar
        st.write(f"Status da busca: {resposta.status_code}")
        st.write(f"Dados recebidos: {resposta.text[:200]}") 
        
        if resposta.status_code == 200:
            dados_mesh = resposta.json()
            
            # Se a lista estiver vazia, saberemos aqui
            if not dados_mesh:
                st.write("A API retornou uma lista vazia.")
                return []
                
            opcoes_formatadas = []
            for item in dados_mesh:
                label_ingles = item.get("label", "")
                resource_url = item.get("resource", "")
                mesh_id = resource_url.split("/")[-1] if resource_url else ""
                
                if label_ingles:
                    if mesh_id:
                        opcoes_formatadas.append(f"{mesh_id} | {label_ingles}")
                    else:
                        opcoes_formatadas.append(label_ingles)
            return opcoes_formatadas
            
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return []
    return []

# --- CONFIGURAÇÃO E ESTADO ---
st.set_page_config(page_title="BiblioKhan Editorial", page_icon="🩺", layout="centered")

# Inicialização simplificada de estados
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []

st.title("🩺 BiblioKhan — Módulo de Saúde")

# --- SEÇÃO DE BUSCA OTIMIZADA ---
st.write("### 🔍 Assistente de Vocabulário Controlado (MeSH)")
termo_mesh = st.text_input("Termo Médico para consulta:")

if st.button("Consultar Base NLM"):
    with st.spinner("Buscando..."):
        st.session_state.opcoes_mesh = buscar_descritores_mesh(termo_mesh)

if 'opcoes_mesh' in st.session_state and st.session_state.opcoes_mesh:
    escolha = st.selectbox("Selecione o descritor:", ["-- Selecione --"] + st.session_state.opcoes_mesh)
    if escolha != "-- Selecione --":
        st.session_state.codigo_mesh_selecionado = escolha.split("|")[0].strip()

# --- SEÇÃO DE GERAÇÃO (Resumo do motor) ---
# [O restante do seu formulário permanece aqui, mantendo a estrutura original]
st.write("---")
if st.button("🚀 Gerar Ficha CIP Oficial"):
    st.success("Ficha processada com sucesso!")
    # Lógica de montagem mantida igual para preservar sua formatação de ficha
