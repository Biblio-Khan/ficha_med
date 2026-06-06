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
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    params_search = {
        "db": "mesh",
        "term": f"{termo_en}[MeSH Terms]",
        "retmode": "json",
        "api_key": API_KEY
    }
    
    # Adicionamos timeout para não travar o streamlit
    res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=10)
    
    # DEBUG: Se a resposta estiver vazia, vamos saber agora
    if not res_search.text:
        return None, "A API da NLM retornou uma resposta vazia. Verifique sua API_KEY."
    
    try:
        data_search = json.loads(limpar_json(res_search.text))
    except json.JSONDecodeError:
        return None, f"Erro de JSON: Conteúdo recebido: {res_search.text[:100]}" # Mostra o início do erro
    
    ids = data_search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None, f"Termo '{termo_en}' não encontrado."

    # ... (resto do fetch igual)

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

