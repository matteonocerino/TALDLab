"""
Chat Interface View - Interfaccia conversazione con paziente virtuale

Questo modulo implementa l'interfaccia principale per l'intervista.
Gestisce la chat, gli errori LLM, il timeout e le statistiche real-time.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_4, RF_5, RF_11, RF_13 del RAD e mockup UI_2
"""

import streamlit as st
import base64
import os
import html
import time
import sys
import google.generativeai as genai

from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.models.conversation import ConversationHistory
from src.models.tald_item import TALDItem
from src.services.conversation_manager import ConversationManager
from src.services.llm_service import LLMService, LLMTimeoutError, LLMConnectionError


def _submit_callback():
    """Callback per gestire l'invio del messaggio ed evitare il doppio click."""
    if st.session_state.chat_text_area and st.session_state.chat_text_area.strip():
        st.session_state.pending_prompt = st.session_state.chat_text_area.strip()
        st.session_state.chat_text_area = ""


def _force_rebuild_llm_service(llm_service):
    """
    HARD RESET completo dell'LLM Service per recupero da disconnessione rete.
    Distrugge e ricrea il modello Gemini da zero, forzando un nuovo socket di rete.
    """
    try:
        # 1. Ricarica API con nuova configurazione (nuovo socket)
        genai.configure(api_key=llm_service.config['api_key'])
        
        # 2. Ricrea completamente il modello (distrugge vecchia connessione)
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Ricrea il modello da zero
        llm_service.model = genai.GenerativeModel(
            model_name=llm_service.config['model'],
            safety_settings=safety_settings
        )
        
        return True
        
    except Exception as e:
        st.error(f"⚠️ Impossibile ristabilire la connessione: {e}")
        return False


def _rebuild_session_with_history(llm_service, tald_item, grade, conversation):
    """
    Ricostruisce una sessione Gemini PULITA mantenendo la memoria dello storico.
    """
    
    # 1. Forza ricostruzione completa del modello LLM
    success = _force_rebuild_llm_service(llm_service)
    if not success:
        raise LLMConnectionError("Impossibile ricostruire il servizio LLM")

    # 2. Prepara lo storico nel formato Gemini
    history_data = []
    
    for msg in conversation.messages:
        if not msg.content:
            continue
            
        role = "user" if msg.is_user_message() else "model"
        history_data.append({
            "role": role,
            "parts": [msg.content]
        })

    # 3. Costruisci la nuova sessione con system prompt
    system_prompt = llm_service._build_system_prompt(tald_item, grade)
    
    full_history = [
        {'role': 'user', 'parts': [system_prompt]},
        {'role': 'model', 'parts': ["Ok."]}
    ] + history_data

    # 4. Crea la NUOVA sessione con il modello RICOSTRUITO
    new_session = llm_service.model.start_chat(history=full_history)
    
    return new_session


