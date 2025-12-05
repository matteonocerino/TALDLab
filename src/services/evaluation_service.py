"""
EvaluationService - Servizio per validazione valutazioni utente

Questo modulo gestisce la validazione delle valutazioni fornite dall'utente
prima che vengano elaborate dal sistema.

Funzionalità principali:
- Validazione formale dei dati (tipi, range 0-4)
- Validazione strutturale (completezza campi obbligatori)
- Costruzione di oggetti UserEvaluation validati
- Gestione della logica differenziata per modalità Guidata (singolo item)
  ed Esplorativa (scheda completa/vettoriale).

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_6 del RAD ("Valutazione finale")
"""

from typing import Optional, List, Dict
from src.models.evaluation import UserEvaluation
from src.models.tald_item import TALDItem


class EvaluationValidationError(Exception):
    """
    Eccezione specifica per errori di validazione nel form di valutazione.
    Viene catturata dall'interfaccia (Boundary) per mostrare messaggi user-friendly.
    """
    pass


class EvaluationService:
    """
    Service (Control) per la validazione e creazione delle valutazioni utente.
    
    Responsabilità:
    - Garantire che i dati immessi dall'utente rispettino i vincoli del dominio TALD (RF_6).
    - Costruire istanze di UserEvaluation coerenti con il Modello Dati aggiornato.
    - Prevenire l'invio di schede incomplete o con valori fuori range.
    
    Come da RAD 2.6.1 - EvaluationService:
    "Gestisce la validazione della valutazione fornita dall'utente. [...]
    Costruisce l'oggetto UserEvaluation dai dati del form e previene l'invio
    di valutazioni incomplete o formalmente errate."
    """
    
    @staticmethod
    def validate_grade(grade: any, item_context: str = "") -> int:
        """
        Valida che un singolo grado sia un intero valido nel range 0-4.
        
        Args:
            grade: Il valore da validare (può arrivare come str o int dalla UI).
            item_context: Stringa opzionale per migliorare il messaggio di errore (es. "Item 5").
            
        Returns:
            int: Il grado validato come intero.
            
        Raises:
            EvaluationValidationError: Se il grado non è valido.
        """
        try:
            grade_int = int(grade)
        except (TypeError, ValueError):
            msg = f"Il grado deve essere un numero intero"
            if item_context: msg += f" per {item_context}"
            raise EvaluationValidationError(msg)
        
        if not (0 <= grade_int <= 4):
            msg = f"Il grado deve essere compreso tra 0 e 4"
            if item_context: msg += f" per {item_context}"
            msg += f" (ricevuto: {grade_int})"
            raise EvaluationValidationError(msg)
        
        return grade_int
    
    @staticmethod
    def validate_evaluation_sheet(sheet: Dict[int, int], valid_item_ids: List[int]) -> Dict[int, int]:
        """
        Valida l'intera scheda di valutazione (Dizionario {id: grado}).
        
        Utilizzato principalmente in modalità Esplorativa per garantire che
        tutti gli item votati esistano e abbiano gradi validi.
        
        Args:
            sheet: Dizionario {item_id: grado}.
            valid_item_ids: Lista degli ID validi caricati dal sistema.
            
        Returns:
            Dict[int, int]: La scheda validata e pulita.
        """
        if not isinstance(sheet, dict):
            raise EvaluationValidationError("Formato scheda di valutazione non valido (atteso dizionario).")
            
        validated_sheet = {}
        
        for item_id, grade in sheet.items():
            # 1. Validazione ID Item
            if item_id not in valid_item_ids:
                raise EvaluationValidationError(f"Item ID {item_id} non riconosciuto nel sistema.")
            
            # 2. Validazione Grado
            # Ignoriamo i gradi None o vuoti (vengono trattati come 0/assenti)
            if grade is not None:
                val_grade = EvaluationService.validate_grade(grade, item_context=f"Item {item_id}")
                # Salviamo solo se > 0 per ottimizzare (sparse dict), oppure teniamo anche gli 0 se espliciti
                validated_sheet[item_id] = val_grade
                
        return validated_sheet
    
    @staticmethod
    def validate_notes(notes: any) -> str:
        """
        Valida e normalizza il campo note (opzionale).
        Taglia eventuali spazi bianchi eccessivi.
        """
        if notes is None:
            return ""
        
        if not isinstance(notes, str):
            notes = str(notes)
        
        clean_notes = notes.strip()
        
        # Controllo lunghezza (coerente con il Model)
        if len(clean_notes) > 5000:
            raise EvaluationValidationError("Le note sono troppo lunghe (max 5000 caratteri).")
            
        return clean_notes
    
    @staticmethod
    def create_guided_evaluation(
        target_item_id: int,
        grade: any,
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea una valutazione per la Modalità Guidata.
        
        In questa modalità, l'utente valuta UN SOLO item specifico.
        Il servizio converte questo singolo input nel formato vettoriale
        standard richiesto dal nuovo modello UserEvaluation.
        
        Args:
            target_item_id (int): L'ID dell'item su cui ci si sta esercitando.
            grade (any): Il voto assegnato (0-4).
            notes (str): Note opzionali.
            
        Returns:
            UserEvaluation: Oggetto entity pronto per il salvataggio.
        """
        # Validazione input puntuale
        val_grade = EvaluationService.validate_grade(grade)
        val_notes = EvaluationService.validate_notes(notes)
        
        # Costruzione del vettore (un solo item valorizzato)
        evaluation_sheet = {target_item_id: val_grade}
        
        return UserEvaluation(
            evaluation_sheet=evaluation_sheet,
            notes=val_notes
        )
    
    @staticmethod
    def create_exploratory_evaluation(
        evaluation_sheet: Dict[int, int],
        all_items: List[TALDItem],
        notes: Optional[str] = None
    ) -> UserEvaluation:
        """
        Crea una valutazione per la Modalità Esplorativa.
        
        Qui l'utente compila una scheda complessa. Il servizio valida
        l'intera mappa dei voti.
        
        Args:
            evaluation_sheet (Dict): Mappa {item_id: grado} proveniente dalla UI.
            all_items (List[TALDItem]): Lista item di riferimento per validare gli ID.
            notes (str): Note opzionali.
            
        Returns:
            UserEvaluation: Oggetto entity validato.
        """
        # Estrazione ID validi per controllo incrociato
        valid_ids = [item.id for item in all_items]
        
        # Validazione massiva della scheda
        val_sheet = EvaluationService.validate_evaluation_sheet(evaluation_sheet, valid_ids)
        val_notes = EvaluationService.validate_notes(notes)
        
        # Check specifico per Esplorativa:
        # È tecnicamente possibile inviare una scheda vuota (nessun disturbo rilevato -> Paziente Sano),
        # quindi non solleviamo eccezione se sheet è vuoto.
        
        return UserEvaluation(
            evaluation_sheet=val_sheet,
            notes=val_notes
        )
    
    @staticmethod
    def get_validation_errors_summary(errors: list[str]) -> str:
        """
        Utility per formattare una lista di errori in un messaggio leggibile per la UI.
        """
        if not errors:
            return "Nessun errore"
        
        if len(errors) == 1:
            return f"Errore: {errors[0]}"
        
        message = "Si sono verificati i seguenti errori:\n"
        for i, error in enumerate(errors, 1):
            message += f"{i}. {error}\n"
        
        return message.strip()