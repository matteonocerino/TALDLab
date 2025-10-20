"""
SessionState Model - Modello per gestione stato sessione

Questo modulo contiene la classe SessionState che mantiene lo stato globale
della sessione corrente, coordinando tutte le fasi dell'interazione
(selezione modalità, intervista, valutazione, report).

Entity del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum

from .conversation import ConversationHistory
from .evaluation import GroundTruth, UserEvaluation, EvaluationResult


class SessionPhase(Enum):
    """
    Enumerazione delle fasi possibili della sessione.
    
    Rappresenta il workflow dell'applicazione:
    SELECTION → ITEM_SELECTION → INTERVIEW → EVALUATION → REPORT
    """
    SELECTION = "selection"              # Selezione modalità (guidata/esplorativa)
    ITEM_SELECTION = "item_selection"    # Selezione item (solo modalità guidata)
    INTERVIEW = "interview"              # Conduzione intervista
    EVALUATION = "evaluation"            # Valutazione finale
    REPORT = "report"                    # Visualizzazione report


@dataclass
class SessionState:
    """
    Rappresenta lo stato globale della sessione corrente.
    
    Mantiene tutte le informazioni necessarie per coordinare il flusso
    dell'applicazione attraverso le diverse fasi (selezione, intervista,
    valutazione, report).
    
    Attributes:
        phase (SessionPhase): Fase corrente della sessione
        mode (Optional[str]): Modalità selezionata ("guided" o "exploratory")
        current_item_id (Optional[int]): ID dell'item TALD corrente
        ground_truth (Optional[GroundTruth]): Ground truth della simulazione
        conversation (ConversationHistory): Storico conversazionale
        user_evaluation (Optional[UserEvaluation]): Valutazione utente
        evaluation_result (Optional[EvaluationResult]): Risultato confronto
        session_id (str): Identificativo univoco della sessione
        created_at (datetime): Timestamp creazione sessione
    
    Example:
        >>> session = SessionState()
        >>> print(session.phase)
        SessionPhase.SELECTION
        >>> session.start_guided_mode(item_id=5)
        >>> print(session.is_in_interview())
        False  # Deve passare da ITEM_SELECTION prima
    """
    
    phase: SessionPhase = SessionPhase.SELECTION
    mode: Optional[str] = None
    current_item_id: Optional[int] = None
    ground_truth: Optional[GroundTruth] = None
    conversation: ConversationHistory = field(default_factory=ConversationHistory)
    user_evaluation: Optional[UserEvaluation] = None
    evaluation_result: Optional[EvaluationResult] = None
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_guided_mode(self) -> bool:
        """
        Verifica se la sessione è in modalità guidata.
        
        Returns:
            bool: True se mode = "guided"
        """
        return self.mode == "guided"
    
    def is_exploratory_mode(self) -> bool:
        """
        Verifica se la sessione è in modalità esplorativa.
        
        Returns:
            bool: True se mode = "exploratory"
        """
        return self.mode == "exploratory"
    
    def is_in_selection(self) -> bool:
        """Verifica se si è nella fase di selezione modalità."""
        return self.phase == SessionPhase.SELECTION
    
    def is_in_item_selection(self) -> bool:
        """Verifica se si è nella fase di selezione item (solo modalità guidata)."""
        return self.phase == SessionPhase.ITEM_SELECTION
    
    def is_in_interview(self) -> bool:
        """Verifica se si è nella fase di intervista."""
        return self.phase == SessionPhase.INTERVIEW
    
    def is_in_evaluation(self) -> bool:
        """Verifica se si è nella fase di valutazione."""
        return self.phase == SessionPhase.EVALUATION
    
    def is_in_report(self) -> bool:
        """Verifica se si è nella fase di visualizzazione report."""
        return self.phase == SessionPhase.REPORT
    
    def start_guided_mode(self):
        """
        Inizia la modalità guidata.
        
        Imposta la modalità su "guided" e passa alla fase di selezione item.
        """
        self.mode = "guided"
        self.phase = SessionPhase.ITEM_SELECTION
    
    def start_exploratory_mode(self, item_id: int, item_title: str, grade: int):
        """
        Inizia la modalità esplorativa con item casuale.
        
        Args:
            item_id (int): ID dell'item selezionato casualmente
            item_title (str): Titolo dell'item
            grade (int): Grado impostato per la simulazione
        """
        self.mode = "exploratory"
        self.current_item_id = item_id
        
        # Crea ground truth
        self.ground_truth = GroundTruth(
            item_id=item_id,
            item_title=item_title,
            grade=grade,
            mode="exploratory"
        )
        
        # Passa direttamente all'intervista
        self.phase = SessionPhase.INTERVIEW
    
    def set_selected_item(self, item_id: int, item_title: str, grade: int):
        """
        Imposta l'item selezionato in modalità guidata.
        
        Args:
            item_id (int): ID dell'item selezionato
            item_title (str): Titolo dell'item
            grade (int): Grado impostato per la simulazione
        """
        if not self.is_guided_mode():
            raise ValueError("Metodo disponibile solo in modalità guidata")
        
        self.current_item_id = item_id
        
        # Crea ground truth
        self.ground_truth = GroundTruth(
            item_id=item_id,
            item_title=item_title,
            grade=grade,
            mode="guided"
        )
        
        # Passa all'intervista
        self.phase = SessionPhase.INTERVIEW
    
    def terminate_interview(self):
        """
        Termina l'intervista e passa alla fase di valutazione.
        """
        if not self.is_in_interview():
            raise ValueError("Non si può terminare l'intervista se non si è in fase di intervista")
        
        self.phase = SessionPhase.EVALUATION
    
    def submit_evaluation(self, user_eval: UserEvaluation, result: EvaluationResult):
        """
        Sottomette la valutazione e passa alla visualizzazione report.
        
        Args:
            user_eval (UserEvaluation): Valutazione fornita dall'utente
            result (EvaluationResult): Risultato del confronto
        """
        if not self.is_in_evaluation():
            raise ValueError("Non si può sottomettere valutazione se non si è in fase di valutazione")
        
        self.user_evaluation = user_eval
        self.evaluation_result = result
        self.phase = SessionPhase.REPORT
    
    def get_session_duration_minutes(self) -> float:
        """
        Calcola la durata totale della sessione in minuti.
        
        Returns:
            float: Durata in minuti dall'inizio della sessione
        """
        duration = (datetime.now() - self.created_at).total_seconds()
        return round(duration / 60, 2)
    
    def get_conversation_summary(self) -> dict:
        """
        Restituisce un riepilogo della conversazione.
        
        Returns:
            dict: Statistiche conversazione
        """
        return {
            "message_count": self.conversation.get_message_count(),
            "user_messages": len(self.conversation.get_user_messages()),
            "assistant_messages": len(self.conversation.get_assistant_messages()),
            "duration_minutes": self.conversation.get_duration_minutes(),
            "total_words": self.conversation.get_total_words()
        }
    
    def reset(self):
        """
        Resetta la sessione per iniziare una nuova simulazione.
        
        Mantiene solo il session_id per tracciabilità, resetta tutto il resto.
        Utilizzato quando l'utente clicca "Avvia nuova simulazione".
        """
        self.phase = SessionPhase.SELECTION
        self.mode = None
        self.current_item_id = None
        self.ground_truth = None
        self.conversation.clear()
        self.user_evaluation = None
        self.evaluation_result = None
        # created_at viene aggiornato per tracciare la nuova simulazione
        self.created_at = datetime.now()
        # session_id rimane per continuità (opzionale: può essere rigenerato)
    
    def to_dict(self) -> dict:
        """
        Converte lo stato della sessione in dizionario.
        
        Returns:
            dict: Rappresentazione completa dello stato
        """
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "mode": self.mode,
            "current_item_id": self.current_item_id,
            "session_duration_minutes": self.get_session_duration_minutes(),
            "conversation_summary": self.get_conversation_summary(),
            "has_ground_truth": self.ground_truth is not None,
            "has_evaluation": self.user_evaluation is not None,
            "has_result": self.evaluation_result is not None,
            "created_at": self.created_at.isoformat()
        }
    
    def __str__(self) -> str:
        """Rappresentazione leggibile dello stato."""
        return (
            f"SessionState(id={self.session_id}, phase={self.phase.value}, "
            f"mode={self.mode}, messages={self.conversation.get_message_count()})"
        )