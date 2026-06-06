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

def extrair_json_seguro(texto):
    """Captura apenas o primeiro objeto JSON encontrado entre chaves."""
    match = re.search(r'\{.*\}', texto, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Nenhum objeto JSON válido encontrado na resposta da API.")

def buscar_mesh(termo_pt):
    # Tradução
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
    
    # 1. Fazemos a requisição e salvamos o objeto completo
    res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
    
    # 2. DEBUG: Isso vai mostrar o que está acontecendo na tela do Streamlit
    st.write(f"Status Code: {res_search.status_code}")
    st.write(f"Resposta bruta: {res_search.text}") # Isso nos dará a resposta real
    
    # ... resto do código ...
# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina", layout="centered")
st.title("Gerador de Ficha Catalográfica")

termo_input = st.text_input("Insira o assunto principal (Descritor):")

if st.button("Buscar Descritor"):
    if termo_input:
        with st.spinner('Validando na base MeSH...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success("Descritor oficial MeSH encontrado:")
                ficha_formatada = f"1. {descritor}."
                st.code(ficha_formatada)
            else:
                st.error(erro)
    else:
        st.warning("Por favor, preencha o campo de assunto.")
