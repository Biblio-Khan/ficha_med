import requests
from googletrans import Translator

# Configurações
API_KEY = "a057b5a9af48c7802e2d144f8fe4583d2508"
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
translator = Translator()

def buscar_descritor_mesh(termo_pt):
    # 1. Tradução
    termo_en = translator.translate(termo_pt, src='pt', dest='en').text
    
    # 2. Busca na API E-utilities
    params_search = {
        "db": "mesh",
        "term": termo_en,
        "retmode": "json",
        "api_key": API_KEY
    }
    
    response = requests.get(f"{BASE_URL}esearch.fcgi", params=params_search).json()
    
    # Pegamos o primeiro ID retornado como o mais provável
    ids = response.get("esearchresult", {}).get("idlist", [])
    
    if not ids:
        return None
    
    # 3. Fetch dos detalhes do descritor
    params_fetch = {
        "db": "mesh",
        "id": ids[0],
        "retmode": "json",
        "api_key": API_KEY
    }
    
    data = requests.get(f"{BASE_URL}efetch.fcgi", params=params_fetch).json()
    
    # Retornar o nome do descritor principal
    return data # Aqui você fará o parser específico para o seu formato AACR2

# Exemplo de uso
termo = "Diabetes Mellitus"
resultado = buscar_descritor_mesh(termo)
print(resultado)
