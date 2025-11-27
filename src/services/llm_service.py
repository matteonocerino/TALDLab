"""
LLMService - Servizio per integrazione Google Gemini API

Questo modulo gestisce l'interfaccia con Google Gemini API per:
- Simulare pazienti virtuali con disturbi TALD
- Generare risposte clinicamente coerenti
- Produrre spiegazioni cliniche per i report
- Gestire timeout ed errori di connessione

Control del pattern Entity-Control-Boundary (vedi RAD sezione 2.6.1)
Implementa RF_3, RF_4, RF_11 del RAD
"""

import random
import threading
from typing import Dict, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.tald_item import TALDItem
from models.conversation import ConversationHistory


class LLMTimeoutError(Exception):
    """Eccezione per timeout nelle chiamate LLM."""
    pass


class LLMConnectionError(Exception):
    """Eccezione per errori di connessione all'API."""
    pass


class LLMService:
    """
    Service per gestione delle interazioni con Google Gemini API.
    
    Responsabilità:
    - Configurare e inizializzare Gemini API
    - Costruire prompt clinicamente accurati per simulazione pazienti
    - Generare risposte coerenti con i disturbi TALD
    - Gestire timeout ed errori come da RAD RF_11
    - Generare spiegazioni cliniche per i report
    """
    
    # Timeout calibrato per Gemini Flash Lite
    REQUEST_TIMEOUT = 12  # secondi
    
    def __init__(self, config: Dict[str, any]):
        """
        Inizializza il servizio LLM con la configurazione fornita.
        
        Args:
            config (dict): Configurazione contenente api_key, model, temperature, max_tokens
            
        Raises:
            ValueError: Se l'API key non è presente nella configurazione
            LLMConnectionError: Se la configurazione dell'API fallisce
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
    
    def _generate_patient_background(self) -> str:
        """Genera un background paziente randomizzato."""
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
        return f"Ti chiami {nome}, hai {eta} anni, lavori come {lavoro}"
    
    def _get_awareness_instructions(self, tald_item: TALDItem) -> str:
        """
        Genera istruzioni sulla consapevolezza del disturbo.
        Differenzia tra disturbi oggettivi (paziente inconsapevole) e 
        soggettivi (paziente consapevole ma riporta solo se interrogato).
        """
        if tald_item.is_objective():
            return """IMPORTANTE - DISTURBO OGGETTIVO:
- NON sei consapevole di avere questo disturbo.
- Il disturbo emerge spontaneamente nel tuo modo di parlare, fin dalla prima risposta.
- Se ti viene fatto notare il disturbo, reagisci con genuina confusione o incomprensione 
  ("Non capisco cosa intende...", "Davvero? Non me ne sono accorto...").
- Non negare in modo difensivo, semplicemente non capisci di cosa si parla."""
        else:
            return """IMPORTANTE - DISTURBO SOGGETTIVO:
- SEI consapevole di questo disturbo e del disagio che provoca.
- NON parlare spontaneamente del disturbo; descrivilo SOLO se l'intervistatore 
  ti chiede direttamente come ti senti o se hai difficoltà specifiche.
- Quando richiesto, puoi descrivere le tue esperienze interne e il tuo disagio.
- NON usare MAI il nome tecnico del disturbo."""

    def _get_grade_modulation_instructions(self, grade: int) -> str:
        """
        Restituisce istruzioni generali su come modulare l'intensità del disturbo.
        Le descrizioni specifiche del grado vengono dal JSON dell'item.
        """
        if grade == 0:
            return "Il disturbo NON è presente. Rispondi in modo completamente normale."
        elif grade == 1:
            return """## Intensità GRADO 1 (dubbio):
