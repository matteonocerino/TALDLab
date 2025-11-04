"""
Mode Selection View - Schermata selezione modalità

Questo modulo implementa l'interfaccia per la selezione della modalità
di esercizio (guidata o esplorativa).

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_1 del RAD e mockup UI_1
"""

import os
import streamlit as st
import base64


def render_mode_selection() -> str | None:
    """
    Renderizza l'interfaccia di selezione modalità.
    
    Implementa RF_1: selezione modalità di esercizio.
    Corrisponde a mockup UI_1 del RAD.
    
    Mostra due opzioni:
    - Modalità guidata: utente seleziona item TALD in anticipo
    - Modalità esplorativa: item assegnato casualmente
    
    Returns:
        str | None: "guided", "exploratory" o None se nessuna selezione
    """
    
    st.markdown("""
    <style>
    /* 1. VARIABILI E STILI DI BASE PER LIGHT/DARK MODE */
    body[theme="light"] {
        --bg-color: #ffffff; --text-color-primary: #2c3e50; --text-color-secondary: #34495e;
        --card-bg: #ffffff; --card-border: #e6e6e6; --info-box-bg: #e7f3ff; --info-box-border: #007bff;
    }
    body[theme="dark"] {
        --bg-color: #0e1117; --text-color-primary: #fafafa; --text-color-secondary: #adb5bd;
        --card-bg: #161b22; --card-border: #303d; --info-box-bg: #1c213c; --info-box-border: #3b82f6;
    }
    .stApp { background: var(--bg-color) !important; }

    /* 2. LAYOUT PRINCIPALE E SPAZIATURE */
    .block-container {
        display: flex;
        flex-direction: column;
        min-height: 90vh;
        padding-top: 2rem !important; 
    }
    .app-footer {
        margin-top: auto;
        padding-top: 2rem;
        padding-bottom: 1rem;
        font-size: 0.9rem;
        color: var(--text-color-secondary);
    }

    /* 3. STILI DEI COMPONENTI UI */
    .brand { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
    .brand img, .brand .emoji-fallback { height: clamp(56px, 6vw, 96px); width: auto; }
    
    .brand-text-container {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }
    .brand .brand-title { 
        font-size: clamp(20px, 2.2vw, 28px); 
        color: var(--text-color-primary) !important; 
        font-weight: 700;
        line-height: 1.2;
    }
    .brand .brand-sub { 
        font-size: clamp(12px, 1.4vw, 14px); 
        color: var(--text-color-secondary) !important;
        line-height: 1.2;
    }
    
    hr {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        margin-top: 1rem !important;
    }
    
    h1, h3, .card-title, .info-box h4 { color: var(--text-color-primary) !important; }
    p, li, .card-sub, .info-box p { color: var(--text-color-secondary) !important; }

    .mode-card {
        background: var(--card-bg) !important; border: 1px solid var(--card-border) !important;
        border-radius: 10px; padding: 1.2rem; margin-bottom: 1rem; min-height: 260px;
    }
    .mode-card.guided { border-left: 6px solid #27ae60 !important; }
    .mode-card.exploratory { border-left: 6px solid #e67e22 !important; }

    .info-box {
        background-color: var(--info-box-bg) !important; border-left: 4px solid var(--info-box-border) !important;
        padding: 1rem; border-radius: 4px; margin-top: 1rem;
    }
    
    /* Stile per i bottoni colorati in base alla colonna */
    div[data-testid="stButton"] > button {
        border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; padding: 0.5rem 1rem !important;
        color: white !important;
    }
    div[data-testid="stButton"] > button:hover {
        filter: brightness(1.1); color: white !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="stButton"] > button {
        background-color: #27ae60 !important; /* Verde */
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stButton"] > button {
        background-color: #e67e22 !important; /* Arancione */
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Prepara e renderizza l'header del brand con logo o emoji
    logo_path = os.path.join("assets", "taldlab_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_element_html = f'<img src="data:image/png;base64,{b64_logo}" alt="TALDLab logo" />'
    else:
        logo_element_html = '<div class="emoji-fallback">🧠</div>'

    st.markdown(f"""
    <div class="brand">
        {logo_element_html}
        <div class="brand-text-container">
            <div class="brand-title">TALDLab</div>
            <div class="brand-sub">Simulatore di Pazienti Virtuali - Thought and Language Dysfunction Scale</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    st.markdown("## Seleziona la Modalità di Esercitazione")
    st.markdown("Scegli come desideri esercitarti nella rilevazione dei disturbi del pensiero e del linguaggio.")
    
    col1, col2 = st.columns(2, gap="large")
    
    # Colonna Modalità Guidata
    with col1:
        st.markdown("""
        <div class="mode-card guided">
            <h3 class="card-title">📚 Modalità Guidata</h3>
            <p class="card-sub">Training mirato su item specifico</p>
            <p>Seleziona in anticipo quale disturbo TALD vuoi studiare. Ideale per l'apprendimento iniziale e la preparazione a esami.</p>
            <ul>
                <li>Scegli l'item TALD dall'elenco completo</li>
                <li>Sai quale disturbo stai osservando</li>
                <li>Obiettivo: attribuire il grado corretto (0-4)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Avvia Modalità Guidata →", use_container_width=True, key="btn_guided"):
            return "guided"
    
    # Colonna Modalità Esplorativa
    with col2:
        st.markdown("""
        <div class="mode-card exploratory">
            <h3 class="card-title">🔍 Modalità Esplorativa</h3>
            <p class="card-sub">Assessment diagnostico realistico</p>
            <p>Il sistema assegna casualmente un item TALD senza comunicartelo. Simula una vera valutazione clinica.</p>
            <ul>
                <li>Item assegnato casualmente (non visibile)</li>
                <li>Devi identificare quale disturbo osservi</li>
                <li>Obiettivo: identificare l'item e il grado (0-4)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Avvia Modalità Esplorativa →", use_container_width=True, key="btn_exploratory"):
            return "exploratory"
    
    # Box informativo e footer
    st.markdown("""
    <div class="info-box">
        <h4>ℹ️ Come funziona il sistema</h4>
        <p>Dopo aver selezionato la modalità, condurrai un'intervista testuale con un "paziente virtuale" 
        generato tramite LLM. Al termine, valuterai le manifestazioni osservate e riceverai un report 
        dettagliato con feedback formativo.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="app-footer">
        📌 <strong>Progetto di tesi</strong> - Studente: M. Nocerino | Relatore: Prof.ssa R. Francese
    </div>
    """, unsafe_allow_html=True)
    
    return None


def render_mode_info_sidebar():
    """Renderizza informazioni aggiuntive nella sidebar."""
    with st.sidebar:
        st.markdown("## 📖 Guida Rapida")
        st.markdown("""
        **Modalità Guidata**
        1. Seleziona un item TALD
        2. Conduci l'intervista
        3. Valuta il grado osservato
        
        **Modalità Esplorativa**
        1. Avvia simulazione (item casuale)
        2. Conduci l'intervista
        3. Identifica item + valuta grado
        """)
        st.markdown("---")
        st.info("**Item TALD:** 30 totali\n\n**Scala graduazione:** 0-4")
        st.warning("Strumento **formativo**, NON per uso clinico-diagnostico.")


def reset_to_mode_selection():
    """Reset completo dell'applicazione alla schermata di selezione modalità."""
    keys_to_keep = ['initialized', 'tald_items', 'services']
    keys_to_remove = [key for key in st.session_state.keys() if key not in keys_to_keep]
    for key in keys_to_remove:
        del st.session_state[key]
    st.rerun()