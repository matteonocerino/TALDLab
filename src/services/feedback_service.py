"""
FeedbackService - Servizio per gestione feedback utenti

Questo modulo gestisce la raccolta e persistenza dei feedback:
- Validazione dati feedback
- Anonimizzazione (nessun dato identificativo)
- Salvataggio in feedback_log.json (append-only)
- Aggiunta metadati (timestamp, modalità, item)

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_10 del RAD
"""

import json
from datetime import datetime
from typing import Optional
from pathlib import Path


class Feedback:
    """
    Rappresenta un feedback utente.
    
    Entity per i feedback raccolti post-simulazione.
    
    Attributes:
        overall_rating (int): Valutazione generale (1-5)
        realism_rating (int): Realismo simulazione (1-5)
        usefulness_rating (int): Utilità didattica (1-5)
        comments (str): Commenti liberi
        metadata (dict): Metadati non identificativi (item, modalità, timestamp)
    """
    
    def __init__(
        self,
        overall_rating: Optional[int] = None,
        realism_rating: Optional[int] = None,
        usefulness_rating: Optional[int] = None,
        comments: str = "",
        metadata: Optional[dict] = None
    ):
        self.overall_rating = overall_rating
        self.realism_rating = realism_rating
        self.usefulness_rating = usefulness_rating
        self.comments = comments
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Converte feedback in dizionario per JSON."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "ratings": {
                "overall": self.overall_rating,
                "realism": self.realism_rating,
                "usefulness": self.usefulness_rating
            },
            "comments": self.comments,
            "metadata": self.metadata
        }


class FeedbackService:
    """
    Service per gestione raccolta e persistenza feedback.
    
    Responsabilità:
    - Validare dati feedback (RF_10)
    - Anonimizzare (nessun dato identificativo)
    - Salvare in feedback_log.json in modalità append
    - Aggiungere metadati non identificativi
    
    Come da RAD 2.6.1 - FeedbackService:
    "Gestisce la raccolta e persistenza del feedback qualitativo.
    Valida i dati inseriti dall'utente, costruisce l'oggetto Feedback
    con metadati anonimi e lo appende al file feedback_log.json in
    modalità append-only. Garantisce l'anonimizzazione completa senza
    associazione a dati identificativi personali."
    
    Example:
        >>> feedback_data = {
        ...     "overall_rating": 5,
        ...     "realism_rating": 4,
        ...     "usefulness_rating": 5,
        ...     "comments": "Molto utile per l'apprendimento"
        ... }
        >>> metadata = {
        ...     "item_id": 1,
        ...     "item_title": "Circumstantiality",
        ...     "mode": "guided"
        ... }
        >>> FeedbackService.save_feedback(feedback_data, metadata)
    """
    
    FEEDBACK_FILE = "feedback_log.json"
    
    @staticmethod
    def validate_rating(rating: any, field_name: str) -> Optional[int]:
        """
        Valida un rating (1-5 o None).
        """
        if rating is None or rating == "":
            return None
        
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field_name} deve essere un numero intero, ricevuto: {type(rating).__name__}"
            )
        
        if not (1 <= rating_int <= 5):
            raise ValueError(
                f"{field_name} deve essere compreso tra 1 e 5, ricevuto: {rating_int}"
            )
        
        return rating_int
    
    @staticmethod
    def validate_comments(comments: any) -> str:
        """
        Valida e normalizza i commenti.
        """
        if comments is None:
            return ""
        
        if not isinstance(comments, str):
            comments = str(comments)
        
        return comments.strip()
    
    @staticmethod
    def create_feedback(
        overall_rating: Optional[int] = None,
        realism_rating: Optional[int] = None,
        usefulness_rating: Optional[int] = None,
        comments: str = "",
        metadata: Optional[dict] = None
    ) -> Feedback:
        """
        Crea e valida un oggetto Feedback.
        """
        validated_overall = FeedbackService.validate_rating(overall_rating, "Overall rating")
        validated_realism = FeedbackService.validate_rating(realism_rating, "Realism rating")
        validated_usefulness = FeedbackService.validate_rating(usefulness_rating, "Usefulness rating")
        validated_comments = FeedbackService.validate_comments(comments)
        
        if (validated_overall is None and 
            validated_realism is None and 
            validated_usefulness is None and 
            not validated_comments):
            raise ValueError("Il feedback deve contenere almeno una valutazione o un commento")
        
        return Feedback(
            overall_rating=validated_overall,
            realism_rating=validated_realism,
            usefulness_rating=validated_usefulness,
            comments=validated_comments,
            metadata=metadata or {}
        )
    
    @staticmethod
    def save_feedback(
        feedback_data: dict,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Salva il feedback nel file feedback_log.json.
        """
        feedback = FeedbackService.create_feedback(
            overall_rating=feedback_data.get("overall_rating"),
            realism_rating=feedback_data.get("realism_rating"),
            usefulness_rating=feedback_data.get("usefulness_rating"),
            comments=feedback_data.get("comments", ""),
            metadata=metadata
        )
        
        feedback_list = []
        feedback_path = Path(FeedbackService.FEEDBACK_FILE)
        
        if feedback_path.exists():
            try:
                with open(feedback_path, 'r', encoding='utf-8') as f:
                    feedback_list = json.load(f)
            except json.JSONDecodeError:
                feedback_list = []
        
        feedback_list.append(feedback.to_dict())
        
        try:
            with open(feedback_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_list, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            raise IOError(f"Errore nel salvataggio del feedback: {e}")
    
    @staticmethod
    def get_feedback_count() -> int:
        """
        Restituisce il numero di feedback salvati.
        """
        feedback_path = Path(FeedbackService.FEEDBACK_FILE)
        
        if not feedback_path.exists():
            return 0
        
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback_list = json.load(f)
            return len(feedback_list)
        except (json.JSONDecodeError, IOError):
            return 0
    
    @staticmethod
    def get_feedback_statistics() -> dict:
        """
        Calcola statistiche aggregate sui feedback.
        """
        feedback_path = Path(FeedbackService.FEEDBACK_FILE)
        
        if not feedback_path.exists():
            return {"count": 0, "average_ratings": {}, "by_mode": {}}
        
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback_list = json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"count": 0, "average_ratings": {}, "by_mode": {}}
        
        if not feedback_list:
            return {"count": 0, "average_ratings": {}, "by_mode": {}}
        
        overall_ratings = [f["ratings"]["overall"] for f in feedback_list if f["ratings"]["overall"] is not None]
        realism_ratings = [f["ratings"]["realism"] for f in feedback_list if f["ratings"]["realism"] is not None]
        usefulness_ratings = [f["ratings"]["usefulness"] for f in feedback_list if f["ratings"]["usefulness"] is not None]
        
        by_mode = {}
        for f in feedback_list:
            mode = f.get("metadata", {}).get("mode", "unknown")
            by_mode[mode] = by_mode.get(mode, 0) + 1
        
        return {
            "count": len(feedback_list),
            "average_ratings": {
                "overall": round(sum(overall_ratings) / len(overall_ratings), 2) if overall_ratings else None,
                "realism": round(sum(realism_ratings) / len(realism_ratings), 2) if realism_ratings else None,
                "usefulness": round(sum(usefulness_ratings) / len(usefulness_ratings), 2) if usefulness_ratings else None
            },
            "by_mode": by_mode
        }