Il fenomeno è appena percepibile, al limite della normalità.
Manifestalo RARAMENTE (1-2 volte nell'intera conversazione) e in modo molto sottile."""
        elif grade == 2:
            return """## Intensità GRADO 2 (lieve):
Il fenomeno è presente ma non compromette significativamente la comunicazione.
Manifestalo ALCUNE VOLTE durante la conversazione, in modo riconoscibile."""
        elif grade == 3:
            return """## Intensità GRADO 3 (moderato):
Il fenomeno è evidente e influenza la conversazione.
Manifestalo SPESSO, l'intervistatore deve notarlo chiaramente."""
        else:  # grade == 4
            return """## Intensità GRADO 4 (severo/estremo):
Il fenomeno DOMINA la conversazione e può renderla molto difficile.
Manifestalo in QUASI OGNI risposta, in modo marcato."""

    def _get_item_specific_instructions(self, tald_item: TALDItem) -> str:
        """
        Genera istruzioni specifiche per alcuni item TALD che richiedono
        comportamenti particolari (es. pause, interruzioni, prolissità).
        """
        # Item che richiedono pause esplicite
        pause_items = ["Slowed Thinking", "Rupture of Thought", "Blocking"]
        
        # Item che richiedono prolissità (mai risposte brevi)
        verbose_items = ["Logorrhoea", "Pressured Speech", "Circumstantiality", 
                        "Poverty of Content of Speech"]
        
        # Item che richiedono risposte brevi
        brief_items = ["Poverty of Speech"]
        
        instructions = []
        
        if tald_item.title in pause_items:
            instructions.append(
                "- Usa '...' o '(pausa)' per indicare pause significative nel discorso, "
                "coerenti con il disturbo simulato."
            )
        
        if tald_item.title in verbose_items:
            instructions.append(
                "- Le tue risposte devono essere SEMPRE elaborate e prolisse, "
                "anche per domande semplici o saluti. Mai risposte brevi."
            )
        
        if tald_item.title in brief_items:
            instructions.append(
                "- Le tue risposte devono essere SEMPRE molto brevi, concrete, "
                "monosillabiche quando possibile. Non elaborare mai spontaneamente."
            )
        
        if tald_item.title == "Echolalia":
            instructions.append(
                "- Ripeti parole o frasi dell'intervistatore prima di (eventualmente) rispondere."
            )
        
        if tald_item.title == "Verbigeration":
            instructions.append(
                "- Ripeti singole parole più volte all'interno delle tue frasi."
            )
        
        if tald_item.title == "Perseveration":
            instructions.append(
                "- Torna ripetutamente a idee o frasi menzionate in precedenza, "
                "anche quando non sono più pertinenti."
            )
        
        if tald_item.title == "Restricted Thinking":
            instructions.append(
                "- Riporta ogni argomento al tuo tema fisso, "
                "anche quando l'intervistatore propone altri argomenti."
            )
        
        if tald_item.title == "Crosstalk":
            instructions.append(
                "- Rispondi 'a lato' della domanda: capisci cosa ti viene chiesto "
                "ma la tua risposta non centra il punto, pur essendo grammaticalmente corretta."
            )
        
        if instructions:
            return "\n## Istruzioni specifiche per questo disturbo:\n" + "\n".join(instructions)
        return ""

    def _build_system_prompt(
        self, 
        tald_item: TALDItem, 
        grade: int,
        patient_background: Optional[str] = None
    ) -> str:
        """
        Costruisce il prompt di sistema per simulare il paziente.
        Versione aggiornata con istruzioni più precise basate sul manuale TALD.
        """
        if patient_background is None:
            patient_background = self._generate_patient_background()
        
        grade_description = tald_item.get_grade_description(grade)
        awareness_instructions = self._get_awareness_instructions(tald_item)
        grade_modulation = self._get_grade_modulation_instructions(grade)
        item_specific = self._get_item_specific_instructions(tald_item)

        prompt = f"""# RUOLO E CONTESTO
Sei un PAZIENTE in un colloquio psichiatrico. L'intervistatore è un medico/psicologo clinico.
{patient_background}.

**REGOLA FONDAMENTALE:** Rispondi SOLO quando ti viene fatta una domanda. NON salutare per primo, NON fare domande, NON prendere iniziative nella conversazione.

Rivolgiti all'intervistatore sempre con "dottore" (forma neutra), mai "dottoressa" o altri appellativi.

---

# DISTURBO DA SIMULARE
**Disturbo:** {tald_item.title}
**Tipo:** {tald_item.type.upper()}
**Descrizione Clinica:** {tald_item.description}
**Criteri di Manifestazione:** {tald_item.criteria}
**Esempio Tipico:** {tald_item.example}

---

# SEVERITÀ DELLA MANIFESTAZIONE
**GRADO {grade}/4**
**Descrizione specifica per questo item:** {grade_description}

{grade_modulation}
{item_specific}

---

# ISTRUZIONI SULLA CONSAPEVOLEZZA
{awareness_instructions}

---

# REGOLE COMPORTAMENTALI FONDAMENTALI

1. **Sei un paziente, non un medico.** 
   - NON accogliere l'intervistatore
   - NON fare domande di cortesia ("Come sta?", "Come posso aiutarla?")
   - NON dare istruzioni o guidare la conversazione
   - NON iniziare argomenti di conversazione
   - Usa sempre "dottore" (mai "dottoressa")

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

3. **Esempi pratici:**
   
   **Domande anagrafiche (risposta NORMALE):**
   - "Come si chiama?" → "Marco" / "Mi chiamo Marco"
   - "Quanti anni ha?" → "35 anni" / "Ho 35 anni"
   - "Di dove è?" → "Sono di Napoli"
   
   **Domande che richiedono elaborazione (MANIFESTA DISTURBO):**
   - "Che lavoro fa?" → [risposta con disturbo]
   - "Mi parli della sua famiglia" → [risposta con disturbo]
   - "Come sta?" → [risposta con disturbo]
   - "Com'è andata la giornata?" → [risposta con disturbo]

4. **Mantieni il tuo ruolo.**
   - Sei il paziente
   - L'intervistatore è sempre "dottore" (forma neutra)
   - Atteggiamento collaborativo ma passivo

5. **Coerenza.** 
   Quando il disturbo deve manifestarsi, mantienilo costante nella stessa risposta e nelle risposte successive.

6. **Linguaggio naturale.**
   - Tono formale ma non rigido
   - Niente formulazioni cliniche o metalinguaggio
   - Non menzionare MAI il nome tecnico del disturbo ("{tald_item.title}")

7. **Limiti delle risposte.**
   - Rispondi alla domanda posta
   - Non elaborare spontaneamente oltre il necessario (tranne se il disturbo lo richiede, es. Logorrhoea, Circumstantiality)
   - Usa "..." per pause solo se appropriato al disturbo

---

# ESEMPI DI INTERAZIONI CORRETTE

**Intervistatore:** "Buongiorno"
**Tu:** "Buongiorno, dottore."
[Saluto → risposta normale]

**Intervistatore:** "Come si chiama?"
**Tu:** "Marco."
[Dato anagrafico → risposta normale]

**Intervistatore:** "Quanti anni ha?"
**Tu:** "35."
[Dato anagrafico → risposta normale]

**Intervistatore:** "Che lavoro fa?"
**Tu:** "Faccio il... (pausa) l'impiegato, sì... lavoro in ufficio... (pausa) ma stamattina non ricordo se..."
[Domanda elaborativa → manifesta disturbo]

**Intervistatore:** "Come sta oggi?"
**Tu:** [Manifesta il disturbo nella risposta]
[Domanda sul tuo stato → manifesta disturbo]

**SBAGLIATO:**
**Intervistatore:** "Buongiorno"
**Tu:** "Buongiorno dottoressa! Come sta?" ❌
[Non usare dottoressa, non fare domande]

---

# INIZIO SIMULAZIONE
Da questo momento rispondi SOLO quando interrogato, come il paziente descritto.
Attendi la prima domanda dell'intervistatore."""
        
        return prompt
    
    def start_chat_session(self, tald_item: TALDItem, grade: int) -> genai.ChatSession:
        """
        Inizia una nuova sessione di chat inviando le istruzioni di sistema.
        Chiamato UNA SOLA VOLTA all'inizio dell'intervista.
        """
        system_prompt = self._build_system_prompt(tald_item, grade)
        chat_session = self.model.start_chat(history=[
            {'role': 'user', 'parts': [system_prompt]},
            {'role': 'model', 'parts': ["Ok."]}
        ])
        return chat_session
    
    def generate_response(self, chat_session: genai.ChatSession, user_message: str) -> str:
        """Genera una risposta dal paziente virtuale."""
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
                    response_container["error"] = LLMTimeoutError("Risposta vuota o non ricevuta.")
            except Exception as e:
                response_container["error"] = e

        thread = threading.Thread(target=call_model, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            raise LLMTimeoutError("Timeout: il paziente virtuale non ha risposto in tempo.")

        if response_container["error"]:
            e = response_container["error"]

            if isinstance(e, DeadlineExceeded):
                raise LLMTimeoutError("Timeout interno di Gemini.")

            if isinstance(e, ResourceExhausted):
                msg = str(e).lower()
                if any(k in msg for k in ["rate limit", "too many requests", "retry in", 
                                          "requests per minute", "per-minute"]):
                    raise LLMConnectionError("Limite di richieste superato, attendere qualche secondo.")
                if "freetier" in msg or "daily" in msg:
                    raise LLMConnectionError("Quota giornaliera di Gemini esaurita.")
                raise LLMConnectionError(f"Risorsa esaurita: {e}")

            raise LLMConnectionError(f"Errore Gemini: {e}")

        if not response_container["text"]:
            raise LLMTimeoutError("Risposta non prodotta in tempo.")

        return response_container["text"]

    def generate_clinical_explanation(
        self,
        tald_item: TALDItem,
        conversation_history: ConversationHistory,
        grade: int
    ) -> str:
        """
        Genera una spiegazione clinica dei fenomeni osservati nella conversazione.
        Differenzia l'analisi tra disturbi oggettivi e soggettivi.
        """
    
        report_timeout = self.timeout
        response_container = {"text": None, "error": None}
    
        def call_model():
            try:
                transcript = conversation_history.to_text_transcript()
                grade_description = tald_item.get_grade_description(grade)
            
                # Focus diverso per objective vs subjective
                if tald_item.is_objective():
                    focus_instruction = """Focalizzati sui PATTERN LINGUISTICI OSSERVABILI nella conversazione:
- Struttura delle frasi e coerenza sintattica
- Ripetizioni, deviazioni dal tema, interruzioni
- Velocità e quantità della produzione verbale
- Relazione tra domande e risposte"""
                else:
                    focus_instruction = """Focalizzati su ciò che il paziente RIPORTA SOGGETTIVAMENTE:
- Le esperienze interne descritte dal paziente
- Il disagio e le difficoltà riferite
- La consapevolezza del problema mostrata
- Come il paziente descrive i propri sintomi"""

                analysis_prompt = f"""# COMPITO: Analisi Clinica di un Colloquio

Sei un clinico esperto che deve analizzare un colloquio psichiatrico per scopi didattici.

## DISTURBO SIMULATO
**Item TALD:** {tald_item.title}
**Tipo:** {tald_item.type.capitalize()}
**Grado:** {grade}/4 - {grade_description}

**Descrizione Clinica:**
{tald_item.description}

**Criteri Diagnostici:**
{tald_item.criteria}

---

## TRASCRIZIONE DEL COLLOQUIO

{transcript}

---

## FOCUS DELL'ANALISI
{focus_instruction}

---

## RICHIESTA

Fornisci un'analisi clinica (100-250 parole) che spieghi:

1. **Manifestazioni osservate**: Quali segnali specifici di "{tald_item.title}" sono presenti?

2. **Come riconoscerli**: Quali elementi permettono di identificare questo disturbo?

3. **Coerenza col grado {grade}**: La manifestazione corrisponde a "{grade_description}"?

4. **Indicazioni didattiche**: Cosa dovrebbe notare uno studente per riconoscere questo fenomeno?

Scrivi in italiano, in modo chiaro e professionale, come per uno studente di psichiatria.
"""
            
                response = self.model.generate_content(
                    analysis_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=800,
                    ),
                    request_options={'timeout': report_timeout}
                )
            
                if response and getattr(response, "text", None):
                    response_container["text"] = response.text.strip()
                else:
                    response_container["error"] = LLMTimeoutError("Spiegazione clinica non generata.")
            
            except Exception as e:
                response_container["error"] = e
    
        # Esegui in thread con timeout
        thread = threading.Thread(target=call_model, daemon=True)
        thread.start()
        thread.join(timeout=report_timeout)
    
        # 1. Timeout esterno
        if thread.is_alive():
            raise LLMConnectionError("Timeout di rete: il server non risponde.")
    
        # 2. Gestione errori
        if response_container["error"]:
            e = response_container["error"]
        
            if isinstance(e, DeadlineExceeded):
                raise LLMConnectionError("Il server non ha risposto in tempo (Timeout).")
        
            if isinstance(e, ResourceExhausted):
                msg = str(e).lower()
                if any(k in msg for k in ["rate limit", "too many requests", "retry in", 
                                        "requests per minute", "per-minute"]):
                    raise LLMConnectionError("Limite di richieste superato, attendere qualche secondo.")
                if "freetier" in msg or "daily" in msg:
                    raise LLMConnectionError("Quota giornaliera di Gemini esaurita.")
                raise LLMConnectionError(f"Risorsa esaurita: {e}")
        
            # Errori di rete generici
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["network", "connection", "timeout", "unreachable"]):
                raise LLMConnectionError(f"Errore di connessione di rete: {e}")
        
            raise LLMConnectionError(f"Errore Gemini: {e}")
    
        # 3. Verifica risposta
        if not response_container["text"]:
            raise LLMTimeoutError("Spiegazione clinica vuota o non prodotta in tempo.")
    
        return response_container["text"]
    
    def test_connection(self) -> bool:
        """Testa la connessione all'API Gemini."""
        try:
            self.model.generate_content(
                "Test",
                generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    max_output_tokens=5,
                )
            )
            return True
        except Exception as e:
            raise LLMConnectionError(f"Test di connessione fallito: {e}")