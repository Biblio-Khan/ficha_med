import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

# --- Configurações ---
API_KEY = "SUA_CHAVE_AQUI" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def limpar_json(texto):
    """Remove lixo do início da resposta para evitar erro de parser."""
    return re.sub(r'^[^{]*', '', texto)

def buscar_mesh(termo_pt):
    # 1. Tradução Técnica
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 2. Pesquisa na API do MeSH
    params_search = {
        "db": "mesh",
        "term": termo_en,
        "retmode": "json",
        "api_key": API_KEY
    }
    
    try:
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search)
        data_search = json.loads(limpar_json(res_search.text))
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, "Termo não encontrado na base MeSH."
            
        # 3. Detalhamento do Descritor
        params_fetch = {
            "db": "mesh",
            "id": ids[0],
            "retmode": "json",
            "api_key": API_KEY
        }
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch)
        data_fetch = json.loads(limpar_json(res_fetch.text))
        
        # Extração segura do nome
        descritor = data_fetch.get("result", {}).get(ids[0], {}).get("terms", [{}])[0].get("name")
        return descritor, None
        
    except Exception as e:
        return None, f"Erro na comunicação com a API: {e}"

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina")
st.title("Gerador de Ficha Catalográfica (Área Médica)")

termo_input = st.text_input("Insira o assunto principal para a ficha:")

if st.button("Gerar Assuntos da Ficha"):
    if termo_input:
        with st.spinner('Consultando base MeSH...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success("Assunto validado!")
                ficha_formatada = f"1. {descritor}."
                st.subheader("Bloco de Assuntos na Ficha:")
                st.code(ficha_formatada)
            else:
                st.error(f"Erro: {erro}")
    else:
        st.warning("Por favor, preencha o campo de assunto.")
