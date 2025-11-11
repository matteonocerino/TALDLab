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

# Import relativi per compatibilità con la struttura del progetto
from ..models.tald_item import TALDItem
from ..models.conversation import ConversationHistory, ConversationMessage
from .llm_service import LLMService, LLMTimeoutError, LLMConnectionError


class ConversationManager:
    """
    Service per coordinamento del flusso conversazionale.
    
    Responsabilità:
    - Gestire l'aggiunta di messaggi allo storico (RF_5, RF_13)
    - Coordinare le chiamate all'LLMService (RF_4)
    - Mantenere coerenza della conversazione (RF_5)
    - Gestire timeout ed errori come da RAD (RF_11)
    - Esportare trascrizioni in caso di interruzioni (RF_11)
    
    Attributes:
        llm_service (LLMService): Servizio LLM per generazione risposte
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Inizializza il ConversationManager.
        
        Args:
            llm_service (LLMService): Servizio LLM configurato
        """
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
        # Validazione input
        if not message or not message.strip():
            raise ValueError("Il messaggio non può essere vuoto")
        
        # Aggiunge messaggio allo storico
        msg = conversation.add_message("user", message.strip())
        
        return msg
    
    def get_assistant_response(
        self,
        conversation: ConversationHistory,
        user_message: str,
        tald_item: TALDItem,
        grade: int,
        patient_background: Optional[str] = None
    ) -> str:
        """
        Ottiene la risposta del paziente virtuale tramite LLM.
        
        Questo è il metodo principale che:
        1. Chiama l'LLMService per generare la risposta
        2. Aggiunge la risposta allo storico
        3. Gestisce timeout ed errori come da RAD RF_11
        """
        try:
            # Chiama LLMService per generare risposta
            response_text = self.llm_service.generate_response(
                user_message=user_message,
                conversation_history=conversation,
                tald_item=tald_item,
                grade=grade,
                patient_background=patient_background
            )
            
            # Aggiunge risposta allo storico
            conversation.add_message("assistant", response_text)
            
            return response_text
        
        except LLMTimeoutError:
            # Propaga il timeout per gestione nel chiamante (View)
            # Come da RAD RF_11: l'utente deve vedere opzioni di recupero
            raise
        
        except LLMConnectionError:
            # Propaga errore connessione per gestione nel chiamante
            raise
        
        except Exception as e:
            # Qualsiasi altro errore viene wrappato
            raise LLMConnectionError(f"Errore imprevisto durante generazione risposta: {e}") from e
    
    def export_transcript(
        self, 
        conversation: ConversationHistory,
        tald_item: Optional[TALDItem] = None,
        grade: Optional[int] = None
    ) -> str:
        """
        Esporta la trascrizione della conversazione in un file .txt.
        
        Implementa RF_11: salvataggio trascrizione in caso di timeout/errori.
        Utilizzato quando l'utente sceglie "Salva trascrizione" dopo un timeout.
        """
        # Genera nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(f"TALDLab_Trascrizione_{timestamp}.txt")
        
        # Prepara contenuto
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
        
        # Aggiunge trascrizione
        lines.append(conversation.to_text_transcript())
        
        lines.append("\n" + "="*70)
        lines.append("Fine trascrizione")
        lines.append("="*70)
        
        # Salva file in modo sicuro
        content = "\n".join(lines)
        filename.write_text(content, encoding="utf-8")
        
        return str(filename)
    
    def validate_conversation_state(self, conversation: ConversationHistory) -> bool:
        """
        Valida che la conversazione sia in uno stato valido.
        
        Verifica:
        - Che ci siano messaggi
        - Che l'alternanza user/assistant sia corretta
        - Che non ci siano messaggi vuoti
        """
        if conversation.get_message_count() == 0:
            return True  # Conversazione vuota è valida (inizio)
        
        messages = conversation.messages
        
        # Verifica messaggi non vuoti
        for msg in messages:
            if not msg.content or not msg.content.strip():
                raise ValueError("Trovato messaggio vuoto nello storico")
        
        # Verifica alternanza corretta (primo messaggio deve essere user)
        if messages[0].role != "user":
            raise ValueError("Il primo messaggio deve essere dell'utente")
        
        # Verifica alternanza user/assistant
        for i in range(len(messages) - 1):
            if messages[i].role == messages[i + 1].role:
                raise ValueError(
                    f"Alternanza messaggi non valida alla posizione {i}: "
                    f"due messaggi consecutivi con role '{messages[i].role}'"
                )
        
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
        """
        Resetta la conversazione per una nuova simulazione.
        
        Implementa RF_14: reset sessione.
        """
        conversation.clear()