import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

# --- Configurações ---
# Se rodar no Streamlit Cloud, use: API_KEY = st.secrets["API_KEY"]
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (BibliotecarioBot/1.0)'}

def limpar_json(texto):
    """Remove lixo ou avisos de texto antes do JSON real."""
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return match.group(0)
    return texto

def buscar_mesh(termo_pt):
    # 1. Tradução Técnica
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 2. Pesquisa na API do MeSH
    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 1
    }
    
    try:
        # Requisição de busca
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
        
        if res_search.status_code != 200:
            return None, f"Erro HTTP {res_search.status_code}: {res_search.text[:50]}"
            
        data_search = json.loads(limpar_json(res_search.text))
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, f"Termo '{termo_en}' não localizado como descritor oficial."
            
        # 3. Detalhamento do Descritor (Fetch)
        mesh_id = ids[0]
        params_fetch = {
            "db": "mesh",
            "id": mesh_id,
            "retmode": "json",
            "api_key": API_KEY
        }
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS, timeout=15)
        
        data_fetch = json.loads(limpar_json(res_fetch.text))
        
        # Extração segura: O retorno do efetch para o banco mesh é uma estrutura de dicionário
        # Onde a chave é o ID do MeSH
        results = data_fetch.get("result", {})
        descritor = results.get(mesh_id, {}).get("terms", [{}])[0].get("name")
        
        return descritor, None
        
    except Exception as e:
        return None, f"Erro crítico: {str(e)}"

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina", layout="centered")
st.title("Gerador de Ficha Catalográfica (Medicina)")

termo_input = st.text_input("Insira o assunto principal (Descritor):")

if st.button("Buscar Descritor"):
    if termo_input:
        with st.spinner('Validando descritor no MeSH...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success("Descritor oficial MeSH encontrado:")
                ficha_formatada = f"1. {descritor}."
                st.code(ficha_formatada)
                st.info("Nota: Este descritor foi validado diretamente na base oficial da NLM (MeSH).")
            else:
                st.error(f"Não foi possível validar o assunto: {erro}")
    else:
        st.warning("Por favor, preencha o campo de assunto.")

