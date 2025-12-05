"""
TALDLab - Applicazione principale

Simulatore di Pazienti Virtuali per la Thought and Language Dysfunction Scale (TALD).
Orchestratore principale che coordina tutte le fasi dell'applicazione.

Autore: Matteo Nocerino
Matricola: 0512117269
Relatore: Prof.ssa Rita Francese
Anno Accademico: 2024/2025
"""

import streamlit as st
import random
import time

# Import Models
from src.models.session_state import SessionState, SessionPhase

# Import Services
from src.services.configuration_service import ConfigurationService, ConfigurationError
from src.services.llm_service import LLMService, LLMTimeoutError, LLMConnectionError
from src.services.conversation_manager import ConversationManager
from src.services.comparison_engine import ComparisonEngine
from src.services.report_generator import ReportGenerator

# Import Views
from src.views.mode_selection import render_mode_selection, render_mode_info_sidebar
from src.views.item_selection import render_item_selection
from src.views.chat_interface import render_chat_interface
from src.views.evaluation_form import render_evaluation_form
from src.views.report_view import render_report_view
from src.views.feedback_form import render_feedback_form


# ============================================================================
# UTILITY PER CARICAMENTO STILE GLOBALE
# ============================================================================

def load_css(file_path: str):
    """Carica e inietta un file CSS esterno nell'app Streamlit."""
    with open(file_path, encoding="utf-8") as f:
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
            - A.A. 2024/2025
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

    # Inizializza session state
    if 'session' not in st.session_state:
        st.session_state.session = SessionState()        


# ============================================================================
# GESTIONE FASI (WORKFLOW)
# ============================================================================

def handle_mode_selection():
    """
    Fase 1: Selezione Modalità.
    Gestisce l'avvio della modalità Guidata o la generazione randomica della Esplorativa.

    Implementa RF_1 e logica di generazione comorbilità (RF_3).
    """
    selected_mode = render_mode_selection()
    render_mode_info_sidebar()

    # Recuperiamo la sessione usando la chiave semplice 'session'
    session = st.session_state.session
    all_items = st.session_state.tald_items
    
    if selected_mode == "guided":
        # Passa alla selezione item
        session.start_guided_mode()
        st.rerun()
    
    elif selected_mode == "exploratory":
        # === LOGICA GENERAZIONE MULTI-DISTURBO (RF_3) ===
        # Genera un profilo clinico complesso:
        # - Da 0 a 25 disturbi attivi (casuali).
        # - Gradi casuali da 1 a 4 per quelli attivi.
        
        num_disturbi = random.randint(0, 25)  # Limite massimo richiesto: 25
        
        active_items = {}
        if num_disturbi > 0:
            # Campionamento casuale degli item (senza ripetizioni)
            chosen_items = random.sample(all_items, num_disturbi)
            
            # Assegnazione gradi di severità
            for item in chosen_items:
                active_items[item.id] = random.randint(1, 4)
        
        # Avvia sessione esplorativa passando il dizionario completo
        session.start_exploratory_mode(active_items=active_items)
        
        # Imposta un current_item placeholder per non rompere la UI header
        # (in esplorativa l'utente non deve sapere quale item è attivo)
        if all_items:
            st.session_state.current_item = all_items[0] 
            
        st.rerun()


def handle_item_selection():
    """
    Fase 2: Selezione Item (Solo Modalità Guidata).

    Implementa RF_2: gestione item TALD e setup singola simulazione.
    """
    selection = render_item_selection(st.session_state.tald_items)
    session = st.session_state.session
    
    # Navigazione: Reset
    if selection == "reset":
        reset_application()
        st.rerun()

    # Conferma Selezione
    elif selection:
        # === LOGICA GENERAZIONE GUIDATA ===
        # Il grado viene generato casualmente, incluso lo 0 (Paziente Asintomatico)
        random_grade = random.randint(0, 4)

        session.set_selected_item(
            item_id=selection.id,
            grade=random_grade
        )
        
        # Salviamo l'item corrente per visualizzarlo nell'header della chat
        st.session_state.current_item = selection
        st.rerun()


