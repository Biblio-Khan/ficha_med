import streamlit as st
import pandas as pd
import io
from docx import Document

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="BiblioKhan Médicas", page_icon="🩺", layout="centered")

# Inicialização de Estados
if 'lista_assuntos' not in st.session_state: st.session_state.lista_assuntos = []
if 'autores' not in st.session_state: st.session_state.autores = [""]
if 'colaboradores' not in st.session_state: st.session_state.colaboradores = []

# --- FUNÇÕES ---
def formatar_entrada_autor(nome):
    partes = nome.strip().split()
    return f"{partes[-1].upper()}, {' '.join(partes[:-1])}" if len(partes) > 1 else nome.upper()

def calcular_cutter(nome_autor):
    try:
        df = pd.read_csv("cutter.csv")
        # Pega o sobrenome completo (ex: SILVA-SANTOS)
        sobrenome_completo = nome_autor.strip().split()[-1].upper()
        
        # Lógica de fatiamento: tenta o nome todo, depois vai reduzindo (ex: SILVA, SILV, SIL)
        for i in range(len(sobrenome_completo), 2, -1):
            tentativa = sobrenome_completo[:i]
            res = df[df["Name"].str.upper() == tentativa]
            if not res.empty:
                return str(res.iloc[0]["ID"])
        return "????"
    except Exception as e:
        return "Erro"

# --- INTERFACE ---
st.title("🩺 BiblioKhan Médicas")

titulo = st.text_input("Título da obra:")
classe_principal = st.text_input("Classe principal (Ex: 610):")
volumes = st.text_input("Volume ou Edição:")
isbn = st.text_input("ISBN:")
paginas = st.text_input("Páginas:")
cidade = st.text_input("Cidade:")
editora = st.text_input("Editora:")
ano = st.text_input("Ano:")

# [Aqui você mantém os campos dinâmicos de autores/colaboradores/assuntos]

# --- GERAÇÃO AACR2 ---
if st.button("🚀 Gerar Ficha CIP (AACR2)"):
    aut_principal = st.session_state.autores[0]
    # Pega a primeira letra para a classe (ex: S para SILVA)
    sobrenome_letra = aut_principal.strip().split()[-1][0].upper()
    cutter_id = calcular_cutter(aut_principal)
    classificacao = f"{classe_principal} {sobrenome_letra}{cutter_id} {ano}"

    # Lógica de Assuntos e Entradas Secundárias
    lista_final = [f"{i+1}. {a.strip().capitalize()}." for i, a in enumerate(st.session_state.lista_assuntos)]
    lista_final.append("I. Título.") # Título sempre I.
    
    romanos_colab = ["II.", "III.", "IV.", "V."]
    for i, colab in enumerate(st.session_state.colaboradores):
        if colab["nome"]:
            idx = min(i, len(romanos_colab)-1)
            lista_final.append(f"{romanos_colab[idx]} {formatar_entrada_autor(colab['nome'])} ({colab['tipo']}).")

    # --- HTML ---
    html_ficha = f"""
    <div style="border: 1px solid #000; padding: 20px; font-family: monospace;">
        <p><b>{formatar_entrada_autor(aut_principal)}.</b></p>
        <p style="text-indent: 30px;">{titulo}. – {volumes + ' ; ' if volumes else ''}{paginas}.</p>
        <p style="text-indent: 30px;">ISBN {isbn if isbn else "..."}</p>
        <p style="text-indent: 30px;">{' '.join(lista_final)}</p>
        <div style="text-align: right;">{classificacao}</div>
    </div>
    """
    st.markdown(html_ficha, unsafe_allow_html=True)
