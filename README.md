# TALDLab

Prototipo di applicazione web per la simulazione di pazienti virtuali che manifestano disturbi del pensiero e del linguaggio secondo la scala TALD (Thought and Language Dysfunction Scale).

## Descrizione

TALDLab è uno strumento formativo per studenti e professionisti in ambito psicologico/psichiatrico, che permette di esercitarsi nel riconoscimento dei 30 item della scala TALD attraverso colloqui simulati con pazienti virtuali generati tramite Google Gemini API.

**Progetto di Tesi Triennale** Studente: Matteo Nocerino - Matricola 0512117269  
Relatore: Prof.ssa Rita Francese  
Anno Accademico 2024/2025

## Caratteristiche principali

- **Modalità guidata**: esercitazione su item TALD specifico
- **Modalità esplorativa**: identificazione e valutazione dell'item manifestato
- Interazione in linguaggio naturale via chat
- Valutazione automatica con confronto ground truth
- Report finale con spiegazioni cliniche
- Raccolta feedback per validazione del prototipo

## Tecnologie utilizzate

- Python 3.8+
- Streamlit (frontend e backend integrati)
- Google Gemini API (generazione linguaggio naturale)
- JSON (gestione dati strutturati)

## Riferimenti clinici

Il progetto si basa sulla **Thought and Language Dysfunction Scale (TALD)**, una scala clinica standardizzata per la valutazione di 30 fenomeni di disfunzione del pensiero e del linguaggio in ambito psichiatrico.

### Item TALD implementati (30 totali)

La scala TALD include fenomeni **oggettivi** (osservabili dall'esaminatore) e **soggettivi** (riportati dal paziente):

**Fenomeni oggettivi:**
- Circumstantiality, Derailment, Tangentiality, Dissociation of Thinking
- Crosstalk, Perseveration, Verbigeration, Rupture of Thought
- Pressured Speech, Logorrhoea, Manneristic Speech
- Semantic/Phonemic Paraphasia, Neologisms, Clanging, Echolalia
- Poverty of Content/Speech, Restricted/Slowed Thinking, Concretism

**Fenomeni soggettivi:**
- Blocking, Rumination, Poverty of Thought, Inhibited Thinking
- Receptive/Expressive Speech Dysfunction
- Dysfunction of Thought Initiative, Thought Interference, Pressure/Rush of Thoughts

## Struttura del progetto

```text
TALDLab/
├── app.py                      # Entry point applicazione Streamlit
├── tald_items.json             # Configurazione 30 item TALD
├── feedback_log.json           # Log feedback utenti (generato runtime)
├── requirements.txt            # Dipendenze Python
├── .env.example                # Template variabili d'ambiente
├── .gitignore                  # File da escludere da Git
├── README.md                   # Documentazione
├── assets/                     # Risorse statiche
│   └── taldlab_logo.png        # Logo del progetto
├── src/                        # Codice sorgente organizzato
│   ├── __init__.py
│   ├── utils.py                # Funzioni di utilità condivise
│   ├── services/               # Logica di business (Control)
│   │   ├── __init__.py
│   │   ├── configuration_service.py
│   │   ├── llm_service.py
│   │   ├── conversation_manager.py
│   │   ├── evaluation_service.py
│   │   ├── comparison_engine.py
│   │   ├── report_generator.py
│   │   └── feedback_service.py
│   ├── models/                 # Entità di dominio (Entity)
│   │   ├── __init__.py
│   │   ├── tald_item.py
│   │   ├── evaluation.py
│   │   ├── conversation.py
│   │   └── session_state.py
│   └── views/                  # Componenti interfaccia (Boundary)
│       ├── __init__.py
│       ├── mode_selection.py
│       ├── item_selection.py
│       ├── chat_interface.py
│       ├── evaluation_form.py
│       ├── report_view.py
│       └── feedback_form.py
│       ├── style.css
└── docs/
    ├── RAD_TALDLab.pdf         # Requirements Analysis Document
    └── TALD_Manual.pdf         # Manuale scala TALD
```

##  Documentazione

- [Requirements Analysis Document](docs/RAD_TALDLab.pdf) - Analisi dei requisiti completa
- [TALD Manual](docs/TALD_Manual.pdf) - Manuale ufficiale della scala TALD

## Note

Questo progetto è sviluppato a scopi didattici e formativi nell'ambito di una tesi universitaria. Non è destinato a uso clinico-diagnostico.    