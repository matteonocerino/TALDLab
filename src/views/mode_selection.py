"""
Mode Selection View - Schermata selezione modalità

Questo modulo implementa l'interfaccia per la selezione della modalità
di esercizio (guidata o esplorativa).

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_1 del RAD e mockup UI_1
"""

import streamlit as st


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
    
    # CSS personalizzato per card style come mockup
    st.markdown("""
    <style>
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        color: white;
        padding: 2rem 2rem 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        color: #bdc3c7;
        margin: 0;
    }
    
    /* Card styling */
    .mode-card {
        background: #fafafa;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .mode-card:hover {
        border-color: #3498db;
        box-shadow: 0 8px 20px rgba(52, 152, 219, 0.15);
        transform: translateY(-2px);
    }
    
    .mode-card.guided {
        border-left: 5px solid #27ae60;
    }
    
    .mode-card.exploratory {
        border-left: 5px solid #e67e22;
    }
    
    /* Features list */
    .feature-list {
        list-style: none;
        padding-left: 0;
    }
    
    .feature-list li {
        padding: 0.5rem 0;
        color: #34495e;
    }
    
    .feature-list.guided li:before {
        content: "✓ ";
        color: #27ae60;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    
    .feature-list.exploratory li:before {
        content: "✓ ";
        color: #e67e22;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    
    /* Info box */
    .info-box {
        background: #e8f4f8;
        border-left: 4px solid #3498db;
        padding: 1.5rem;
        border-radius: 4px;
        margin-top: 2rem;
    }
    
    .info-box h4 {
        color: #2980b9;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header principale con logo custom
    header_col1, header_col2 = st.columns([1, 11])
    
    with header_col1:
        # Logo custom (se esiste, altrimenti fallback emoji)
        try:
            st.image("assets/taldlab_logo.png", width=70)
        except:
            st.markdown("<div style='font-size: 3.5rem; margin-top: -10px;'>🧠</div>", unsafe_allow_html=True)
    
    with header_col2:
        st.markdown("""
        <div style="margin-top: 10px;">
            <h1 style="margin: 0; color: #2c3e50;">TALDLab</h1>
            <p style="color: #7f8c8d; margin: 0;">Simulatore di Pazienti Virtuali - Thought and Language Dysfunction Scale</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Intro section
    st.markdown("## Seleziona la Modalità di Esercitazione")
    st.markdown("""
    Scegli come desideri esercitarti nella rilevazione dei disturbi del pensiero e del linguaggio. 
    Ogni modalità offre un percorso formativo diverso.
    """)
    
    st.markdown("")  # Spacing
    
    # Due colonne per le card
    col1, col2 = st.columns(2, gap="large")
    
    # Modalità Guidata
    with col1:
        st.markdown("""
        <div class="mode-card guided">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📚 Modalità Guidata")
        st.markdown("**Training mirato su item specifico**")
        
        st.markdown("""
        Seleziona in anticipo quale disturbo TALD vuoi studiare. 
        Ideale per l'apprendimento iniziale e la preparazione a esami.
        """)
        
        st.markdown("""
        <ul class="feature-list guided">
            <li>Scegli l'item TALD dall'elenco completo (30 disponibili)</li>
            <li>Sai quale disturbo stai osservando</li>
            <li>Obiettivo: attribuire il grado corretto (0-4)</li>
            <li>Perfetto per studiare un fenomeno specifico</li>
        </ul>
        """, unsafe_allow_html=True)
        
        if st.button(
            "Avvia Modalità Guidata →",
            use_container_width=True,
            type="primary",
            key="btn_guided"
        ):
            return "guided"
    
    # Modalità Esplorativa
    with col2:
        st.markdown("""
        <div class="mode-card exploratory">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔍 Modalità Esplorativa")
        st.markdown("**Assessment diagnostico realistico**")
        
        st.markdown("""
        Il sistema assegna casualmente un item TALD senza comunicartelo. 
        Simula una vera valutazione clinica.
        """)
        
        st.markdown("""
        <ul class="feature-list exploratory">
            <li>Item assegnato casualmente (non visibile)</li>
            <li>Devi identificare quale disturbo osservi</li>
            <li>Obiettivo: identificare l'item E il grado (0-4)</li>
            <li>Verifica le competenze diagnostiche acquisite</li>
        </ul>
        """, unsafe_allow_html=True)
        
        if st.button(
            "Avvia Modalità Esplorativa →",
            use_container_width=True,
            type="primary",
            key="btn_exploratory"
        ):
            return "exploratory"
    
    # Info box finale
    st.markdown("""
    <div class="info-box">
        <h4>ℹ️ Come funziona il sistema</h4>
        <p>Dopo aver selezionato la modalità, condurrai un'intervista testuale con un "paziente virtuale" 
        generato tramite LLM. Al termine, valuterai le manifestazioni osservate e riceverai un report 
        dettagliato con feedback formativo.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("")
    st.caption("""
    📌 **Progetto di tesi** - Studente: Matteo Nocerino | 
    Relatore: Prof.ssa Rita Francese | A.A. 2024/2025
    """)
    
    return None


def render_mode_info_sidebar():
    """
    Renderizza informazioni aggiuntive nella sidebar.
    
    Mostra guida rapida e risorse.
    """
    with st.sidebar:
        st.markdown("## 📖 Guida Rapida")
        
        st.markdown("""
        ### Modalità Guidata
        1. Seleziona un item TALD
        2. Conduci l'intervista
        3. Valuta il grado osservato
        4. Ricevi feedback
        
        ### Modalità Esplorativa
        1. Avvia simulazione (item casuale)
        2. Conduci l'intervista
        3. Identifica item + valuta grado
        4. Ricevi feedback
        """)
        
        st.markdown("---")
        
        st.markdown("### ℹ️ Info Sistema")
        st.info("""
        **Item TALD:** 30 totali
        - Oggettivi: 21
        - Soggettivi: 9
        
        **Scala graduazione:** 0-4
        """)
        
        st.markdown("---")
        
        st.markdown("### ⚠️ Disclaimer")
        st.warning("""
        Strumento **formativo**, 
        NON per uso clinico-diagnostico.
        """)


def reset_to_mode_selection():
    """
    Reset completo dell'applicazione alla schermata di selezione modalità.
    
    Utilizzato dal pulsante "Nuova simulazione" nelle altre view.
    Pulisce session_state e ritorna alla fase iniziale.
    """
    # Mantiene solo le configurazioni persistenti
    keys_to_keep = ['initialized', 'tald_items', 'services']
    
    # Rimuove tutto tranne le chiavi da mantenere
    keys_to_remove = [key for key in st.session_state.keys() 
                      if key not in keys_to_keep]
    
    for key in keys_to_remove:
        del st.session_state[key]
    
    # Forza rerun per tornare a selection
    st.rerun()