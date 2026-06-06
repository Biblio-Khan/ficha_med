import streamlit as st
import requests
from deep_translator import GoogleTranslator

# --- Configurações ---
# Substitua pela sua chave obtida no NCBI
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" 
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

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
        response_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search).json()
        ids = response_search.get("esearchresult", {}).get("idlist", [])
        
        if not ids:
            return None, "Termo não encontrado na base MeSH."
            
        # 3. Detalhamento do Descritor
        params_fetch = {
            "db": "mesh",
            "id": ids[0],
            "retmode": "json",
            "api_key": API_KEY
        }
        response_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch).json()
        
        # Extração do nome do descritor
        descritor = response_fetch.get("result", {}).get(ids[0], {}).get("terms", [{}])[0].get("name")
        return descritor, None
        
    except Exception as e:
        return None, f"Erro na comunicação com a API: {e}"

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Ficha - Medicina")
st.title("Gerador de Ficha Catalográfica (Área Médica)")

termo_input = st.text_input("Insira o assunto principal para a ficha:")

if st.button("Gerar Assuntos da Ficha"):
    if termo_input:
        with st.spinner('Consultando base MeSH e formatando...'):
            descritor, erro = buscar_mesh(termo_input)
            
            if descritor:
                st.success("Assunto validado com sucesso!")
                
                # --- Formatação AACR2 ---
                # A lógica de pontuação segue: 1. [Assunto]. 2. [Subdivisão].
                ficha_formatada = f"1. {descritor}."
                
                st.subheader("Bloco de Assuntos na Ficha:")
                st.text_area("Copie o texto abaixo para sua ficha:", value=ficha_formatada, height=100)
            else:
                st.error(f"Erro: {erro}")
    else:
        st.warning("Por favor, preencha o campo de assunto.")

st.markdown("---")
st.caption("Sistema integrado à API NLM/PubMed para validação de descritores MeSH.")
