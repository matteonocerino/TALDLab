"""
TALDLab - Applicazione principale

Simulatore di Pazienti Virtuali per la Thought and Language Dysfunction Scale (TALD).
Orchestratore principale che coordina tutte le fasi dell'applicazione.

Autore: Matteo Nocerino
Matricola: 0512117269
Relatore: Prof.ssa Rita Francese
Anno Accademico: 2025/2026
"""

import streamlit as st
import random
from pathlib import Path

# Import Models
from src.models.session_state import SessionState, SessionPhase
from src.models.tald_item import TALDItem
from src.models.conversation import ConversationHistory
from src.models.evaluation import GroundTruth

# Import Services
from src.services.configuration_service import ConfigurationService, ConfigurationError
from src.services.llm_service import LLMService
from src.services.conversation_manager import ConversationManager
from src.services.evaluation_service import EvaluationService
from src.services.comparison_engine import ComparisonEngine
from src.services.report_generator import ReportGenerator
from src.services.feedback_service import FeedbackService

# Import Views
from src.views.mode_selection import render_mode_selection
from src.views.item_selection import render_item_selection
from src.views.chat_interface import render_chat_interface
from src.views.evaluation_form import render_evaluation_form
from src.views.report_view import render_report_view, handle_pdf_download
from src.views.feedback_form import render_feedback_form


# ============================================================================
# UTILITY PER CARICAMENTO STILE GLOBALE
# ============================================================================

def load_css(file_path: str):
    """Carica e inietta un file CSS esterno nell'app Streamlit."""
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ============================================================================
# CONFIGURAZIONE STREAMLIT
# ============================================================================

