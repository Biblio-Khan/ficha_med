import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import requests

# =========================================================================
# 1. INICIALIZAÇÃO SEGURA E BLINDADA DO FIREBASE
# =========================================================================
def inicializar_firebase():
    # Verifica se o Firebase já foi inicializado para evitar erros no re-run do Streamlit
    if not firebase_admin._apps:
        try:
            # 1. Transforma o bloco [firebase] do secrets num dicionário Python
            firebase_config = dict(st.secrets["firebase"])

            # 2. Corrige e limpa a chave privada contra erros de formatação
            raw_key = firebase_config["private_key"].strip()
            
            # Se a chave foi colada com '\n' em texto corrido, substitui por quebras reais
            if "\\n" in raw_key:
                firebase_config["private_key"] = raw_key.replace("\\n", "\n")
            else:
                firebase_config["private_key"] = raw_key

            # 3. Cria a credencial e inicializa o app
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            
        except Exception as e:
            st.error(f"❌ Erro crítico ao inicializar o Firebase: {e}")
            st.stop() # Para a execução do Streamlit se o Firebase falhar

# Executa a função de inicialização
inicializar_firebase()

# Cria o cliente do Firestore para usares no resto do código
db = firestore.client()

# =========================================================================
# 2. CARREGAMENTO DOS OUTROS SECRETS (Links e Telegram)
# =========================================================================
# O .get() evita que o app quebre caso te tenhas esquecido de alguma chave nos secrets
URL_PLANILHA = st.secrets.get("URL_PLANILHA", "")
URL_SCRIPT_GOOGLE = st.secrets.get("URL_SCRIPT_GOOGLE", "")
TELEGRAM_BOT_TOKEN_MED = st.secrets.get("TELEGRAM_BOT_TOKEN_MED", "")
TELEGRAM_CHAT_ID_MED = st.secrets.get("TELEGRAM_CHAT_ID_MED", "")

# =========================================================================
# 3. FUNÇÃO AUXILIAR: ENVIO DE NOTIFICAÇÕES PARA O TELEGRAM
# =========================================================================
def enviar_mensagem_telegram(texto):
    if not TELEGRAM_BOT_TOKEN_MED or not TELEGRAM_CHAT_ID_MED:
        st.warning("⚠️ Configurações do Telegram ausentes nos Secrets.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_MED}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID_MED,
        "text": texto,
        "parse_mode": "Markdown"
    }
    
    try:
        resposta = requests.post(url, json=payload)
        return resposta.status_code == 200
    except Exception as e:
        st.error(f"Erro ao enviar mensagem para o Telegram: {e}")
        return False

# =========================================================================
# 4. INTERFACE E LÓGICA DO MÓDULO MÉDICO (STREAMLIT)
# =========================================================================
st.set_page_config(page_title="Módulo Médico", page_icon="🏥", layout="centered")

st.title("🏥 Módulo Médico - Sistema de Gestão")
st.write("---")

# Painel Lateral Informativo
st.sidebar.header("⚙️ Status do Sistema")
st.sidebar.success("🔥 Conectado ao Firebase (medicas-ec650)")

if TELEGRAM_BOT_TOKEN_MED:
    st.sidebar.success("🤖 Bot do Telegram Ativo")
else:
    st.sidebar.error("❌ Bot do Telegram Inativo")

# 🖥️ EXEMPLO DE USO DO FIREBASE (Leitura de Dados)
st.subheader("🗂️ Consulta de Registos médicos")

if st.button("🔄 Atualizar e Procurar Dados do Firebase"):
    try:
        # AVISO: Altera 'medicos' ou 'pacientes' para o nome exato da tua coleção no Firestore
        colecao_ref = db.collection("medicos").limit(10).get()
        
        if not colecao_ref:
            st.info("Conexão bem-sucedida! Contudo, a coleção selecionada está vazia.")
        else:
            for doc in colecao_ref:
                dados = doc.to_dict()
                st.write(f"**ID do Documento:** `{doc.id}`")
                st.json(dados) # Mostra os dados do Firebase formatados na tela
                
    except Exception as e:
        st.error(f"Erro ao ler dados do Firestore: {e}")

st.write("---")

# 🖥️ EXEMPLO DE USO DO TELEGRAM (Envio de Alerta)
st.subheader("📢 Disparar Alerta Médico")
mensagem_teste = st.text_input("Mensagem de Alerta:", value="⚠️ Notificação de teste do Módulo Médico.")

if st.button("🚀 Enviar Notificação via Bot"):
    with st.spinner("A enviar..."):
        sucesso = enviar_mensagem_telegram(mensagem_teste)
        if sucesso:
            st.success("Notificação enviada para o grupo/chat do Telegram com sucesso!")
        else:
            st.error("Falha ao enviar mensagem. Verifica o Token e o Chat ID nos teus Secrets.")