def handle_interview():
    """
    Fase 3: Intervista con Paziente Virtuale.
    Implementa RF_4, RF_5, RF_11, RF_13.
    """
    session = st.session_state.session
    current_item = st.session_state.current_item
    llm_service = st.session_state.llm_service
    
    # --- SETUP SESSIONE CHAT ---
    # inizializziamo la sessione LLM qui nel controller se non esiste.
    
    if "chat_session" not in st.session_state:
        try:
            # Recupera la configurazione complessa (dizionario {id: grado}) dal Ground Truth
            active_items_config = session.ground_truth.active_items
            all_tald_items = st.session_state.tald_items
            
            # Inizializza il modello con il System Prompt combinato
            st.session_state.chat_session = llm_service.start_chat_session(
                active_items=active_items_config,
                all_tald_items=all_tald_items
            )
        except Exception as e:
            st.error(f"Errore inizializzazione chat: {e}")
            return

    # Recuperiamo parametri per la UI (titoli, breadcrumbs)
    _, primary_grade = session.ground_truth.get_primary_item()

    
    # Rendering interfaccia chat
    # NOTA: Passiamo session.conversation che è l'oggetto corretto
    result = render_chat_interface(
        conversation=session.conversation,
        conversation_manager=st.session_state.conversation_manager,
        llm_service=llm_service,
        tald_item=current_item, # Usato per l'header grafico
        grade=primary_grade,    # Usato per l'info box (solo in guidata)
        mode=session.mode
    )
    
    # --- Gestione Navigazione da Chat ---
    
    if result == "reset":
        # Torna a selezione modalità
        reset_application()
        st.rerun()

    elif result == "back_to_items":
        # Torna alla selezione item (solo guidata)
        session.phase = SessionPhase.ITEM_SELECTION
        session.conversation.clear()
        if 'chat_session' in st.session_state:
            del st.session_state['chat_session']
        st.rerun()

    elif result == True: 
        # Termina intervista -> Valutazione
        session.terminate_interview()
        if 'chat_session' in st.session_state:
            del st.session_state['chat_session']
        st.rerun()


def handle_evaluation():
    """
    Fase 4: Valutazione Finale.
    Implementa RF_6 (Form) e RF_7 (Confronto).
    """
    session = st.session_state.session
    current_item = st.session_state.current_item
    
    # Renderizza il form appropriato (Griglia 30 item o Singolo)
    user_input = render_evaluation_form(
        tald_items=st.session_state.tald_items,
        current_item=current_item,
        conversation=session.conversation,
        mode=session.mode
    )

    # --- Gestione Navigazione Uscita (Back/Reset) ---
    if user_input == "RESET":
        reset_application()
        st.rerun()
        
    elif user_input == "BACK_TO_ITEMS":
        # Reset parziale per tornare a scegliere un item (solo guidata)
        session.phase = SessionPhase.ITEM_SELECTION
        session.conversation.clear()  
        if 'chat_session' in st.session_state:  
            del st.session_state['chat_session']
        
        # Pulizia stati locali della valutazione
        keys_to_clean = ['eval_submitting', 'exploratory_sheet', 'eval_notes']
        for k in keys_to_clean:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
    
    # --- Gestione Conferma Valutazione ---
    elif user_input:
        # Se user_input è un oggetto UserEvaluation valido, procediamo
        try:
            # 1. Confronto con ground truth (Vettoriale o Singolo)
            comparison_result = ComparisonEngine.compare(
                user_evaluation=user_input,
                ground_truth=session.ground_truth
            )
            
            st.markdown("")
            
            # 2. Generazione report con Status Bar
            with st.status("🧠 Analisi clinica in corso...", expanded=True) as status:
                st.write("🔍 Elaborazione dati e confronto...")
                time.sleep(0.8)
                
                st.write("🩺 Generazione spiegazione clinica (Gemini)...")
                
                # Generazione report completo
                report = st.session_state.report_generator.generate_report(
                    ground_truth=session.ground_truth,
                    user_evaluation=user_input,
                    result=comparison_result,
                    conversation=session.conversation,
                    tald_item=current_item,
                    all_items=st.session_state.tald_items
                )

                st.write("📄 Finalizzazione documento...")
                time.sleep(0.6)
                
                status.update(label="✅ Report generato con successo!", state="complete", expanded=False)
                time.sleep(0.8)
            
            # 3. Salvataggio stato e Transizione
            session.submit_evaluation(user_input, comparison_result)
            st.session_state.report = report
            st.rerun()

        # --- GESTIONE ERRORI ---

        except LLMTimeoutError as e:
            # Timeout
            st.session_state.eval_submitting = False
            st.session_state.eval_message_type = "error"
            st.session_state.eval_message_icon = "⏱️"
            st.session_state.eval_error_message = (
                f"**Timeout Generazione Report**\n\n"
                f"Il paziente non ha risposto in tempo.\n"
                f"Puoi riprovare cliccando di nuovo."
            )
            st.rerun()  
        
        except LLMConnectionError as e:
            # Errore di Rete / API
            st.session_state.eval_submitting = False
            st.session_state.eval_message_type = "error"
            st.session_state.eval_message_icon = "🌐" 
            st.session_state.eval_error_message = f"""
            **Errore di connessione**
            
            {str(e)}
            
            **Possibili cause:**
            - Limite di richieste Gemini superato (attendi 1 minuto)
            - Quota giornaliera esaurita
            - Problemi di rete (Wi-Fi)
            
            Puoi riprovare cliccando nuovamente "Conferma Valutazione".
            """

            # Tentativo di ripristino silenzioso
            try:
                new_llm = LLMService(st.session_state.config)
                st.session_state.llm_service = new_llm
                st.session_state.report_generator = ReportGenerator(new_llm)
                st.session_state.conversation_manager.llm_service = new_llm
                if 'chat_session' in st.session_state:
                    del st.session_state['chat_session']
            except:
                pass

            st.rerun()

        except Exception as e:
            # Errore Generico
            st.session_state.eval_submitting = False
            st.session_state.eval_message_type = "error"
            st.session_state.eval_message_icon = "❌"
            st.session_state.eval_error_message = (
                f"**Errore imprevisto**\n\n"
                f"Dettagli: {str(e)}"
            )
            st.rerun()