def configure_streamlit():
    """
    Configura le impostazioni globali di Streamlit.
    
    Implementa la configurazione della pagina con titolo, icona e layout.
    """
    st.set_page_config(
        page_title="TALDLab - TALD Simulator",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': """
            # TALDLab
            **Simulatore di Pazienti Virtuali per scala TALD**
            
            Progetto di tesi triennale
            - Studente: Matteo Nocerino
            - Matricola: 0512117269
            - Relatore: Prof.ssa Rita Francese
            - A.A. 2025/2026
            """
        }
    )


# ============================================================================
# INIZIALIZZAZIONE APPLICAZIONE
# ============================================================================

def initialize_application():
    """
    Inizializza l'applicazione caricando configurazioni e services.
    
    Questa funzione viene eseguita UNA SOLA VOLTA all'avvio dell'app.
    Carica:
    - Configurazione da .env
    - 30 item TALD da JSON
    - Services (LLM, ConversationManager, etc.)
    
    Gestisce errori critici di configurazione.
    """
    if 'initialized' not in st.session_state:
        try:
            # Carica configurazione
            with st.spinner("🔧 Caricamento configurazione..."):
                config = ConfigurationService.load_env_config()
                tald_items = ConfigurationService.load_tald_items()
                
                # Valida configurazione
                ConfigurationService.validate_configuration(config)
            
            # Inizializza services
            with st.spinner("⚙️ Inizializzazione services..."):
                llm_service = LLMService(config)
                conversation_manager = ConversationManager(llm_service)
                report_generator = ReportGenerator(llm_service)
            
            # Salva in session_state
            st.session_state.config = config
            st.session_state.tald_items = tald_items
            st.session_state.llm_service = llm_service
            st.session_state.conversation_manager = conversation_manager
            st.session_state.report_generator = report_generator
            
            # Inizializza session state
            st.session_state.session = SessionState()
            st.session_state.conversation = ConversationHistory()
            
            # Flag inizializzazione completata
            st.session_state.initialized = True
            
        except ConfigurationError as e:
            st.error(f"""
            ❌ **Errore di configurazione**
            
            {str(e)}
            
            Verifica che:
            1. Il file `.env` esista con `GEMINI_API_KEY`
            2. Il file `tald_items.json` contenga 30 item validi
            3. Tutte le dipendenze siano installate
            """)
            st.stop()
        
        except Exception as e:
            st.error(f"""
            ❌ **Errore imprevisto durante l'inizializzazione**
            
            {str(e)}
            
            Contatta il supporto tecnico.
            """)
            st.stop()


# ============================================================================
# GESTIONE FASI (WORKFLOW)
# ============================================================================

def handle_mode_selection():
    """
    Gestisce la fase di selezione modalità.
    
    Implementa RF_1: selezione modalità di esercizio.
    """
    selected_mode = render_mode_selection()
    
    if selected_mode == "guided":
        st.session_state.session.start_guided_mode()
        st.rerun()
    
    elif selected_mode == "exploratory":
        random_item = random.choice(st.session_state.tald_items)
        
        st.session_state.session.start_exploratory_mode(
            item_id=random_item.id,
            item_title=random_item.title,
            grade=random_item.default_grade
        )
        
        st.session_state.current_item = random_item
        
        st.rerun()


def handle_item_selection():
    """
    Gestisce la fase di selezione item (solo modalità guidata).
    
    Implementa RF_2: gestione item TALD.
    """
    selected_item = render_item_selection(st.session_state.tald_items)
    
    if selected_item:
        st.session_state.session.set_selected_item(
            item_id=selected_item.id,
            item_title=selected_item.title,
            grade=selected_item.default_grade
        )
        
        st.session_state.current_item = selected_item
        
        st.rerun()


def handle_interview():
    """
    Gestisce la fase di intervista con paziente virtuale.
    
    Implementa RF_4, RF_5, RF_11, RF_13.
    """
    current_item = st.session_state.current_item
    ground_truth = st.session_state.session.ground_truth
    
    terminated = render_chat_interface(
        conversation=st.session_state.conversation,
        conversation_manager=st.session_state.conversation_manager,
        tald_item=current_item,
        grade=ground_truth.grade,
        mode=ground_truth.mode
    )
    
    if terminated:
        st.session_state.session.terminate_interview()
        st.rerun()


def handle_evaluation():
    """
    Gestisce la fase di valutazione finale.
    
    Implementa RF_6, RF_7.
    """
    current_item = st.session_state.current_item
    ground_truth = st.session_state.session.ground_truth
    
    user_evaluation = render_evaluation_form(
        tald_items=st.session_state.tald_items,
        current_item=current_item,
        conversation=st.session_state.conversation,
        mode=ground_truth.mode
    )
    
    if user_evaluation == "BACK":
        st.session_state.session.phase = SessionPhase.INTERVIEW
        st.rerun()
    
    elif user_evaluation:
        try:
            comparison_result = ComparisonEngine.compare(
                user_evaluation=user_evaluation,
                ground_truth=ground_truth
            )
            
            report = st.session_state.report_generator.generate_report(
                ground_truth=ground_truth,
                user_evaluation=user_evaluation,
                result=comparison_result,
                conversation=st.session_state.conversation,
                tald_item=current_item
            )
            
            st.session_state.session.submit_evaluation(user_evaluation, comparison_result)
            st.session_state.report = report
            
            st.rerun()
        
        except Exception as e:
            st.error(f"""
            ❌ **Errore durante la generazione del report**
            
            {str(e)}
            """)


def handle_report():
    """
    Gestisce la fase di visualizzazione report.
    
    Implementa RF_8, RF_9.
    """
    report = st.session_state.report
    
    action = render_report_view(report)
    
    if action == "download_pdf":
        handle_pdf_download(report)
    
    elif action == "new_simulation":
        reset_application()
        st.rerun()
    
    elif action == "feedback":
        st.session_state.show_feedback = True
        st.rerun()


def handle_feedback():
    """
    Gestisce la fase di feedback opzionale.
    
    Implementa RF_10.
    """
    report = st.session_state.report
    
    completed = render_feedback_form(
        item_id=report.tald_item.id,
        item_title=report.tald_item.title,
        mode=report.ground_truth.mode,
        score=report.result.score
    )
    
    if completed:
        st.balloons()
        st.success("🎉 Grazie per aver usato TALDLab!")
        
        if st.button("🔄 Avvia Nuova Simulazione", use_container_width=True, type="primary"):
            reset_application()
            st.rerun()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def reset_application():
    """
    Reset dell'applicazione per nuova simulazione.
    
    Implementa RF_14: reset sessione.
    
    Pulisce session_state mantenendo solo configurazioni caricate.
    """
    keys_to_keep = [
        'initialized',
        'config',
        'tald_items',
        'llm_service',
        'conversation_manager',
        'report_generator'
    ]
    
    keys_to_remove = [key for key in st.session_state.keys() 
                      if key not in keys_to_keep]
    
    for key in keys_to_remove:
        del st.session_state[key]
    
    st.session_state.session = SessionState()
    st.session_state.conversation = ConversationHistory()


def render_error_page(error_message: str):
    """
    Renderizza pagina di errore generico.
    
    Args:
        error_message (str): Messaggio di errore da mostrare
    """
    st.error(f"""
    ❌ **Si è verificato un errore**
    
    {error_message}
    """)
    
    if st.button("🔄 Riavvia Applicazione"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """
    Funzione principale dell'applicazione.
    
    Coordina il flusso tra tutte le fasi del workflow.
    Implementa il pattern architetturale Entity-Control-Boundary.
    """
    # Configura Streamlit
    configure_streamlit()
    
    # Carica il foglio di stile globale dell'applicazione
    load_css("src/views/style.css")
    
    # Inizializza applicazione (solo prima volta)
    initialize_application()
    
    # Routing basato sulla fase corrente
    try:
        session = st.session_state.session
        
        if session.is_in_selection():
            handle_mode_selection()
        
        elif session.is_in_item_selection():
            handle_item_selection()
        
        elif session.is_in_interview():
            handle_interview()
        
        elif session.is_in_evaluation():
            handle_evaluation()
        
        elif session.is_in_report():
            if st.session_state.get('show_feedback', False):
                handle_feedback()
            else:
                handle_report()
        
        else:
            render_error_page(f"Fase non valida: {session.phase}")
    
    except Exception as e:
        render_error_page(f"Errore imprevisto: {str(e)}")
        
        with st.expander("🔧 Debug Info"):
            st.write("Session State:", st.session_state.session.to_dict())
            st.exception(e)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()