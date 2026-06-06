import streamlit as st
import requests
import json
import re
from deep_translator import GoogleTranslator

# --- Configurações ---
# Se rodar no Streamlit Cloud, substitua por: API_KEY = st.secrets["API_KEY"]
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (BibliotecarioBot/1.0)'}

def validar_e_extrair_json(texto):
    """Extrai o primeiro objeto JSON, corrige aspas duplicadas e valida o conteúdo."""
    # 1. Corrige problemas comuns de aspas da API NLM
    texto_limpo = texto.replace('""', '"')
    
    # 2. Localiza o primeiro bloco JSON
    match = re.search(r'\{.*\}', texto_limpo, re.DOTALL)
    if not match:
        if texto.strip().startswith('<'):
            raise ValueError("A API retornou XML. Verifique sua permissão de API.")
        raise ValueError("Resposta não contém um objeto JSON válido.")
    
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        raise ValueError("Erro ao decodificar o JSON recebido.")

def buscar_mesh(termo_pt):
    # Tradução do termo
    try:
        termo_en = GoogleTranslator(source='pt', target='en').translate(termo_pt)
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 1. Busca Permissiva (Sem [MeSH Terms] para evitar bloqueios de escopo)
    params_search = {
        "db": "mesh",
        "term": termo_en,
        "retmode": "json",
        "api_key": API_KEY,
        "retmax": 5
    }
    
    try:
        res_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search, headers=HEADERS, timeout=15)
        data_search = validar_e_extrair_json(res_search.text)
        ids = data_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, f"Termo '{termo_en}' não localizado."
            
        # 2. Detalhamento (Fetch)
        mesh_id = ids[0]
        params_fetch = {"db": "mesh", "id": mesh_id, "retmode": "json", "api_key": API_KEY}
        res_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch, headers=HEADERS, timeout=15)
        
        data_fetch = validar_e_extrair_json(res_fetch.text)
        
        # 3. Extração do nome oficial
        results = data_fetch.get("result", {})
        descritor = results.get(mesh_id, {}).get("terms", [{}])[0].get("name")
        
        return descritor, None
        
    except Exception as e:
        return None, str(e)

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina", layout="centered")
st.title("Gerador de Ficha Catalográfica")

termo_input = st.text_input("Insira o assunto principal (ex: Câncer, Coração, Diabetes):")

if st.button("Buscar Descritor"):
    if termo_input:
        with st.spinner('Validando na base MeSH...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success(f"Descritor oficial MeSH encontrado:")
                ficha_formatada = f"1. {descritor}."
                st.code(ficha_formatada)
            else:
                st.error(f"Erro: {erro}")
    else:
        st.warning("Por favor, preencha o campo de assunto.")
