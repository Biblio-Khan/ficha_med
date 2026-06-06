import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

# --- Configurações ---
# Se rodar no Streamlit Cloud, use: API_KEY = st.secrets["API_KEY"]
API_KEY = "SUA_CHAVE_AQUI" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (BibliotecarioBot/1.0)'}

def validar_e_extrair_json(texto):
    """Verifica se o texto é JSON, caso contrário levanta erro explicativo."""
    # Remove lixo inicial e final
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if not match:
        # Se começar com '<', é XML (erro comum da NLM)
        if texto.strip().startswith('<'):
            raise ValueError("A API retornou XML em vez de JSON. Verifique suas permissões de API.")
        raise ValueError("Resposta não contém um objeto JSON.")
    
    try:
        return json.loads(match.group(0).replace('""', '"'))
    except json.JSONDecodeError:
        raise ValueError("Erro ao decodificar o JSON recebido.")

def buscar_mesh(termo_pt):
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 1. Pesquisa
    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 1
    }
    
    try:
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
        data_search = validar_e_extrair_json(res_search.text)
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, "Termo não encontrado."
            
        # 2. Detalhamento
        # Nota: O efetch do MeSH pode ser sensível. Garantimos o formato JSON aqui.
        params_fetch = {"db": "mesh", "id": ids[0], "retmode": "json", "api_key": API_KEY}
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS, timeout=15)
        
        data_fetch = validar_e_extrair_json(res_fetch.text)
        
        # Extração do nome
        results = data_fetch.get("result", {})
        descritor = results.get(ids[0], {}).get("terms", [{}])[0].get("name")
        
        return descritor, None
        
    except Exception as e:
        return None, str(e)

# --- Interface ---
st.set_page_config(page_title="Gerador de Ficha", layout="centered")
st.title("Gerador de Ficha Catalográfica")

termo = st.text_input("Assunto principal:")

if st.button("Buscar Descritor"):
    if termo:
        with st.spinner('Consultando base MeSH...'):
            descritor, erro = buscar_mesh(termo)
            if descritor:
                st.success(f"Descritor oficial: {descritor}")
                st.code(f"1. {descritor}.")
            else:
                st.error(f"Erro: {erro}")
    else:
        st.warning("Preencha o campo.")
