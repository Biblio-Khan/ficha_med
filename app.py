import streamlit as st
import requests
import json
from deep_translator import GoogleTranslator

# --- Configurações ---
# Se usar Streamlit Cloud, substitua por: API_KEY = st.secrets["API_KEY"]
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (BibliotecarioBot/1.0)'}

def limpar_json(texto):
    """Isola o JSON extraindo do primeiro '{' até o último '}'."""
    inicio = texto.find('{')
    fim = texto.rfind('}')
    if inicio != -1 and fim != -1:
        return texto[inicio:fim+1]
    return texto

def buscar_mesh(termo_pt):
    # 1. Tradução
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 2. Pesquisa
    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 1
    }
    
    try:
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
        if res_search.status_code != 200:
            return None, f"Erro HTTP {res_search.status_code}"
            
        data_search = json.loads(limpar_json(res_search.text))
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, f"Termo '{termo_en}' não encontrado."
            
        # 3. Detalhamento
        mesh_id = ids[0]
        params_fetch = {"db": "mesh", "id": mesh_id, "retmode": "json", "api_key": API_KEY}
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS, timeout=15)
        
        data_fetch = json.loads(limpar_json(res_fetch.text))
        
        # O retorno do efetch para mesh é: {"result": {"ID": {"terms": [{"name": "..."}]}}}
        results = data_fetch.get("result", {})
        descritor = results.get(mesh_id, {}).get("terms", [{}])[0].get("name")
        
        return descritor, None
        
    except Exception as e:
        return None, f"Erro na API: {str(e)}"

# --- Interface ---
st.set_page_config(page_title="Gerador de Ficha - Medicina")
st.title("Gerador de Ficha (Medicina)")

termo_input = st.text_input("Assunto principal:")

if st.button("Buscar"):
    if termo_input:
        with st.spinner('Consultando...'):
            descritor, erro = buscar_mesh(termo_input)
            if descritor:
                st.success(f"Descritor encontrado: {descritor}")
                st.code(f"1. {descritor}.")
            else:
                st.error(erro)
    else:
        st.warning("Preencha o campo.")