def handle_report():
    """
    Gestisce la fase di visualizzazione report.
    
    Implementa RF_8, RF_9.
    """
    report = st.session_state.report
    
    action = render_report_view(report)
    
    if action == "new_simulation":
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

    # --- LOGICA TITOLO INTELLIGENTE PER SIDEBAR ---
    if report.ground_truth.is_guided_mode():
        # Modalità Guidata: Abbiamo un ID e un Titolo precisi
        primary_id = report.tald_item.id
        item_title = report.tald_item.title
    else:
        # Modalità Esplorativa: Creiamo un titolo riepilogativo
        primary_id = 0 # Non usato visivamente nella nuova sidebar esplorativa
        active_count = len(report.ground_truth.active_items)
        if active_count == 0:
            item_title = "Paziente Sano (Asintomatico)"
        elif active_count == 1:
            # Se c'è un solo item, proviamo a recuperare il nome, altrimenti generico
            first_id = next(iter(report.ground_truth.active_items))
            # Cerchiamo il nome nella lista completa se disponibile
            found = next((i for i in st.session_state.tald_items if i.id == first_id), None)
            item_name = found.title if found else "Singolo Disturbo"
            item_title = f"Profilo Singolo: {item_name}"
        else:
            item_title = f"Profilo Complesso ({active_count} disturbi attivi)"
    
    # Rendering del form
    result = render_feedback_form(
        item_id=primary_id,
        item_title=item_title,
        mode=report.ground_truth.mode,
        score=report.result.score
    )
    
    # Gestione navigazione 
    if result == True:
        # Utente ha cliccato "Nuova Simulazione"
        reset_application()
        st.rerun()
        
    elif result == "back_to_report":
        # Utente vuole rivedere il report
        st.session_state.show_feedback = False # Spegni flag feedback
        st.rerun()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def reset_application():
    """
    Reset dell'applicazione per nuova simulazione.

    Implementa RF_14: reset sessione.
    """
    # 1. Resetta la logica interna della sessione (torna a SELECTION)
    if 'session' in st.session_state:
        st.session_state.session.reset()

    # 2. Pulisce lo stato di Streamlit (variabili temporanee)
    keys_to_keep = [
        'initialized',
        'config',
        'tald_items',
        'llm_service',
        'conversation_manager',
        'report_generator',
        'session' # Manteniamo l'oggetto wrapper
    ]
    
    keys_to_remove = [key for key in st.session_state.keys() 
                      if key not in keys_to_keep]
    
    for key in keys_to_remove:
        del st.session_state[key]
        

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
        reset_application()
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
            # Mostra lo stato della sessione solo se esiste
            if 'session' in st.session_state:
                st.write("Session State:", st.session_state.session.to_dict())
            st.exception(e)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()