def render_chat_interface(
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    llm_service: LLMService,
    tald_item: TALDItem,
    grade: int,
    mode: str
) -> bool | str:
    """
    Renderizza l'interfaccia di chat.
    Returns: True se l'utente termina l'intervista, "reset" se torna indietro, False altrimenti.
    """

    # 1. Inizializzazione Sessione
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = llm_service.start_chat_session(tald_item, grade)

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Renderizzazione componenti statici
    _render_header(tald_item, mode)
    render_chat_sidebar(conversation, tald_item, mode)

    # Controlla se l'utente vuole tornare indietro
    if st.session_state.get("reset_requested"):
        for key in ("llm_error", "pending_prompt", "chat_session", "frozen_duration_during_retry"):
            if key in st.session_state:
                del st.session_state[key]

        if "confirm_terminate_pending" in st.session_state:
            del st.session_state["confirm_terminate_pending"]

        del st.session_state["reset_requested"]

        return "reset"

    if st.session_state.get("back_to_item_selection"):
        for key in ("llm_error", "pending_prompt", "chat_session", "frozen_duration_during_retry"):
            if key in st.session_state:
                del st.session_state[key]

        if "confirm_terminate_pending" in st.session_state:
            del st.session_state["confirm_terminate_pending"]

        del st.session_state["back_to_item_selection"]

        return "back_to_items"


    # --- Visualizzazione Errori (IN ALTO) ---
    if "llm_error" in st.session_state:
        _handle_llm_error_display(
            conversation, tald_item, grade, llm_service, mode
        )

    if conversation.get_message_count() == 0:
        _render_initial_instructions(mode, tald_item if mode == "guided" else None)

    # --- Renderizzazione Storico Chat ---
    chat_container = st.container()
    with chat_container:
        for msg in conversation.messages:
            role = "user" if msg.is_user_message() else "assistant"
            avatar = "🧑‍⚕️" if role == "user" else "👤"
            bubble_class = "chat-bubble-user" if role == "user" else "chat-bubble-assistant"

            st.markdown(
                f"""
                <div class="{bubble_class}">
                    <div class="chat-avatar">{avatar}</div>
                    <div class="chat-text">{html.escape(msg.content)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # --- Logica di Processing ---
    # Esegue solo se NON c'è un errore attivo
    if "llm_error" not in st.session_state:
        
        # Fase 1: Prepara il prompt
        if st.session_state.get("pending_prompt") and not st.session_state.is_processing:
            st.session_state.is_processing = True
            prompt = st.session_state.pop("pending_prompt")

            # Aggiungi SOLO se non è già presente (evita duplicati su retry)
            should_add_to_history = True
            if conversation.messages:
                last_msg = conversation.messages[-1]
                if last_msg.is_user_message() and last_msg.content == prompt:
                    should_add_to_history = False
            
            if should_add_to_history:
                conversation_manager.add_user_message(conversation, prompt)
            
            # Imposta per elaborazione
            st.session_state.current_prompt_processing = prompt
            st.rerun()

        # Fase 2: Chiama l'LLM
        if st.session_state.is_processing and st.session_state.get("current_prompt_processing"):
            prompt = st.session_state.pop("current_prompt_processing")

            # 1. Placeholder per i pallini (sotto la chat attuale)
            typing_placeholder = st.empty()
            
            # 2. Mostra l'animazione HTML
            typing_placeholder.markdown("""
                <div class="chat-bubble-assistant">
                    <div class="chat-avatar">👤</div>
                    <div class="chat-text">
                        <div class="typing-indicator-container">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            try:
                start_time = time.time()
                    
                conversation_manager.get_assistant_response(
                    chat_session=st.session_state.chat_session,
                    conversation=conversation,
                    user_message=prompt
                )

                elapsed_time = time.time() - start_time # Tempo impiegato per generare QUESTA risposta

                # Se stiamo recuperando da un errore (Riprova), dobbiamo "cucire" il tempo
                # ignorando i minuti passati nell'errore.
                if "frozen_duration_during_retry" in st.session_state:
                    
                    # 1. Recuperiamo quanto doveva essere il tempo prima di questa generazione
                    frozen_minutes = st.session_state["frozen_duration_during_retry"]
                    
                    # 2. Calcoliamo quanto tempo di generazione (in minuti) abbiamo appena speso
                    elapsed_minutes = elapsed_time / 60.0
                    
                    # 3. Il nuovo "Totale Ideale" dovrebbe essere: Vecchio Totale + Tempo Generazione
                    target_total_minutes = frozen_minutes + elapsed_minutes
                    
                    # 4. Vediamo quanto segna l'orologio "reale" (che include il tempo perso nell'errore)
                    current_real_minutes = conversation.get_duration_minutes()
                    
                    # 5. Calcoliamo il tempo "morto" da sottrarre
                    dead_time_minutes = current_real_minutes - target_total_minutes
                    
                    # 6. Spostiamo l'inizio della sessione in avanti per nascondere il tempo morto
                    if dead_time_minutes > 0:
                         conversation.session_start += timedelta(minutes=dead_time_minutes)
        
                    # Pulizia
                    del st.session_state["frozen_duration_during_retry"]
                
            except Exception as e:
                # Rimuovi la risposta assistant incompleta (se presente)
                if conversation.messages and not conversation.messages[-1].is_user_message():
                    conversation.messages.pop()
    
                # Rimuovi anche l'ultimo messaggio utente rimasto senza risposta
                if conversation.messages and conversation.messages[-1].is_user_message():
                    conversation.messages.pop()

                # === CALCOLO MINUTI CONGELATI ===
                # Salviamo i minuti validi attuali (che ora puntano all'ultimo messaggio di successo)
                frozen_duration = conversation.get_duration_minutes()

                # Classifica errore
                error_type = "Generic"
                error_message = str(e)
                
                if isinstance(e, LLMTimeoutError):
                    error_type = "Timeout"
                elif isinstance(e, LLMConnectionError):
                    error_type = "Connection"
                elif "network" in error_message.lower() or "connection" in error_message.lower():
                    error_type = "Connection"
                    error_message = "Errore di rete. Verifica la connessione e riprova."
                
                # Salva stato errore
                st.session_state.llm_error = {
                    "type": error_type,
                    "message": error_message,
                    "last_prompt": prompt,
                    "frozen_duration": frozen_duration # Salviamo il tempo "congelato"
                }
                
                # Distruggi sessione corrotta
                if "chat_session" in st.session_state:
                    del st.session_state["chat_session"]
                
            finally:
                typing_placeholder.empty()
                st.session_state.is_processing = False
                st.rerun()

    st.markdown("---")

    # --- Area Input ---
    input_disabled = (
    st.session_state.is_processing or 
    "llm_error" in st.session_state or
    st.session_state.get("confirm_terminate_pending", False)
)

    st.text_area(
        "Scrivi qui la tua domanda...",
        key="chat_text_area",
        placeholder="Scrivi la tua domanda per il paziente virtuale...",
        label_visibility="collapsed",
        height=80,
        disabled=input_disabled
    )

    col1, col2 = st.columns(2)
    
    with col1:
        terminate = st.button(
            "⏹️ Termina", 
            use_container_width=True,
            disabled=st.session_state.is_processing or st.session_state.get("confirm_terminate_pending", False)
        )
        
    with col2:
        st.button(
            "Invia ➤", 
            use_container_width=True,
            disabled=input_disabled,
            on_click=_submit_callback
        )

    # LOGICA TERMINATE (dopo aver creato il bottone)
    if terminate:
        if conversation.get_message_count() < 2:
            st.warning("⚠️ Conduci almeno uno scambio domanda–risposta prima di terminare.")
        else:
            # Salva stato "conferma termina" per disabilitare input
            st.session_state.confirm_terminate_pending = True
            st.rerun()

    # MOSTRA WARNING DI CONFERMA (dopo i bottoni, con spaziatura)
    if st.session_state.get("confirm_terminate_pending", False): 
        st.markdown("---")
        st.markdown("") 
    
        _, center_col, _ = st.columns([1, 3, 1])
    
        with center_col:
            with st.container(border=True):
                st.warning("""
                ⚠️ **Stai per terminare l'intervista**
            
                Una volta terminata, non potrai più interagire con il paziente.
                Sei sicuro di aver raccolto abbastanza informazioni?
                """)

                b1, b2 = st.columns([1, 1])
            
                with b1:
                    if st.button("❌ Annulla", use_container_width=True, key="btn_cancel_terminate"):
                        del st.session_state["confirm_terminate_pending"]
                        st.rerun()
                
                with b2:
                    if st.button("✅ Conferma e Valuta", use_container_width=True, type="primary", key="btn_confirm_terminate"):
                        del st.session_state["confirm_terminate_pending"]
                        return True

    return False


def _handle_llm_error_display(conversation, tald_item, grade, llm_service, mode):
    """
    Mostra l'errore e le opzioni di recupero.
    """
    error = st.session_state['llm_error']
    last_prompt = error.get("last_prompt")
    error_type = error.get("type", "Generic")
    error_message = error.get("message", "Errore sconosciuto")

    _, center_col, _ = st.columns([1, 3, 1])
    
    with center_col:
        with st.container(border=True):
            if error_type == "Timeout":
                st.error("⏱️ **Timeout:** Il paziente non ha risposto entro i tempi previsti.")
            elif error_type == "Connection":
                st.error(f"❌ **Errore di Connessione**\n\n{error_message}")
                st.info("💡 **Suggerimento:** Se hai perso la connessione, verifica che il Wi-Fi sia attivo e clicca su Riprova.")
            else:
                st.error(f"⚠️ **Errore:** {error_message}")

            b1, b2 = st.columns([1, 1])
        
            # TASTO SCARICA
            with b1:
                # Genera il contenuto SOLO al momento del click, non prima
                st.download_button(
                    label="💾 Salva Trascrizione",
                    data=_generate_transcript_content(conversation, tald_item, mode),
                    file_name=f"TALD_Trascrizione_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"download_transcript_{datetime.now().timestamp()}"  
                )

            # TASTO RIPROVA
            with b2:
                if st.button("🔄 Riprova invio messaggio", use_container_width=True, type="primary"):
                
                    try:
                        # Recupera il tempo congelato
                        saved_frozen_duration = st.session_state.llm_error.get("frozen_duration", conversation.get_duration_minutes())

                       # Chiama la funzione helper 
                        new_session = _rebuild_session_with_history(
                            llm_service, tald_item, grade, conversation
                        )
                    
                        # Aggiorna la sessione
                        st.session_state.chat_session = new_session
                    
                        # Rimette il prompt in coda
                        st.session_state.pending_prompt = last_prompt

                        # IMPORTANTE: Passa il tempo congelato alla fase successiva
                        st.session_state.frozen_duration_during_retry = saved_frozen_duration
                    
                        # Rimuove l'errore
                        del st.session_state["llm_error"]
                    
                        # Riavvia
                        st.rerun()
                    
                    except Exception as rebuild_error:
                        st.error(f"❌ Impossibile ricostruire la sessione: {rebuild_error}")


def _generate_transcript_content(conversation, tald_item, mode):
    """Genera il testo della trascrizione in memoria."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        "="*60,
        " TALDLab - Trascrizione Intervista Clinica",
        "="*60,
        f"Data:      {timestamp}",
        f"Durata:    {conversation.get_duration_minutes()} minuti",
        f"Messaggi:  {conversation.get_message_count()}",
        "-"*60,
    ]
    
    # Mostra info in base alla modalità
    if mode == "guided":
        # In guidata: mostra solo item, NON il grado (deve indovinarlo)
        header.append(f"Item TALD: {tald_item.id}. {tald_item.title} ({tald_item.type})")
        header.append(f"Grado:     [da valutare]")
    else:
        # In esplorativa: non mostra nulla (deve indovinare tutto)
        header.append(f"Item TALD: [da identificare]")
        header.append(f"Grado:     [da valutare]")
    
    header.extend([
        "="*60,
        "\n"
    ])
    
    return "\n".join(header) + conversation.to_text_transcript()


def _render_header(tald_item: TALDItem, mode: str):
    """Renderizza l'header e il brand."""
    logo_path = os.path.join("assets", "taldlab_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_element_html = f'<img src="data:image/png;base64,{b64_logo}" alt="TALDLab logo" />'
    else:
        logo_element_html = '<div class="emoji-fallback">🧠</div>'
    
    title = f"Intervista: {tald_item.title}" if mode == "guided" else "Intervista Esplorativa"
    
    st.markdown(f"""
    <div class="brand">
        {logo_element_html}
        <div class="brand-text-container">
            <div class="brand-title">{title}</div>
            <div class="brand-sub">Conduzione colloquio con Paziente Virtuale</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    mode_label = "🎯 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    st.markdown(f'<p class="breadcrumb"><strong>{mode_label}</strong> › Intervista</p>', unsafe_allow_html=True)
    st.markdown("---")


def _render_initial_instructions(mode: str, tald_item: Optional[TALDItem] = None):
    """Renderizza il box istruzioni iniziale."""
    if mode == "guided":
        st.info(f"**Obiettivo:** Interagisci con il paziente per osservare le manifestazioni di **{tald_item.title}** e valutarne il grado.")
    else:
        st.info("**Obiettivo:** Interagisci con il paziente per **identificare il disturbo** nascosto e valutarne il grado.")


def render_chat_sidebar(conversation: ConversationHistory, tald_item: TALDItem, mode: str):
    """Renderizza la sidebar con statistiche e info item."""
    with st.sidebar:
        st.markdown("## 📊 Monitoraggio")
        col1, col2 = st.columns(2)

        # Se c'è un errore attivo, mostriamo il tempo congelato (l'ultimo valido)
        if "llm_error" in st.session_state and "frozen_duration" in st.session_state.llm_error:
            display_minutes = st.session_state.llm_error["frozen_duration"]
        # Se stiamo riprovando, mostriamo ancora il tempo congelato finché non finisce
        elif "frozen_duration_during_retry" in st.session_state:
            display_minutes = st.session_state.frozen_duration_during_retry
        else:
            # Altrimenti tempo normale
            display_minutes = conversation.get_duration_minutes()

        with col1: st.metric("Messaggi", conversation.get_message_count())
        with col2: st.metric("Minuti", display_minutes)
        st.caption(f"Parole scambiate: {conversation.get_total_words()}")
        
        st.markdown("---")
        if mode == "guided":
            st.markdown(f"## 🎯 Item in Osservazione")
            st.info(f"**{tald_item.id}. {tald_item.title}**")
            with st.expander("📖 Rivedi dettagli item"):
                st.markdown(f"**Tipo:** {tald_item.type.capitalize()}")
                st.markdown(f"**Descrizione:** *{tald_item.description}*")
        else:
            st.markdown("## 🔍 Obiettivo")
            st.warning("**Identifica l'item TALD** e il suo grado di manifestazione.")
        
        st.markdown("---")
        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Fai **domande aperte** (es. "Parlami della tua giornata...").
        - Osserva i **pattern linguistici** ricorrenti.
        - Se necessario, poni domande dirette relative ai **criteri diagnostici**.
        """)

        st.markdown("---")

        if st.session_state.get("confirm_back_chat"):
            st.warning("""
            ⚠️ **Attenzione**

            Tornando indietro perderai l’intervista corrente.
            Confermi?
            """)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("❌ Annulla", use_container_width=True, key="cancel_back_chat"):
                    del st.session_state["confirm_back_chat"]
                    st.rerun()

            with col2:
                if st.button("✅ Conferma", use_container_width=True, key="confirm_back_chat_ok"):
                    del st.session_state["confirm_back_chat"]
                    if mode == "guided":
                        st.session_state.back_to_item_selection = True
                    else:
                        st.session_state.reset_requested = True
                    st.rerun()

        else:
            if mode == "guided":
                if st.button("← Torna a Selezione Item", use_container_width=True):
                    st.session_state["confirm_back_chat"] = True
                    st.rerun()
            else:
                if st.button("← Torna a Selezione Modalità", use_container_width=True):
                    st.session_state["confirm_back_chat"] = True
                    st.rerun()