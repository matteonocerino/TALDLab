"""
LLMService - Servizio per integrazione Google Gemini API

Questo modulo gestisce l'interfaccia con Google Gemini API per:
- Simulare pazienti virtuali con profili clinici complessi (comorbilità)
- Generare risposte clinicamente coerenti per uno o più disturbi simultanei
- Produrre spiegazioni cliniche analitiche per i report
- Gestire timeout ed errori di connessione

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_3, RF_4, RF_11 del RAD
"""

import random
import threading
import socket
from typing import Dict, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded
from src.models.evaluation import GroundTruth
from src.models.tald_item import TALDItem
from src.models.conversation import ConversationHistory


class LLMTimeoutError(Exception):
    """Eccezione specifica per timeout nelle chiamate LLM."""
    pass


class LLMConnectionError(Exception):
    """Eccezione specifica per errori di connessione all'API."""
    pass


class LLMService:
    """
    Service per gestione delle interazioni con Google Gemini API.
    
    Responsabilità:
    - Configurare e inizializzare Gemini API (RF_12)
    - Costruire prompt di sistema complessi che supportano la comorbilità (RF_3)
    - Generare risposte coerenti combinando più disturbi TALD
    - Gestire il caso "Paziente Sano" (Grado 0)
    - Gestire robustamente errori di rete e timeout (RF_11)
    """
    
    # Timeout calibrato per Gemini Flash Lite (bilanciamento velocità/stabilità)
    REQUEST_TIMEOUT = 15  # secondi
    
    def __init__(self, config: Dict[str, any]):
        """
        Inizializza il servizio LLM con la configurazione fornita.
        
        Args:
            config (dict): Configurazione (api_key, model, temperature, max_tokens).
            
        Raises:
            ValueError: Se l'API key è assente.
            LLMConnectionError: Se la configurazione fallisce.
        """
        self.config = config
        self.timeout = self.REQUEST_TIMEOUT
        
        if not config.get('api_key'):
            raise ValueError(
                "API key non presente nella configurazione. "
                "Impossibile inizializzare LLMService."
            )
        
        try:
            genai.configure(api_key=config['api_key'])
            
            # Impostazioni di sicurezza permissive per consentire simulazioni cliniche
            # (es. deliri o linguaggio disorganizzato potrebbero essere flammati altrimenti)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            self.model = genai.GenerativeModel(
                model_name=config['model'],
                safety_settings=safety_settings
            )
            
        except Exception as e:
            raise LLMConnectionError(f"Errore nella configurazione di Gemini API: {e}")
    
    def _check_connectivity(self):
        """
        Esegue un test rapido di connettività (ping a Google DNS).
        Evita di attendere il timeout completo (14s) se manca la rete.
        """
        try:
            # Connessione rapida (2s) a un DNS affidabile
            socket.create_connection(("8.8.8.8", 53), timeout=2)
        except OSError:
            raise LLMConnectionError("Nessuna connessione internet rilevata.")
        
    def _generate_patient_background(self) -> str:
        """
        Genera un background anagrafico casuale per il paziente virtuale.
        Serve a dare coerenza "umana" oltre ai sintomi clinici.
        """
        nomi_m = ["Marco", "Luca", "Giuseppe", "Andrea", "Matteo", "Alessandro", 
                  "Davide", "Stefano", "Paolo", "Riccardo"]
        nomi_f = ["Laura", "Sofia", "Francesca", "Chiara", "Giulia", "Elena", 
                  "Sara", "Valentina", "Martina", "Alessia"]
        
        genere = random.choice(["M", "F"])
        nome = random.choice(nomi_m if genere == "M" else nomi_f)
        eta = random.randint(25, 55)
        
        lavori = [
            "impiegato in un'azienda", "insegnante di scuola media",
            "tecnico informatico", "cameriere in un ristorante",
            "commesso in un negozio", "operaio", "segretaria", "cuoco",
            "meccanico", "studente universitario", "impiegato comunale",
            "addetto alle vendite", "receptionist"
        ]
        
        lavoro = random.choice(lavori)
        return f"Ti chiami {nome}, hai {eta} anni, lavori come {lavoro}."
    
    def _get_awareness_instructions(self, tald_item: TALDItem) -> str:
        """
        Genera istruzioni sulla consapevolezza del disturbo.
        Differenzia tra disturbi oggettivi (paziente inconsapevole) e 
        soggettivi (paziente consapevole ma riporta solo se interrogato).
        """
        if tald_item.is_objective():
            return f"""**CONSAPEVOLEZZA (Oggettivo):**
- NON sei consapevole di avere il disturbo '{tald_item.title}'.
- Il disturbo emerge spontaneamente nel tuo modo di parlare.
- Se ti viene fatto notare, reagisci con genuina confusione ("Non capisco cosa intende...", "Davvero?").
- Non negare in modo difensivo, semplicemente non capisci di cosa si parla."""
        else:
            return f"""**CONSAPEVOLEZZA (Soggettivo):**
- SEI consapevole del disturbo '{tald_item.title}' e del disagio che provoca.
- NON parlarne spontaneamente; descrivilo SOLO se l'intervistatore ti chiede come ti senti o se hai difficoltà.
- Quando richiesto, descrivi le tue esperienze interne e il disagio.
- NON usare MAI il nome tecnico '{tald_item.title}'."""

    def _get_grade_instructions(self, grade: int, item_title: str) -> str:
        """
        Genera istruzioni specifiche per modulare l'intensità del disturbo.
        Include la logica speciale per GRADO 0 (Paziente Sano).
        """
        if grade == 0:
            return f"""**INTENSITÀ: GRADO 0 (ASSENTE)**
            ATTENZIONE: Il disturbo '{item_title}' è descritto sopra ma è **ASSENTE** in questo paziente.
            NON manifestare nessuno dei sintomi elencati per questo item.
            Il tuo comportamento verbale deve essere normale rispetto a questo specifico tratto."""
            
        elif grade == 1:
            return f"**INTENSITÀ: GRADO 1 (DUBBIO/MINIMO)**. Il fenomeno '{item_title}' è appena percepibile. Manifestalo RARAMENTE (1-2 volte) e in modo molto sottile."
            
        elif grade == 2:
            return f"**INTENSITÀ: GRADO 2 (LIEVE)**. Il fenomeno '{item_title}' è presente ma non compromette la comunicazione. Manifestalo alcune volte."
            
        elif grade == 3:
            return f"**INTENSITÀ: GRADO 3 (MODERATO)**. Il fenomeno '{item_title}' è evidente e frequente. L'intervistatore deve notarlo chiaramente."
            
        else:  # grade 4
            return f"**INTENSITÀ: GRADO 4 (SEVERO)**. Il fenomeno '{item_title}' DOMINA la conversazione e la rende difficile. Manifestalo quasi costantemente."

    def _get_item_specific_instructions(self, tald_item: TALDItem) -> str:
        """
        Genera istruzioni specifiche per item che richiedono comportamenti particolari
        (es. pause, interruzioni, prolissità).
        """
        instructions = []
        
        # Regole per pause e rallentamenti
        if tald_item.title in ["Slowed Thinking", "Rupture of Thought", "Blocking"]:
            instructions.append(
                "- Usa '...' o '(pausa)' per indicare pause significative nel discorso, "
                "coerenti con il disturbo simulato."
            )
        
        # Regole per verbosità
        if tald_item.title in ["Logorrhoea", "Pressured Speech", "Circumstantiality", "Poverty of Content of Speech"]:
            instructions.append( 
                "- Le tue risposte sono più elaborate del normale, ma SEMPRE entro 100-150 parole MAX.\n"
                "- La prolissità si manifesta con: digressioni, dettagli irrilevanti, difficoltà a concludere.\n"
                "- NON con lunghezza eccessiva: il disturbo è nella STRUTTURA, non nella quantità."
            )
        
        # Regole per brevità
        if tald_item.title == "Poverty of Speech":
            instructions.append(
                "- Le tue risposte devono essere SEMPRE molto brevi, concrete, "
                "monosillabiche quando possibile. Non elaborare mai spontaneamente."
            )
        
        # Regole specifiche per item particolari
        if tald_item.title == "Echolalia":
            instructions.append("- Ripeti parole o frasi dell'intervistatore prima di (eventualmente) rispondere.")
        
        if tald_item.title == "Verbigeration":
            instructions.append("- Ripeti singole parole più volte all'interno delle tue frasi.")
        
        if tald_item.title == "Perseveration":
            instructions.append("- Torna ripetutamente a idee o frasi menzionate in precedenza, anche se non pertinenti.")
        
        if tald_item.title == "Restricted Thinking":
            instructions.append("- Riporta ogni argomento al tuo tema fisso, anche quando l'intervistatore propone altro.")
        
        if tald_item.title == "Crosstalk":
            instructions.append(
                "- Rispondi 'a lato' della domanda: capisci cosa ti viene chiesto "
                "ma la tua risposta non centra il punto, pur essendo grammaticalmente corretta."
            )
        
        if instructions:
            return "\n**Comportamenti Obbligatori:**\n" + "\n".join(instructions)
        return ""

    def _build_system_prompt(
        self, 
        active_items: Dict[int, int], 
        all_items_map: Dict[int, TALDItem]
    ) -> str:
        """
        Costruisce il "System Prompt" completo per il simulatore.
        
        Supporta la COMORBILITÀ (RF_3): itera su tutti gli item attivi
        e combina le istruzioni in un unico profilo coerente.
        
        Args:
            active_items (Dict[int, int]): Mappa {item_id: grado}.
            all_items_map (Dict[int, TALDItem]): Lookup per recuperare i dettagli degli item.
            
        Returns:
            str: Il prompt testuale completo da inviare a Gemini.
        """
        background = self._generate_patient_background()
        
        # Costruzione sezioni cliniche
        clinical_profile = ""
        has_severe_symptoms = False
        
        # Ordiniamo per grado decrescente (i disturbi più gravi hanno priorità)
        sorted_items = sorted(active_items.items(), key=lambda x: x[1], reverse=True)
        
        for item_id, grade in sorted_items:
            item = all_items_map.get(item_id)
            if item:
                # Recupera la descrizione del grado dal JSON dell'item per massima precisione
                try:
                    grade_desc_json = item.get_grade_description(grade)
                except:
                    grade_desc_json = "Vedi criteri generali"

                # Costruzione blocco item
                item_block = f"""
### DISTURBO ATTIVO: {item.title} ({item.type.upper()})
- **Descrizione:** {item.description}
- **Criteri:** {item.criteria}
- **Esempio:** {item.example}

{self._get_grade_instructions(grade, item.title)}
**Descrizione specifica Grado {grade}:** {grade_desc_json}

{self._get_awareness_instructions(item)}
{self._get_item_specific_instructions(item)}
"""
                clinical_profile += item_block
                if grade >= 3:
                    has_severe_symptoms = True
        
        # Gestione caso "Paziente Sano" (tutti gli item a 0 o lista vuota)
        is_healthy = not any(g > 0 for g in active_items.values())
        
        if is_healthy:
            clinical_instructions = """
## PROFILO CLINICO: PAZIENTE ASINTOMATICO
In questa simulazione NON devi manifestare alcun disturbo psicopatologico rilevante.
Il tuo eloquio, il pensiero e la comprensione sono nella norma.
Rispondi alle domande in modo coerente, fluido e naturale.
Sei un paziente collaborativo ma senza segni di TALD.
"""
        else:
            clinical_instructions = f"""
## PROFILO CLINICO (COMORBILITÀ)
Il paziente manifesta i seguenti fenomeni simultaneamente. 
Devi integrare queste istruzioni nel tuo comportamento verbale in modo coerente.
{clinical_profile}
"""

        length_control = """
# CONTROLLO LUNGHEZZA RISPOSTE (PRIORITÀ MASSIMA)

LIMITI ASSOLUTI per TUTTE le risposte:
- Domande semplici/chiuse: MAX 30-50 parole (2-3 frasi)
- Domande aperte standard: MAX 80-100 parole (5-6 frasi)
- Domande molto complesse: MAX 150 parole (assoluto limite massimo)

IMPORTANTE: Se stai per superare il limite, FERMATI anche a metà frase.
I pazienti reali si interrompono, perdono il filo, vengono interrotti dall'intervistatore.
La simulazione deve essere INTERATTIVA, non un monologo.
"""

        # Prompt finale assemblato con tutte le regole di interazione
        prompt = f"""# RUOLO: PAZIENTE VIRTUALE (Simulazione Psichiatrica)
{background}
Stai partecipando a un colloquio clinico. L'intervistatore è un medico/psicologo.

{clinical_instructions}

{length_control}

---

# REGOLE COMPORTAMENTALI FONDAMENTALI

1. **Sei un paziente, non un medico.** - NON accogliere l'intervistatore.
   - NON fare domande di cortesia ("Come sta?", "Come posso aiutarla?").
   - NON dare istruzioni o guidare la conversazione.
   - NON iniziare argomenti di conversazione.
   - Usa sempre "dottore" (mai "dottoressa").  

2. **Quando manifestare il disturbo:**

   **RISPOSTE NORMALI (senza disturbo):**
   - Saluti semplici: "Buongiorno" / "Salve"
   - Dati anagrafici diretti: nome, età, provenienza
   - Risposte sì/no semplici quando appropriate
   
   **MANIFESTA IL DISTURBO:**
   - Domande su esperienze, emozioni, pensieri ("Come si sente?", "Cosa prova?")
   - Domande che richiedono elaborazione ("Mi parli di...", "Cosa fa nella vita?", "Com'è la sua giornata?")
   - Domande aperte su famiglia, lavoro, relazioni
   - Qualsiasi risposta che richieda più di una frase semplice

3. **Esempi pratici di interazione:**
   
   **Domande anagrafiche (risposta NORMALE):**
   - "Come si chiama?" → "Marco" / "Mi chiamo Marco"
   - "Quanti anni ha?" → "35 anni" / "Ho 35 anni"
   - "Di dove è?" → "Sono di Napoli"
   
   **Domande che richiedono elaborazione (MANIFESTA DISTURBO):**
   - "Che lavoro fa?" → [risposta con disturbo attivato]
   - "Mi parli della sua famiglia" → [risposta con disturbo attivato]
   - "Come sta?" → [risposta con disturbo attivato]
   - "Com'è andata la giornata?" → [risposta con disturbo attivato]

4. **Coerenza.** Mantieni i sintomi costanti per tutta la durata dell'intervista. Non guarire improvvisamente.

5. **Linguaggio naturale.**
   - Tono formale ma non rigido.
   - Niente formulazioni cliniche o metalinguaggio.
   - Non menzionare MAI il nome tecnico dei disturbi.

{"**NOTA:** Visti i disturbi severi presenti, la comunicazione può risultare molto difficile o frammentata." if has_severe_symptoms else ""}

---

# INIZIO SIMULAZIONE
Da questo momento rispondi SOLO quando interrogato, come il paziente descritto.
Attendi la prima domanda dell'intervistatore.
"""
        return prompt
    
    def start_chat_session(
        self, 
        active_items: Dict[int, int], 
        all_tald_items: List[TALDItem]
    ) -> genai.ChatSession:
        """
        Avvia una nuova sessione di chat configurata.
        
        Adattato per supportare la logica multi-item (RF_3).
        
        Args:
            active_items (Dict[int, int]): Configurazione disturbi {id: grado}.
            all_tald_items (List[TALDItem]): Lista completa item (per lookup).
            
        Returns:
            genai.ChatSession: Oggetto sessione pronto all'uso.
        """
        # Crea mappa per lookup veloce
        items_map = {item.id: item for item in all_tald_items}
        
        system_prompt = self._build_system_prompt(active_items, items_map)
        
        # Inizializza la chat con il prompt di sistema nel contesto
        chat_session = self.model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ["Ho capito il mio ruolo. Sono pronto."]}
        ])
        return chat_session
    
    def generate_response(self, chat_session: genai.ChatSession, user_message: str) -> str:
        """
        Genera una risposta dal paziente virtuale.
        Gestisce errori di rete e timeout (RF_11).
        """
        # 1. Controllo preventivo connettività
        self._check_connectivity()

        # 2. Esecuzione richiesta in thread separato per gestire timeout client-side
        response_container = {"text": None, "error": None}

        def call_model():
            try:
                response = chat_session.send_message(
                    user_message,
                    request_options={'timeout': self.timeout}
                )
                if response and getattr(response, "text", None):
                    response_container["text"] = response.text.strip()
                else:
                    response_container["error"] = LLMTimeoutError("Risposta vuota dall'API.")
            except Exception as e:
                response_container["error"] = e

        thread = threading.Thread(target=call_model, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout + 5.0) # Margine di sicurezza

        if thread.is_alive():
            raise LLMTimeoutError("Timeout: il paziente virtuale non ha risposto in tempo.")

        if response_container["error"]:
            e = response_container["error"]
            error_str = str(e).lower()

            if isinstance(e, DeadlineExceeded) or "deadline" in error_str:
                raise LLMTimeoutError("Timeout interno di Gemini.")

            if any(k in error_str for k in ["connection", "network", "socket", "failed to connect"]):
                 raise LLMConnectionError(f"Connessione fallita: {e}")

            if isinstance(e, ResourceExhausted):
                raise LLMConnectionError("Limite risorse/quota API esaurito.")

            raise LLMConnectionError(f"Errore generico Gemini: {e}")

        if not response_container["text"]:
            raise LLMTimeoutError("Nessun testo generato.")

        return response_container["text"] 

    def generate_clinical_explanation(
        self,
        ground_truth: GroundTruth,
        all_tald_items: List[TALDItem],
        conversation_history: ConversationHistory
    ) -> str:
        """
        Genera l'analisi clinica finale ("Justification").
        Gestisce sia item singoli (Guidata) che profili complessi/sani (Esplorativa).
        """
        self._check_connectivity()
        
        transcript = conversation_history.to_text_transcript()
        
        # 1. COSTRUZIONE DEL CONTESTO CLINICO (Ground Truth)
        active_items_data = []
        target_title_guided = None
        
        if ground_truth.active_items:
            for item_id, grade in ground_truth.active_items.items():
                # In GUIDATA: includiamo l'item anche se è 0 (perché è il focus dell'esercizio)
                # In ESPLORATIVA: includiamo solo i disturbi presenti (>0)
                if ground_truth.is_guided_mode() or grade > 0:
                    item_obj = next((i for i in all_tald_items if i.id == item_id), None)
                    if item_obj:
                        active_items_data.append(f"- {item_obj.title}: {grade}/4 (Definizione: {item_obj.description})")
                        if ground_truth.is_guided_mode():
                            target_title_guided = item_obj.title
        
        if ground_truth.is_guided_mode():
            # === CASO GUIDATA (Focus su Item Specifico) ===
            # Anche se grado è 0, active_items_data ne contiene 1.
            focus_subject = target_title_guided if target_title_guided else "Item Target"
            context_str = "\n".join(active_items_data)
            label = "Punteggio"
            score_instruction = f"Riporta ESATTAMENTE il grado indicato nei 'Dati Contesto' per '{focus_subject}'. NON ricalcolarlo."
        
        else:
            # === CASO ESPLORATIVA (Focus sul Profilo) ===
            if not active_items_data:
                # SANO (Tutti 0)
                focus_subject = "Paziente Asintomatico (Sano)"
                context_str = "Nessun disturbo TALD attivo (Tutti a Grado 0)."
                label = "Punteggi"
                score_instruction = "Scrivi UNA SOLA frase riassuntiva (es. 'Nessun disturbo rilevato'). NON elencare i singoli item a 0."
            else:
                # PATOLOGICO (Uno o più disturbi > 0)
                focus_subject = "Profilo Clinico (Disturbi Rilevati)"
                context_str = "\n".join(active_items_data)
                label = "Punteggi"
                score_instruction = "Elenca i gradi ESATTI per tutti i disturbi attivi indicati nei 'Dati Contesto'."

        # 2. PROMPT DINAMICO
        analysis_prompt = f"""
Sei un supervisore clinico esperto nella Scala TALD.
Analizza la seguente trascrizione di un colloquio simulato.

DATI CONTESTO (GROUND TRUTH):
Oggetto della valutazione: {focus_subject}
Dettagli clinici reali:
{context_str}

TRASCRIZIONE:
{transcript}

COMPITO:
Genera un report clinico tecnico ("Justification") seguendo ESATTAMENTE lo schema fornito.
Se sono presenti più disturbi, analizzali congiuntamente nelle sezioni.

REGOLE DI FORMATTAZIONE CRITICHE (PER STRUTTURA AD ALBERO):
1. Usa "###" per i titoli delle sezioni principali (es. ### 1. Metadati Clinici).
2. Usa il simbolo "*" (asterisco) per le CATEGORIE (es. * Estratti chiave:).
3. Usa il simbolo "-" (trattino) per i CONTENUTI ANNIDATI sotto le categorie.
4. IMPORTANTE: NON TRADURRE I NOMI DEI DISTURBI. Usa sempre i termini TALD originali in INGLESE (es. scrivi "Derailment" NON "Deragliamento").

SCHEMA DI OUTPUT RICHIESTO (Template Tesi):

### 1. Metadati Clinici
* Quadro generale:
  - [Definisci se è un caso singolo, una comorbilità o un paziente sano, elencando i disturbi coinvolti]
* Criteri di riferimento:
  - [Riassumi brevemente i criteri diagnostici chiave per i disturbi presenti]

### 2. Evidenze e Ragionamento
* Estratti chiave:
  - "[Cita tra virgolette le frasi della chat che dimostrano i disturbi]"
* Collegamento ai criteri:
  - [Spiega perché queste frasi confermano la diagnosi e i gradi specifici]

### 3. Punteggio Finale e Confidenza
* Valutazione:
  - {label}: [{score_instruction}]
  - Confidenza: [Indica Alta, Media o Bassa]

### 4. Giustificazione a Tre Livelli
* Analisi quantitativa:
  - [Analizza lunghezza risposte, pause, disfluenze o frequenza dei fenomeni]
* Allineamento clinico:
  - [Sintesi del ragionamento clinico complessivo che giustifica il quadro]
* Limitazioni:
  - [Indica eventuali incertezze dovute alla brevità della simulazione]

NON aggiungere saluti, introduzioni o conclusioni.
Parti IMMEDIATAMENTE con "### 1. Metadati Clinici".
Scrivi in italiano professionale.
"""
        try:
            response = self.model.generate_content(analysis_prompt)
            return response.text.strip()
        except Exception as e:
            raise LLMConnectionError(f"Errore generazione spiegazione: {e}")

    def test_connection(self) -> bool:
        """Test di connessione semplice."""
        self._check_connectivity()
        try:
            self.model.generate_content("Test", request_options={'timeout': 5})
            return True
        except Exception:
            return False