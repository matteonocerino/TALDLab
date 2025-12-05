"""
ComparisonEngine - Servizio per confronto valutazioni

Questo modulo confronta la valutazione dell'utente con il ground truth.
In base alla modalità, esegue:
- Confronto puntuale sul grado (Modalità Guidata)
- Confronto vettoriale sull'intera scheda TALD (Modalità Esplorativa)

Calcola le metriche di accuratezza (True Positives, False Positives, False Negatives)
e assegna un punteggio percentuale (0-100) sulla performance diagnostica.

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_7 del RAD
"""

from typing import Dict, List
from src.models.evaluation import UserEvaluation, GroundTruth, EvaluationResult


class ComparisonEngine:
    """
    Service per confronto automatico tra valutazione utente e ground truth.
    
    Responsabilità:
    - Analizzare la corrispondenza tra i disturbi rilevati e quelli reali (RF_7)
    - Calcolare la matrice di confusione (TP, FP, FN) in modalità esplorativa
    - Valutare la precisione dei gradi di severità assegnati
    - Calcolare un punteggio normalizzato (0-100)
    - Generare feedback testuali dettagliati per l'utente
    
    Come da RAD 2.6.1 - ComparisonEngine:
    "Esegue il confronto vettoriale tra la scheda di valutazione compilata
    dall'utente (30 valori) e il ground truth. Calcola la matrice di confusione
    per identificare disturbi correttamente diagnosticati, omessi e sovrastimati."
    """
    
    # Costanti per il calcolo del punteggio
    MAX_GRADE = 4
    MIN_GRADE = 0
    MAX_FEEDBACK_LENGTH = 3000

    @staticmethod
    def compare(
        user_evaluation: UserEvaluation,
        ground_truth: GroundTruth
    ) -> EvaluationResult:
        """
        Esegue il confronto tra valutazione e verità clinica.
        Dispatcha la logica corretta in base alla modalità della sessione.
        
        Args:
            user_evaluation (UserEvaluation): Input dell'utente.
            ground_truth (GroundTruth): Configurazione della simulazione.
            
        Returns:
            EvaluationResult: Oggetto contenente metriche, punteggi e feedback.
        """
        if ground_truth.is_guided_mode():
            return ComparisonEngine._compare_guided(user_evaluation, ground_truth)
        else:
            return ComparisonEngine._compare_exploratory(user_evaluation, ground_truth)

    # =========================================================================
    # LOGICA MODALITÀ GUIDATA (1 vs 1)
    # =========================================================================

    @staticmethod
    def _compare_guided(user_eval: UserEvaluation, gt: GroundTruth) -> EvaluationResult:
        """
        Confronto semplificato per la modalità guidata.
        Si concentra sulla correttezza del grado per l'unico item oggetto di studio.
        """
        # Identifica l'item target (l'unico attivo nel GT in modalità guidata)
        target_item_id, gt_grade = gt.get_primary_item()
        
        # Recupera il voto dell'utente per quell'item
        user_grade = user_eval.get_grade_for_item(target_item_id)
        
        # Calcolo differenza
        grade_diff = abs(user_grade - gt_grade)
        grade_correct = (grade_diff == 0)
        
        # Scoring Guidato: 
        # 100 punti = esatto
        # 50 punti = errore di 1 grado (accettabile in training)
        # 0 punti = errore > 1
        score = 0
        if grade_correct:
            score = 100
        elif grade_diff == 1:
            score = 50
        
        # Generazione Feedback
        feedback = ComparisonEngine._generate_guided_feedback(
            gt_grade, user_grade, grade_diff
        )
        
        return EvaluationResult(
            true_positives=[target_item_id] if grade_correct else [],
            grade_diffs={target_item_id: grade_diff},
            score=score,
            feedback_message=feedback
        )

    # =========================================================================
    # LOGICA MODALITÀ ESPLORATIVA (N vs M - Vettoriale)
    # =========================================================================

    @staticmethod
    def _compare_exploratory(user_eval: UserEvaluation, gt: GroundTruth) -> EvaluationResult:
        """
        Confronto vettoriale completo per la modalità esplorativa (Assessment).
        Gestisce casi di comorbilità (più item) e paziente sano (0 item).
        
        Algoritmo:
        1. Estrae i set di item rilevati (User) vs reali (GT) con grado > 0.
        2. Calcola intersezioni e differenze (TP, FP, FN).
        3. Per i True Positives, calcola la precisione del grado.
        4. Compone un punteggio ponderato (50% Identificazione, 50% Precisione Grado).
        """
        
        # 1. Estrazione Item Attivi (Grado > 0)
        # GT: Quali disturbi ha VERAMENTE il paziente?
        gt_active_ids = {i_id for i_id, gr in gt.active_items.items() if gr > 0}
        
        # USER: Quali disturbi ha SEGNALATO l'utente?
        user_active_ids = {i_id for i_id, gr in user_eval.evaluation_sheet.items() if gr > 0}
        
        # 2. Calcolo Matrice di Confusione (Set Operations)
        true_positives = list(gt_active_ids.intersection(user_active_ids))  # Corretti
        false_positives = list(user_active_ids - gt_active_ids)             # Inventati (Allucinazioni)
        false_negatives = list(gt_active_ids - user_active_ids)             # Persi (Omissioni)
        
        # 3. Analisi Differenze Gradi (Solo per i True Positives)
        grade_diffs = {}
        total_grade_penalty = 0
        
        for item_id in true_positives:
            u_g = user_eval.get_grade_for_item(item_id)
            g_g = gt.active_items.get(item_id, 0)
            diff = abs(u_g - g_g)
            grade_diffs[item_id] = diff
            
            # Penalità: diff 0 -> 0, diff 1 -> 0.5, diff >=2 -> 1.0 (max penalty)
            if diff == 1:
                total_grade_penalty += 0.5
            elif diff >= 2:
                total_grade_penalty += 1.0

        # 4. Calcolo Punteggio 
        score = ComparisonEngine._calculate_exploratory_score(
            tp_count=len(true_positives),
            fp_count=len(false_positives),
            fn_count=len(false_negatives),
            gt_count=len(gt_active_ids),
            grade_penalty=total_grade_penalty
        )
        
        # 5. Generazione Feedback Testuale
        feedback = ComparisonEngine._generate_exploratory_feedback(
            true_positives, false_positives, false_negatives, 
            grade_diffs, gt, user_eval
        )
        
        return EvaluationResult(
            true_positives=sorted(true_positives),
            false_positives=sorted(false_positives),
            false_negatives=sorted(false_negatives),
            grade_diffs=grade_diffs,
            score=score,
            feedback_message=feedback
        )

    @staticmethod
    def _calculate_exploratory_score(
        tp_count: int, fp_count: int, fn_count: int, 
        gt_count: int, grade_penalty: float
    ) -> int:
        """
        Calcola il punteggio 0-100 per la modalità esplorativa usando un sistema a penalità.
        
        Logica Didattica:
        - Si parte da 100 (Credito pieno).
        - Si sottraggono punti per ogni errore commesso.
        - Questo approccio è più equo per i casi "Paziente Sano" e più comprensibile.
        
        Pesi Penalità:
        - FN (Omissione): -15 punti (Grave: non vedere un sintomo).
        - FP (Falso Positivo): -10 punti (Medio: inventare un sintomo).
        - Errore Grado: gestito tramite grade_penalty (che accumula 0.5 per lievi, 1.0 per gravi).
          Qui convertiamo quel valore in punti reali (es. 1.0 penalty = -5 punti).
        """
        
        current_score = 100.0
        
        # 1. Penalità per Errori di Identificazione
        PENALTY_OMISSION = 15.0  # Mancato
        PENALTY_FALSE_ALARM = 10.0 # Inventato
        
        current_score -= (fn_count * PENALTY_OMISSION)
        current_score -= (fp_count * PENALTY_FALSE_ALARM)
        
        # 2. Penalità per Precisione Grado (sui True Positives)
        # grade_penalty arriva dal metodo chiamante con valori:
        # 0.5 per diff=1, 1.0 per diff>=2
        # Moltiplichiamo per un fattore scalare per convertirlo in punti voto.
        # Es: diff=1 (0.5) -> -2.5 punti | diff=2 (1.0) -> -5 punti
        SCORE_SCALING_FACTOR = 5.0 
        
        current_score -= (grade_penalty * SCORE_SCALING_FACTOR)
        
        # 3. Normalizzazione (0-100)
        final_score = int(max(0, min(100, current_score)))
        
        return final_score

    # =========================================================================
    # GENERAZIONE FEEDBACK TESTUALI
    # =========================================================================

    @staticmethod
    def _generate_guided_feedback(gt_grade: int, user_grade: int, diff: int) -> str:
        """Genera il testo per la modalità guidata."""
        if diff == 0:
            return f"✅ Eccellente. Hai individuato correttamente il grado di severità ({gt_grade}/4)."
        elif diff == 1:
            direction = "sottostimato" if user_grade < gt_grade else "sovrastimato"
            return (f"⚠️ Buona approssimazione. Hai leggermente {direction} il disturbo "
                    f"(Tuo: {user_grade}, Reale: {gt_grade}). La differenza è minima.")
        else:
            direction = "sottostimato" if user_grade < gt_grade else "sovrastimato"
            return (f"❌ Errore significativo. Hai {direction} marcatamente la severità "
                    f"(Tuo: {user_grade}, Reale: {gt_grade}). Rivedi i criteri diagnostici.")

    @staticmethod
    def _generate_exploratory_feedback(
        tp: List[int], fp: List[int], fn: List[int], 
        diffs: Dict[int, int], gt: GroundTruth, user: UserEvaluation
    ) -> str:
        """Genera il testo dettagliato per la modalità esplorativa."""
        blocks = []
        
        # 1. Analisi Identificazione
        if not fp and not fn and tp:
            blocks.append("✅ **Diagnosi Perfetta:** Hai identificato esattamente tutti i disturbi presenti.")
        elif not fp and not fn and not tp:
            # Caso paziente sano corretto
            blocks.append("✅ **Diagnosi Perfetta:** Hai correttamente rilevato l'assenza di disturbi (Paziente Sano).")
        else:
            # Errori misti
            if tp:
                blocks.append(f"✅ Hai individuato correttamente {len(tp)} disturbo/i.")
            if fn:
                blocks.append(f"❌ **Omissioni:** Hai mancato {len(fn)} disturbo/i presenti nel quadro clinico.")
            if fp:
                blocks.append(f"⚠️ **Falsi Positivi:** Hai segnalato {len(fp)} disturbo/i non presenti nel ground truth.")

        blocks.append("\n") 

        # 2. Dettaglio Gradi (solo per TP)
        if tp:
            blocks.append("**Analisi della severità (Gradi):**")
            for item_id in tp:
                u_g = user.get_grade_for_item(item_id)
                g_g = gt.active_items[item_id]
                d = diffs[item_id]
                
                # Lavoriamo con gli ID per disaccoppiamento.
                if d == 0:
                    blocks.append(f"- Item {item_id}: Grado corretto ({u_g}/4).")
                elif d == 1:
                    blocks.append(f"- Item {item_id}: Impreciso (Tuo: {u_g}, Reale: {g_g}).")
                else:
                    blocks.append(f"- Item {item_id}: Errato (Tuo: {u_g}, Reale: {g_g}).")

        # 3. Dettaglio Errori (se presenti)
        if fn or fp:
            blocks.append("\n**Dettaglio Discrepanze:**")
            if fn:
                for iid in fn:
                    g_g = gt.active_items[iid]
                    blocks.append(f"- Item {iid} era PRESENTE (Grado {g_g}) ma non l'hai segnalato.")
            if fp:
                for iid in fp:
                    u_g = user.get_grade_for_item(iid)
                    blocks.append(f"- Item {iid} era ASSENTE (Grado 0) ma hai assegnato Grado {u_g}.")

        return "\n".join(blocks)