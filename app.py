import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

# --- Configurações ---
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
# User-Agent para evitar bloqueios de segurança do NCBI
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) BibliotecarioBot/1.0'}

def limpar_json(texto):
    """Remove caracteres estranhos antes do JSON."""
    return re.sub(r'^[^{]*', '', texto)

def buscar_mesh(termo_pt):
    # 1. Tradução
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 2. Pesquisa na API do MeSH com Tag [MeSH Terms]
    # A tag garante busca no vocabulário controlado
    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 1
    }
    
    try:
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS)
        data_search = json.loads(limpar_json(res_search.text))
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, f"Termo '{termo_en}' não localizado como descritor oficial."
            
        # 3. Detalhamento (Fetch)
        mesh_id = ids[0]
        params_fetch = {
            "db": "mesh",
            "id": mesh_id,
            "retmode": "json",
            "api_key": API_KEY
        }
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS)
        data_fetch = json.loads(limpar_json(res_fetch.text))
        
        # Extração do nome oficial
        descritor = data_fetch.get("result", {}).get(mesh_id, {}).get("terms", [{}])[0].get("name")
        return descritor, None
        
    except Exception as e:
        return None, f"Erro na comunicação com a API: {str(e)}"

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina")
st.title("Gerador de Ficha Catalográfica (Área Médica)")

termo_input = st.text_input("Insira o assunto principal:")

if st.button("Buscar Descritor"):
    if termo_input:
        with st.spinner('Validando descritor no MeSH...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success("Descritor encontrado!")
                ficha_formatada = f"1. {descritor}."
                st.subheader("Bloco de Assuntos na Ficha:")
                st.code(ficha_formatada)
            else:
                st.error(erro)
    else:
        st.warning("Por favor, digite um assunto.")

