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

from typing import Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.evaluation import UserEvaluation
from models.tald_item import TALDItem


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
        
        Args:
            grade (any): Valore da validare
            
        Returns:
            int: Grado validato
            
        Raises:
            EvaluationValidationError: Se il grado non è valido
        """
        # Verifica che sia numerico
        try:
            grade_int = int(grade)
        except (TypeError, ValueError):
            raise EvaluationValidationError(
                f"Il grado deve essere un numero intero, ricevuto: {type(grade).__name__}"
            )
        
        # Verifica range 0-4
        if not (0 <= grade_int <= 4):
            raise EvaluationValidationError(
                f"Il grado deve essere compreso tra 0 e 4, ricevuto: {grade_int}"
            )
        
        return grade_int
    
    @staticmethod
    def validate_item_id(item_id: any, items: list[TALDItem]) -> int:
        """
        Valida che l'item_id sia un ID valido tra i 30 item TALD.
        
        Args:
            item_id (any): ID da validare
            items (list[TALDItem]): Lista degli item TALD disponibili
            
        Returns:
            int: Item ID validato
            
        Raises:
            EvaluationValidationError: Se l'item_id non è valido
        """
        # Verifica che sia numerico
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError):
            raise EvaluationValidationError(
                f"L'item ID deve essere un numero intero, ricevuto: {type(item_id).__name__}"
            )
        
        # Verifica che esista nella lista
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
        
        Args:
            notes (any): Note da validare
            
        Returns:
            str: Note normalizzate (stringa vuota se None)
        """
        if notes is None:
            return ""
        
        if not isinstance(notes, str):
            # Converti in stringa se possibile
            notes = str(notes)
        
        # Normalizza (strip whitespace)
        return notes.strip()
    
    @staticmethod
    def create_guided_evaluation(
        grade: any,
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea e valida una valutazione in modalità guidata.
        
        In modalità guidata:
        - L'item è già noto (selezionato dall'utente in anticipo)
        - L'utente deve solo valutare il grado (0-4)
        - item_id rimane None
        
        Implementa RF_6 per modalità guidata.
        
        Args:
            grade (any): Grado attribuito dall'utente (0-4)
            notes (str, optional): Note opzionali
            
        Returns:
            UserEvaluation: Oggetto valutazione validato
            
        Raises:
            EvaluationValidationError: Se la validazione fallisce
            
        Example:
            >>> eval = EvaluationService.create_guided_evaluation(
            ...     grade=3,
            ...     notes="Disturbo evidente"
            ... )
            >>> print(eval.grade)
            3
            >>> print(eval.item_id)
            None
        """
        # Valida grade (obbligatorio)
        validated_grade = EvaluationService.validate_grade(grade)
        
        # Valida notes (opzionale)
        validated_notes = EvaluationService.validate_notes(notes)
        
        # Crea oggetto UserEvaluation
        # In modalità guidata, item_id è None
        return UserEvaluation(
            grade=validated_grade,
            item_id=None,
            notes=validated_notes
        )
    
    @staticmethod
    def create_exploratory_evaluation(
        item_id: any,
        grade: any,
        items: list[TALDItem],
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea e valida una valutazione in modalità esplorativa.
        
        In modalità esplorativa:
        - L'item era nascosto durante l'intervista
        - L'utente deve identificare l'item E valutare il grado
        - Entrambi i campi sono obbligatori
        
        Implementa RF_6 per modalità esplorativa.
        
        Args:
            item_id (any): ID dell'item identificato dall'utente (1-30)
            grade (any): Grado attribuito dall'utente (0-4)
            items (list[TALDItem]): Lista item TALD per validazione
            notes (str, optional): Note opzionali
            
        Returns:
            UserEvaluation: Oggetto valutazione validato
            
        Raises:
            EvaluationValidationError: Se la validazione fallisce
            
        Example:
            >>> eval = EvaluationService.create_exploratory_evaluation(
            ...     item_id=5,
            ...     grade=2,
            ...     items=tald_items,
            ...     notes="Identificato Crosstalk"
            ... )
            >>> print(eval.item_id)
            5
            >>> print(eval.grade)
            2
        """
        # Valida item_id (obbligatorio in modalità esplorativa)
        if item_id is None:
            raise EvaluationValidationError(
                "In modalità esplorativa devi selezionare un item TALD"
            )
        
        validated_item_id = EvaluationService.validate_item_id(item_id, items)
        
        # Valida grade (obbligatorio)
        validated_grade = EvaluationService.validate_grade(grade)
        
        # Valida notes (opzionale)
        validated_notes = EvaluationService.validate_notes(notes)
        
        # Crea oggetto UserEvaluation
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
        
        Args:
            evaluation (UserEvaluation): Valutazione da verificare
            mode (str): "guided" o "exploratory"
            
        Returns:
            bool: True se la valutazione è completa
            
        Raises:
            EvaluationValidationError: Se la valutazione è incompleta
        """
        # Verifica modalità valida
        if mode not in ["guided", "exploratory"]:
            raise ValueError(f"Modalità non valida: {mode}")
        
        # In entrambe le modalità, grade è obbligatorio
        if evaluation.grade is None:
            raise EvaluationValidationError("Il grado deve essere specificato")
        
        # In modalità esplorativa, anche item_id è obbligatorio
        if mode == "exploratory" and evaluation.item_id is None:
            raise EvaluationValidationError(
                "In modalità esplorativa devi identificare l'item TALD"
            )
        
        # In modalità guidata, item_id deve essere None
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
        
        Utile per mostrare all'utente cosa deve correggere.
        
        Args:
            errors (list[str]): Lista degli errori riscontrati
            
        Returns:
            str: Messaggio formattato
        """
        if not errors:
            return "Nessun errore"
        
        if len(errors) == 1:
            return f"Errore: {errors[0]}"
        
        message = "Errori riscontrati:\n"
        for i, error in enumerate(errors, 1):
            message += f"{i}. {error}\n"
        
        return message.strip()