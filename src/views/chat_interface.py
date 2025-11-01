"""
Chat Interface View - Interfaccia conversazione con paziente virtuale

Questo modulo implementa l'interfaccia principale per l'intervista.
Gestisce la chat, gli errori LLM, il timeout e le statistiche real-time.

Boundary del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_4, RF_5, RF_11, RF_13 del RAD e mockup UI_2
"""

import streamlit as st
import time
from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.conversation import ConversationHistory
from src.models.tald_item import TALDItem
from src.services.conversation_manager import ConversationManager
from src.services.llm_service import LLMTimeoutError, LLMConnectionError


def render_chat_interface(
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    tald_item: TALDItem,
    grade: int,
    mode: str
) -> bool:
    """
    Renderizza l'interfaccia di chat per l'intervista con il paziente virtuale.
    
    Implementa RF_4: interazione linguaggio naturale
    Implementa RF_5: gestione storico conversazionale
    Implementa RF_11: gestione errori e timeout
    Implementa RF_13: visualizzazione storico
    
    Args:
        conversation (ConversationHistory): Storico conversazione corrente
        conversation_manager (ConversationManager): Manager per coordinamento
        tald_item (TALDItem): Item TALD simulato
        grade (int): Grado di severità (0-4)
        mode (str): "guided" o "exploratory"
        
    Returns:
        bool: True se l'utente ha cliccato "Termina Intervista"
    """
    
    # CSS minimo per chat bubbles (coerente con views precedenti)
    st.markdown("""
    <style>
    .chat-message {
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 15px;
        max-width: 80%;
    }
    .chat-message.user {
        background: #e3f2fd;
        margin-left: auto;
        border-left: 4px solid #2196f3;
    }
    .chat-message.assistant {
        background: #fff3e0;
        border-left: 4px solid #ff6b6b;
    }
    .message-time {
        font-size: 0.75rem;
        color: #95a5a6;
        margin-top: 0.3rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header con logo
    _render_header(tald_item, mode)
    
    # Breadcrumb
    mode_label = "📚 Modalità Guidata" if mode == "guided" else "🔍 Modalità Esplorativa"
    st.markdown(f"**{mode_label}** › Intervista")
    st.markdown("---")
    
    # Layout: Sidebar + Chat
    render_chat_sidebar(conversation, tald_item, mode)
    
    # Istruzioni iniziali (se chat vuota)
    if conversation.get_message_count() == 0:
        _render_initial_instructions(mode, tald_item if mode == "guided" else None)
    
    # Storico conversazionale (RF_13)
    st.markdown("### 💬 Conversazione")
    _render_conversation_history(conversation)
    
    st.markdown("---")
    
    # Area input
    with st.form(key="message_form", clear_on_submit=True):
        user_input = st.text_area(
            "La tua domanda:",
            placeholder="Scrivi la tua domanda per il paziente virtuale...",
            height=80,
            label_visibility="collapsed",
            key="user_input"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.form_submit_button(
                "Invia ➤",
                use_container_width=True,
                type="primary"
            )
    
    # Pulsante termina intervista
    st.markdown("")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        terminate_button = st.button(
            "⏹️ Termina Intervista",
            use_container_width=True,
            type="secondary",
            key="terminate_interview"
        )
    
    # Gestione invio messaggio
    if submit_button and user_input and user_input.strip():
        _handle_user_message(
            user_input=user_input.strip(),
            conversation=conversation,
            conversation_manager=conversation_manager,
            tald_item=tald_item,
            grade=grade
        )
        st.rerun()
    
    # Gestione terminazione intervista
    if terminate_button:
        if conversation.get_message_count() < 2:
            st.warning("⚠️ Conduci almeno uno scambio conversazionale prima di terminare.")
        else:
            return True
    
    return False


def _render_header(tald_item: TALDItem, mode: str):
    """Renderizza header con logo."""
    header_col1, header_col2 = st.columns([1, 11])
    
    with header_col1:
        try:
            st.image("assets/taldlab_logo.png", width=60)
        except:
            st.markdown("<div style='font-size: 3rem;'>🧠</div>", unsafe_allow_html=True)
    
    with header_col2:
        if mode == "guided":
            st.markdown(f"""
            <div style="margin-top: 5px;">
                <h2 style="margin: 0; color: #2c3e50;">Intervista: {tald_item.title}</h2>
                <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">
                    {tald_item.type.capitalize()}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="margin-top: 5px;">
                <h2 style="margin: 0; color: #2c3e50;">Intervista Esplorativa</h2>
                <p style="color: #7f8c8d; margin: 0; font-size: 0.9rem;">
                    Item nascosto - Identifica il disturbo
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("")


def _render_initial_instructions(mode: str, tald_item: Optional[TALDItem] = None):
    """Renderizza istruzioni iniziali."""
    if mode == "guided":
        st.info(f"""
        **📋 Item da osservare:** {tald_item.title}
        
        Conduci l'intervista ponendo domande al paziente virtuale. 
        Al termine, dovrai valutare il **grado di severità** (0-4) del disturbo osservato.
        
        💡 **Suggerimento:** Fai domande aperte per osservare le manifestazioni linguistiche.
        """)
    else:
        st.info("""
        **🔍 Modalità Esplorativa Attiva**
        
        L'item TALD è nascosto. Conduci l'intervista per:
        1. **Identificare** quale disturbo manifesta il paziente
        2. **Valutare** il grado di severità osservato (0-4)
        
        💡 **Suggerimento:** Osserva attentamente i pattern linguistici.
        """)
    
    st.markdown("")


def _render_conversation_history(conversation: ConversationHistory):
    """
    Renderizza lo storico completo della conversazione.
    
    Implementa RF_13: visualizzazione storico conversazionale.
    """
    if conversation.get_message_count() == 0:
        st.info("👋 **Nessun messaggio ancora.** Inizia l'intervista ponendo una domanda al paziente.")
        return
    
    # Mostra messaggi
    for msg in conversation.messages:
        if msg.is_user_message():
            # Messaggio utente (blu)
            st.markdown(f"""
            <div class="chat-message user">
                <strong>Tu:</strong><br>
                {msg.content}
                <div class="message-time">{msg.get_formatted_time("%H:%M")}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Messaggio paziente (arancione)
            st.markdown(f"""
            <div class="chat-message assistant">
                <strong>Paziente:</strong><br>
                {msg.content}
                <div class="message-time">{msg.get_formatted_time("%H:%M")}</div>
            </div>
            """, unsafe_allow_html=True)


def _handle_user_message(
    user_input: str,
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    tald_item: TALDItem,
    grade: int
):
    """
    Gestisce invio messaggio e risposta paziente.
    
    Implementa RF_11: gestione errori e timeout.
    """
    # Aggiunge messaggio utente
    conversation_manager.add_user_message(conversation, user_input)
    
    # Loading
    with st.spinner("🤔 Il paziente sta pensando..."):
        try:
            # Ottiene risposta (timeout 30s)
            response = conversation_manager.get_assistant_response(
                conversation=conversation,
                user_message=user_input,
                tald_item=tald_item,
                grade=grade
            )
            
        except LLMTimeoutError:
            _handle_timeout_error(conversation, conversation_manager, tald_item, grade)
            
        except LLMConnectionError as e:
            _handle_connection_error(str(e), conversation, conversation_manager, tald_item, grade)


def _handle_timeout_error(
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    tald_item: TALDItem,
    grade: int
):
    """Gestisce timeout >30s (RF_11)."""
    st.error("""
    ⏱️ **Timeout: Il servizio LLM non risponde**
    
    La richiesta ha superato il limite di 30 secondi.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Riprova", use_container_width=True, type="primary", key="retry_timeout"):
            if conversation.messages and conversation.messages[-1].is_user_message():
                user_msg = conversation.messages[-1].content
                conversation.messages.pop()
                _handle_user_message(user_msg, conversation, conversation_manager, tald_item, grade)
                st.rerun()
    
    with col2:
        if st.button("💾 Salva Trascrizione", use_container_width=True, key="save_timeout"):
            _export_transcript(conversation, conversation_manager, tald_item, grade)


def _handle_connection_error(
    error_message: str,
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    tald_item: TALDItem,
    grade: int
):
    """Gestisce errori connessione (RF_11)."""
    st.error(f"""
    ❌ **Errore di connessione**
    
    {error_message}
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Riprova", use_container_width=True, type="primary", key="retry_conn"):
            st.rerun()
    
    with col2:
        if st.button("💾 Salva Trascrizione", use_container_width=True, key="save_conn"):
            _export_transcript(conversation, conversation_manager, tald_item, grade)


def _export_transcript(
    conversation: ConversationHistory,
    conversation_manager: ConversationManager,
    tald_item: TALDItem,
    grade: int
):
    """Esporta trascrizione."""
    try:
        filepath = conversation_manager.export_transcript(conversation, tald_item, grade)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        st.download_button(
            label="⬇️ Scarica Trascrizione",
            data=content,
            file_name=filepath,
            mime="text/plain",
            use_container_width=True
        )
        
        st.success(f"✅ Salvata: {filepath}")
        
    except Exception as e:
        st.error(f"Errore: {e}")


def render_chat_sidebar(
    conversation: ConversationHistory,
    tald_item: TALDItem,
    mode: str
):
    """Renderizza sidebar con statistiche."""
    with st.sidebar:
        st.markdown("## 📊 Statistiche Intervista")
        
        # Metriche
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Messaggi", conversation.get_message_count())
        
        with col2:
            st.metric("Durata", f"{conversation.get_duration_minutes()} min")
        
        # Dettagli
        st.markdown(f"""
        **Dettagli:**
        - Tue domande: {len(conversation.get_user_messages())}
        - Risposte: {len(conversation.get_assistant_messages())}
        - Parole: {conversation.get_total_words()}
        """)
        
        st.markdown("---")
        
        # Info item
        if mode == "guided":
            st.markdown("## 📋 Item TALD")
            st.info(f"""
            **{tald_item.id}. {tald_item.title}**
            
            Tipo: {tald_item.type.capitalize()}
            """)
            
            with st.expander("📖 Descrizione"):
                st.markdown(tald_item.description)
        else:
            st.warning("""
            **🔍 Item nascosto**
            
            Osserva le manifestazioni per identificarlo.
            """)
        
        st.markdown("---")
        
        # Suggerimenti
        st.markdown("## 💡 Suggerimenti")
        st.markdown("""
        - Fai **domande aperte**
        - Osserva **pattern linguistici**
        - Nota **coerenza** risposte
        - Valuta **severità**
        """)
        
        st.markdown("---")
        
        # Export
        if st.button("💾 Esporta Trascrizione", use_container_width=True):
            if conversation.get_message_count() > 0:
                transcript = conversation.to_text_transcript()
                st.download_button(
                    label="⬇️ Scarica",
                    data=transcript,
                    file_name=f"trascrizione_{conversation.session_start.strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.warning("Nessun messaggio")