import streamlit as st
import requests
from googletrans import Translator

# Configuração da API
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508" # Substitua pela sua chave
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
translator = Translator()

def buscar_mesh(termo_pt):
    # 1. Traduzir para o inglês
    try:
        termo_en = translator.translate(termo_pt, src='pt', dest='en').text
    except Exception as e:
        return None, f"Erro na tradução: {e}"

    # 2. Pesquisar ID no MeSH
    params_search = {"db": "mesh", "term": termo_en, "retmode": "json", "api_key": API_KEY}
    response_search = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search).json()
    
    ids = response_search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None, "Termo não encontrado no MeSH."

    # 3. Buscar detalhes do descritor
    params_fetch = {"db": "mesh", "id": ids[0], "retmode": "json", "api_key": API_KEY}
    response_fetch = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch).json()
    
    # Extrair nome do descritor (retorno da API do MeSH é uma estrutura complexa)
    # Ajuste conforme a chave específica da estrutura do JSON da NLM
    descritor = response_fetch.get("result", {}).get(ids[0], {}).get("terms", [{}])[0].get("name")
    
    return descritor, None

# Interface Streamlit
st.title("Gerador de Ficha Catalográfica - Área Médica")
termo_input = st.text_input("Digite o assunto (Descritor):")

if st.button("Buscar Descritor"):
    if termo_input:
        with st.spinner('Consultando PubMed/MeSH...'):
            resultado, erro = buscar_mesh(termo_input)
            
            if resultado:
                st.success(f"Descritor validado: {resultado}")
                # Aqui entra a lógica de montagem da ficha que você já possui
                st.write("---")
                st.subheader("Sugestão de Assunto para Ficha:")
                st.code(f"1. {resultado}.")
            else:
                st.error(erro)
    else:
        st.warning("Por favor, digite um assunto.")
