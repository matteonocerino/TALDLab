"""
EvaluationService - Servizio per validazione valutazioni utente

Questo modulo gestisce la validazione delle valutazioni fornite dall'utente:
- Verifica completezza campi obbligatori
- Valida range valori (grade 0-4)
- Crea oggetti UserEvaluation validati
- Gestisce differenze tra modalità guidata/esplorativa

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_6 del RAD
"""

from typing import Optional, List
from src.models.evaluation import UserEvaluation
from src.models.tald_item import TALDItem


class EvaluationValidationError(Exception):
    """Eccezione per errori di validazione della valutazione utente."""
    pass


class EvaluationService:
    """
    Service per validazione delle valutazioni utente.
    
    Responsabilità:
    - Validare che i campi obbligatori siano compilati (RF_6)
    - Verificare che i valori siano nel range corretto (RF_6)
    - Costruire oggetti UserEvaluation validati
    - Gestire differenze tra modalità guidata ed esplorativa
    
    Come da RAD 2.6.1 - EvaluationService:
    "Gestisce la validazione della valutazione fornita dall'utente.
    Verifica che il grado sia compreso tra 0 e 4, che in modalità
    esplorativa sia stato selezionato un item valido e che i campi
    obbligatori siano compilati."
    
    Example:
        >>> # Modalità guidata
        >>> eval = EvaluationService.create_guided_evaluation(
        ...     grade=2,
        ...     notes="Il paziente mostrava segni chiari"
        ... )
        >>> 
        >>> # Modalità esplorativa
        >>> eval = EvaluationService.create_exploratory_evaluation(
        ...     item_id=5,
        ...     grade=3,
        ...     notes="Identificato Crosstalk"
        ... )
    """
    
    @staticmethod
    def validate_grade(grade: any) -> int:
        """
        Valida che il grado sia un valore valido (0-4).
        """
        try:
            grade_int = int(grade)
        except (TypeError, ValueError):
            raise EvaluationValidationError(
                f"Il grado deve essere un numero intero, ricevuto: {type(grade).__name__}"
            )
        
        if not (0 <= grade_int <= 4):
            raise EvaluationValidationError(
                f"Il grado deve essere compreso tra 0 e 4, ricevuto: {grade_int}"
            )
        
        return grade_int
    
    @staticmethod
    def validate_item_id(item_id: any, items: List[TALDItem]) -> int:
        """
        Valida che l'item_id sia un ID valido tra i 30 item TALD.
        """
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError):
            raise EvaluationValidationError(
                f"L'item ID deve essere un numero intero, ricevuto: {type(item_id).__name__}"
            )
        
        valid_ids = [item.id for item in items]
        
        if item_id_int not in valid_ids:
            raise EvaluationValidationError(
                f"Item ID {item_id_int} non valido. "
                f"Gli ID validi sono: {sorted(valid_ids)}"
            )
        
        return item_id_int
    
    @staticmethod
    def validate_notes(notes: any) -> str:
        """
        Valida e normalizza le note (campo opzionale).
        """
        if notes is None:
            return ""
        
        if not isinstance(notes, str):
            notes = str(notes)
        
        return notes.strip()
    
    @staticmethod
    def create_guided_evaluation(
        grade: any,
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea e valida una valutazione in modalità guidata.
        """
        validated_grade = EvaluationService.validate_grade(grade)
        validated_notes = EvaluationService.validate_notes(notes)
        
        return UserEvaluation(
            grade=validated_grade,
            item_id=None,
            notes=validated_notes
        )
    
    @staticmethod
    def create_exploratory_evaluation(
        item_id: any,
        grade: any,
        items: List[TALDItem],
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea e valida una valutazione in modalità esplorativa.
        """
        if item_id is None:
            raise EvaluationValidationError(
                "In modalità esplorativa devi selezionare un item TALD"
            )
        
        validated_item_id = EvaluationService.validate_item_id(item_id, items)
        validated_grade = EvaluationService.validate_grade(grade)
        validated_notes = EvaluationService.validate_notes(notes)
        
        return UserEvaluation(
            grade=validated_grade,
            item_id=validated_item_id,
            notes=validated_notes
        )
    
    @staticmethod
    def validate_evaluation_completeness(
        evaluation: UserEvaluation,
        mode: str
    ) -> bool:
        """
        Verifica che la valutazione sia completa per la modalità specificata.
        """
        if mode not in ["guided", "exploratory"]:
            raise ValueError(f"Modalità non valida: {mode}")
        
        if evaluation.grade is None:
            raise EvaluationValidationError("Il grado deve essere specificato")
        
        if mode == "exploratory" and evaluation.item_id is None:
            raise EvaluationValidationError(
                "In modalità esplorativa devi identificare l'item TALD"
            )
        
        if mode == "guided" and evaluation.item_id is not None:
            raise EvaluationValidationError(
                "In modalità guidata l'item_id deve essere None "
                "(l'item è già noto)"
            )
        
        return True
    
    @staticmethod
    def get_validation_errors_summary(errors: list[str]) -> str:
        """
        Genera un messaggio riepilogativo degli errori di validazione.
        """
        if not errors:
            return "Nessun errore"
        
        if len(errors) == 1:
            return f"Errore: {errors[0]}"
        
        message = "Errori riscontrati:\n"
        for i, error in enumerate(errors, 1):
            message += f"{i}. {error}\n"
        
        return message.strip()