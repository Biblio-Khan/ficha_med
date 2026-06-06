import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

API_KEY = "SUA_CHAVE_AQUI" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (BibliotecarioBot/1.0)'}

def extrair_json_seguro(texto):
    # Corrige aspas duplicadas que vêm do NCBI
    texto_limpo = texto.replace('""', '"')
    match = re.search(r'\{.*\}', texto_limpo, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("JSON inválido.")

def buscar_mesh(termo_pt):
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 1
    }
    
    # 1. Busca
    res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
    data_search = extrair_json_seguro(res_search.text)
    ids = data_search.get("esearchresult", {}).get("idlist", [])
    
    if not ids:
        return None, "Termo não encontrado."
        
    # 2. Detalhes
    params_fetch = {"db": "mesh", "id": ids[0], "retmode": "json", "api_key": API_KEY}
    res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS, timeout=15)
    
    data_fetch = extrair_json_seguro(res_fetch.text)
    
    # Extração
    descritor = data_fetch.get("result", {}).get(ids[0], {}).get("terms", [{}])[0].get("name")
    return descritor, None

# Interface (mantida igual)
st.title("Gerador de Ficha Catalográfica")
termo = st.text_input("Assunto principal:")
if st.button("Buscar"):
    if termo:
        descritor, erro = buscar_mesh(termo)
        if descritor:
            st.success(f"Descritor: {descritor}")
            st.code(f"1. {descritor}.")
        else:
            st.error(erro)
