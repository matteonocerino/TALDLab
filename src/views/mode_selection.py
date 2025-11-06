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
    
    # NOTA: Il blocco CSS è stato rimosso e spostato in 'src/views/style.css',
    # che viene caricato globalmente da 'app.py'.
    
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