"""
ComparisonEngine - Servizio per confronto valutazioni

Questo modulo confronta la valutazione dell'utente con il ground truth:
- Verifica correttezza identificazione item (modalità esplorativa)
- Verifica correttezza attribuzione grado
- Calcola differenza numerica tra gradi
- Assegna punteggio complessivo (0-100)
- Genera feedback testuale

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_7 del RAD
"""

from typing import Optional, Dict
from src.models.evaluation import UserEvaluation, GroundTruth, EvaluationResult


class ComparisonEngine:
    """
    Service per confronto automatico tra valutazione utente e ground truth.
    
    Responsabilità:
    - Confrontare valutazione utente con ground truth (RF_7)
    - Determinare correttezza item identificato (modalità esplorativa)
    - Determinare correttezza grado attribuito
    - Calcolare punteggio performance (0-100)
    - Generare messaggio feedback
    
    Come da RAD 2.6.1 - ComparisonEngine:
    "Esegue il confronto automatico tra valutazione utente e ground truth.
    Calcola la correttezza dell'identificazione dell'item (solo modalità
    esplorativa), la correttezza del grado attribuito, la differenza
    numerica tra grado osservato e grado effettivo e un punteggio
    complessivo di performance dell'esercitazione."
    
    Example:
        >>> result = ComparisonEngine.compare(user_eval, ground_truth)
        >>> print(f"Score: {result.score}/100")
        >>> print(f"Item corretto: {result.item_correct}")
        >>> print(f"Grado corretto: {result.grade_correct}")
    """
    
    # Pesi per il calcolo del punteggio 
    SCORE_ITEM_CORRECT = 50      # 50 punti per item corretto (esplorativa)
    SCORE_GRADE_EXACT = 50       # 50 punti per grado esatto
    SCORE_GRADE_CLOSE = 25       # 25 punti per grado vicino (±1)

    # Limiti e parametri
    MAX_GRADE = 4
    MIN_GRADE = 0
    MAX_FEEDBACK_LENGTH = 2000

    @staticmethod
    def compare(
        user_evaluation: UserEvaluation,
        ground_truth: GroundTruth
    ) -> EvaluationResult:
        """
        Confronta la valutazione utente con il ground truth.
        
        Implementa RF_7: confronto automatico con ground truth.
        
        Args:
            user_evaluation (UserEvaluation): Valutazione fornita dall'utente
            ground_truth (GroundTruth): Ground truth della simulazione
            
        Returns:
            EvaluationResult: Risultato del confronto con punteggio
            
        Example:
            >>> # Modalità guidata
            >>> user_eval = UserEvaluation(grade=3, item_id=None)
            >>> gt = GroundTruth(item_id=1, item_title="Circumstantiality", grade=2, mode="guided")
            >>> result = ComparisonEngine.compare(user_eval, gt)
            >>> print(result.grade_correct)  # False (3 vs 2)
            >>> print(result.score)  # 25 (grado vicino di 1)
        """
        # Validazioni basiche per robustezza
        if not (ComparisonEngine.MIN_GRADE <= user_evaluation.grade <= ComparisonEngine.MAX_GRADE):
            raise ValueError(f"User grade fuori range: {user_evaluation.grade}")
        if not (ComparisonEngine.MIN_GRADE <= ground_truth.grade <= ComparisonEngine.MAX_GRADE):
            raise ValueError(f"Ground truth grade fuori range: {ground_truth.grade}")

        # 1. Verifica correttezza item (solo modalità esplorativa)
        item_correct: Optional[bool] = None
        if ground_truth.is_exploratory_mode():
            # Se user_evaluation.item_id è None, è automaticamente incorretto
            item_correct = (user_evaluation.item_id == ground_truth.item_id)

        # 2. Verifica correttezza grado
        grade_correct: bool = (user_evaluation.grade == ground_truth.grade)

        # 3. Calcola differenza grado
        grade_difference: int = abs(user_evaluation.grade - ground_truth.grade)

        # 4. Calcola punteggio
        score: int = ComparisonEngine._calculate_score(
            item_correct=item_correct,
            grade_correct=grade_correct,
            grade_difference=grade_difference,
            mode=ground_truth.mode
        )

        # 5. Genera messaggio feedback
        feedback_message: str = ComparisonEngine._generate_feedback_message(
            item_correct=item_correct,
            grade_correct=grade_correct,
            grade_difference=grade_difference,
            user_grade=user_evaluation.grade,
            ground_truth_grade=ground_truth.grade,
            mode=ground_truth.mode
        )

        # 6. Troncamento feedback se troppo lungo (protezione per UI/PDF)
        if len(feedback_message) > ComparisonEngine.MAX_FEEDBACK_LENGTH:
            feedback_message = feedback_message[:ComparisonEngine.MAX_FEEDBACK_LENGTH]

        # 7. Crea oggetto EvaluationResult
        return EvaluationResult(
            item_correct=item_correct,
            grade_correct=grade_correct,
            grade_difference=grade_difference,
            score=score,
            feedback_message=feedback_message
        )
    
    @staticmethod
    def _calculate_score(
        item_correct: Optional[bool],
        grade_correct: bool,
        grade_difference: int,
        mode: str
    ) -> int:
        """
        Calcola il punteggio complessivo (0-100).
        
        Sistema di punteggio:
        - Modalità guidata: 100 punti totali per il grado
          * Grado esatto: 100 punti
          * Grado ±1: 50 punti
          * Grado ±2+: 0 punti
        
        - Modalità esplorativa: 50 punti item + 50 punti grado
          * Item corretto: 50 punti
          * Item errato: 0 punti
          * Grado esatto: +50 punti
          * Grado ±1: +25 punti
          * Grado ±2+: +0 punti
        
        Args:
            item_correct (bool|None): True se item corretto (None in guidata)
            grade_correct (bool): True se grado corretto
            grade_difference (int): Differenza assoluta tra gradi
            mode (str): "guided" o "exploratory"
            
        Returns:
            int: Punteggio 0-100
        """
        score = 0
        
        if mode == "guided":
            # Modalità guidata: solo grado conta
            if grade_correct:
                score = 100
            elif grade_difference == 1:
                score = 50
            else:  # differenza >= 2
                score = 0
        else:  # exploratory
            # Punteggio item (50 punti)
            if item_correct:
                score += ComparisonEngine.SCORE_ITEM_CORRECT

            # Punteggio grado (50 punti)
            if grade_correct:
                score += ComparisonEngine.SCORE_GRADE_EXACT
            elif grade_difference == 1:
                score += ComparisonEngine.SCORE_GRADE_CLOSE
            # Se differenza >= 2, nessun punto per il grado
        
        # Garantire 0 <= score <= 100
        return max(0, min(100, int(score)))
    
    @staticmethod
    def _generate_feedback_message(
        item_correct: Optional[bool],
        grade_correct: bool,
        grade_difference: int,
        user_grade: int,
        ground_truth_grade: int,
        mode: str
    ) -> str:
        """
        Genera un messaggio di feedback testuale per l'utente.
        
        Args:
            item_correct (bool|None): Correttezza item
            grade_correct (bool): Correttezza grado
            grade_difference (int): Differenza gradi
            user_grade (int): Grado attribuito dall'utente
            ground_truth_grade (int): Grado effettivo
            mode (str): "guided" o "exploratory"
            
        Returns:
            str: Messaggio feedback formattato
        """
        messages = []
        
        # Feedback item (solo modalità esplorativa)
        if mode == "exploratory":
            if item_correct:
                messages.append("Hai identificato correttamente l'item TALD.")
            else:
                # se item_correct è None (improbabile in exploratory), segnaliamo genericamente
                messages.append("L'item identificato non è corretto.")
        
        # Feedback grado
        if grade_correct:
            messages.append(f"Hai attribuito il grado corretto ({ground_truth_grade}/4).")
        else:
            if grade_difference == 1:
                if user_grade > ground_truth_grade:
                    messages.append(
                        f"Il grado è leggermente sovrastimato: hai attribuito {user_grade}/4, "
                        f"il grado corretto era {ground_truth_grade}/4 (differenza: 1 punto)."
                    )
                else:
                    messages.append(
                        f"Il grado è leggermente sottostimato: hai attribuito {user_grade}/4, "
                        f"il grado corretto era {ground_truth_grade}/4 (differenza: 1 punto)."
                    )
            else:  # differenza >= 2
                if user_grade > ground_truth_grade:
                    messages.append(
                        f"Il grado è significativamente sovrastimato: hai attribuito {user_grade}/4, "
                        f"il grado corretto era {ground_truth_grade}/4 (differenza: {grade_difference} punti)."
                    )
                else:
                    messages.append(
                        f"Il grado è significativamente sottostimato: hai attribuito {user_grade}/4, "
                        f"il grado corretto era {ground_truth_grade}/4 (differenza: {grade_difference} punti)."
                    )
        
        return " ".join(messages)
    
    @staticmethod
    def get_performance_category(score: int) -> str:
        """
        Determina la categoria di performance basata sul punteggio.
        
        Args:
            score (int): Punteggio 0-100
            
        Returns:
            str: Categoria ("Eccellente", "Buono", "Sufficiente", "Insufficiente")
        """
        if score >= 90:
            return "Eccellente"
        elif score >= 75:
            return "Buono"
        elif score >= 60:
            return "Sufficiente"
        else:
            return "Insufficiente"
    
    @staticmethod
    def is_passing_evaluation(score: int, threshold: int = 60) -> bool:
        """
        Verifica se la valutazione raggiunge la soglia di sufficienza.
        
        Args:
            score (int): Punteggio 0-100
            threshold (int): Soglia minima (default: 60)
            
        Returns:
            bool: True se score >= threshold
        """
        return score >= threshold
    
    @staticmethod
    def get_detailed_analysis(
        user_evaluation: UserEvaluation,
        ground_truth: GroundTruth,
        result: EvaluationResult
    ) -> Dict:
        """
        Genera un'analisi dettagliata del confronto.
        
        Utile per debugging e per statistiche avanzate.
        
        Args:
            user_evaluation (UserEvaluation): Valutazione utente
            ground_truth (GroundTruth): Ground truth
            result (EvaluationResult): Risultato confronto
            
        Returns:
            dict: Analisi dettagliata con statistiche
        """
        analysis = {
            "mode": ground_truth.mode,
            "ground_truth": {
                "item_id": ground_truth.item_id,
                "item_title": ground_truth.item_title,
                "grade": ground_truth.grade
            },
            "user_evaluation": {
                "item_id": user_evaluation.item_id,
                "grade": user_evaluation.grade,
                "has_notes": bool(user_evaluation.notes and user_evaluation.notes.strip())
            },
            "comparison": {
                "item_correct": result.item_correct,
                "grade_correct": result.grade_correct,
                "grade_difference": result.grade_difference,
                "score": result.score,
                "performance_category": ComparisonEngine.get_performance_category(result.score),
                "is_passing": ComparisonEngine.is_passing_evaluation(result.score)
            }
        }
        
        return analysis