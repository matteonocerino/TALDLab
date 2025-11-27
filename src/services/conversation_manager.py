"""
ConversationManager - Servizio per coordinamento flusso conversazionale

Questo modulo gestisce il flusso dell'intervista tra utente e paziente virtuale:
- Aggiunta messaggi allo storico
- Coordinamento chiamate LLM
- Gestione errori e timeout
- Export trascrizioni

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_4, RF_5, RF_11, RF_13 del RAD
"""

from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

from src.models.tald_item import TALDItem
from src.models.conversation import ConversationHistory, ConversationMessage
from src.services.llm_service import LLMService, LLMTimeoutError, LLMConnectionError


class ConversationManager:
    """
    Service per coordinamento del flusso conversazionale.
    
    Responsabilità:
    - Gestire l'aggiunta di messaggi allo storico (RF_5, RF_13)
    - Coordinare le chiamate all'LLMService (RF_4)
    - Mantenere coerenza della conversazione (RF_5)
    - Gestire timeout ed errori come da RAD (RF_11)
    - Esportare trascrizioni in caso di interruzioni (RF_11)
    """
    
    def __init__(self, llm_service: LLMService):
        """Inizializza il ConversationManager con il servizio LLM."""
        self.llm_service = llm_service
    
    def add_user_message(
        self, 
        conversation: ConversationHistory, 
        message: str
    ) -> ConversationMessage:
        """
        Aggiunge un messaggio dell'utente allo storico.
        Implementa RF_5: gestione storico conversazionale.
        """
        if not message or not message.strip():
            raise ValueError("Il messaggio non può essere vuoto")
        
        msg = conversation.add_message("user", message.strip())
        return msg
    
    def get_assistant_response(
        self,
        chat_session,
        conversation: ConversationHistory,
        user_message: str
    ) -> str:
        """
        Ottiene la risposta del paziente virtuale tramite LLM.
        
        Coordina la chiamata al servizio esterno e l'aggiornamento dello storico.
        Gestisce timeout ed errori di connessione (RF_11).
        
        Args:
            chat_session: Oggetto sessione gestito da LLMService
            conversation: Storico conversazionale (Entity)
            user_message: Ultimo messaggio utente
        """
        try:
            # Generazione risposta tramite LLM
            response_text = self.llm_service.generate_response(
                chat_session=chat_session,
                user_message=user_message
            )
            
            # Aggiornamento storico locale
            conversation.add_message("assistant", response_text)
            
            return response_text
        
        except LLMTimeoutError:
            raise
        except LLMConnectionError:
            raise
        except Exception as e:
            raise LLMConnectionError(f"Errore imprevisto durante generazione risposta: {e}") from e
    
    def export_transcript(
        self, 
        conversation: ConversationHistory,
        tald_item: Optional[TALDItem] = None,
        grade: Optional[int] = None
    ) -> str:
        """
        Esporta la trascrizione della conversazione in un file .txt locale.
        Implementa RF_11: salvataggio trascrizione per recupero sessione.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(f"TALDLab_Trascrizione_{timestamp}.txt")
        
        lines = []
        lines.append("="*70)
        lines.append("TALDLab - Trascrizione Intervista")
        lines.append("="*70)
        lines.append(f"\nData: {conversation.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Durata: {conversation.get_duration_minutes()} minuti")
        lines.append(f"Messaggi totali: {conversation.get_message_count()}")
        lines.append(f"Parole totali: {conversation.get_total_words()}")
        
        if tald_item:
            lines.append(f"\nItem TALD simulato: {tald_item.id}. {tald_item.title}")
            lines.append(f"Tipo: {tald_item.type}")
            if grade is not None:
                lines.append(f"Grado: {grade}/4")
        
        lines.append("\n" + "="*70)
        lines.append("TRASCRIZIONE")
        lines.append("="*70 + "\n")
        
        lines.append(conversation.to_text_transcript())
        
        lines.append("\n" + "="*70)
        lines.append("Fine trascrizione")
        lines.append("="*70)
        
        content = "\n".join(lines)
        filename.write_text(content, encoding="utf-8")
        
        return str(filename)
    
    def validate_conversation_state(self, conversation: ConversationHistory) -> bool:
        """Valida la consistenza dello storico della conversazione."""
        if conversation.get_message_count() == 0:
            return True
        
        messages = conversation.messages
        
        for msg in messages:
            if not msg.content or not msg.content.strip():
                raise ValueError("Trovato messaggio vuoto nello storico")
        
        if messages[0].role != "user":
            raise ValueError("Il primo messaggio deve essere dell'utente")
        
        for i in range(len(messages) - 1):
            if messages[i].role == messages[i + 1].role:
                raise ValueError(f"Alternanza messaggi non valida alla posizione {i}")
        
        return True
    
    def get_conversation_stats(self, conversation: ConversationHistory) -> Dict[str, object]:
        """
        Restituisce statistiche sulla conversazione corrente.
        
        Utile per debugging e per mostrare info all'utente nella sidebar.
        """
        return {
            "total_messages": conversation.get_message_count(),
            "user_messages": len(conversation.get_user_messages()),
            "assistant_messages": len(conversation.get_assistant_messages()),
            "duration_minutes": conversation.get_duration_minutes(),
            "total_words": conversation.get_total_words(),
            "session_start": conversation.session_start.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def clear_conversation(self, conversation: ConversationHistory):
        """Resetta la conversazione (RF_14)."""
        conversation.clear()