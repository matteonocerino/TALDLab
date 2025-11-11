\# TALDLab



Prototipo di applicazione web per la simulazione di pazienti virtuali che manifestano disturbi del pensiero e del linguaggio secondo la scala TALD (Thought and Language Dysfunction Scale).



\## Descrizione



TALDLab è uno strumento formativo per studenti e professionisti in ambito psicologico/psichiatrico, che permette di esercitarsi nel riconoscimento dei 30 item della scala TALD attraverso colloqui simulati con pazienti virtuali generati tramite Google Gemini API.



\*\*Progetto di Tesi Triennale\*\*  

Studente: Matteo Nocerino - Matricola 0512117269  

Relatore: Prof.ssa Rita Francese  

Anno Accademico 2024/2025



\## Caratteristiche principali



\- \*\*Modalità guidata\*\*: esercitazione su item TALD specifico

\- \*\*Modalità esplorativa\*\*: identificazione e valutazione dell'item manifestato

\- Interazione in linguaggio naturale via chat

\- Valutazione automatica con confronto ground truth

\- Report finale con spiegazioni cliniche

\- Raccolta feedback per validazione del prototipo



\## Tecnologie utilizzate



\- Python 3.8+

\- Streamlit (frontend e backend integrati)

\- Google Gemini API (generazione linguaggio naturale)

\- JSON (gestione dati strutturati)



\## Riferimenti clinici



Il progetto si basa sulla \*\*Thought and Language Dysfunction Scale (TALD)\*\*, una scala clinica standardizzata per la valutazione di 30 fenomeni di disfunzione del pensiero e del linguaggio in ambito psichiatrico.



\### Item TALD implementati (30 totali)



La scala TALD include fenomeni \*\*oggettivi\*\* (osservabili dall'esaminatore) e \*\*soggettivi\*\* (riportati dal paziente):



\*\*Fenomeni oggettivi:\*\*

\- Circumstantiality, Derailment, Tangentiality, Dissociation of Thinking

\- Crosstalk, Perseveration, Verbigeration, Rupture of Thought

\- Pressured Speech, Logorrhoea, Manneristic Speech

\- Semantic/Phonemic Paraphasia, Neologisms, Clanging, Echolalia

\- Poverty of Content/Speech, Restricted/Slowed Thinking, Concretism



\*\*Fenomeni soggettivi:\*\*

\- Blocking, Rumination, Poverty of Thought, Inhibited Thinking

\- Receptive/Expressive Speech Dysfunction

\- Dysfunction of Thought Initiative, Thought Interference, Pressure/Rush of Thoughts



\## Struttura del progetto

```

TALDLab/

├── app.py                      # Entry point applicazione Streamlit

├── tald\_items.json             # Configurazione 30 item TALD

├── feedback\_log.json           # Log feedback utenti (generato runtime)

├── requirements.txt            # Dipendenze Python

├── .env.example               # Template variabili d'ambiente

├── .gitignore                 # File da escludere da Git

├── README.md                  # Documentazione

├── src/                       # Codice sorgente organizzato

│   ├── \_\_init\_\_.py

│   ├── services/              # Logica di business (Control)

│   │   ├── \_\_init\_\_.py

│   │   ├── configuration\_service.py

│   │   ├── llm\_service.py

│   │   ├── conversation\_manager.py

│   │   ├── evaluation\_service.py

│   │   ├── comparison\_engine.py

│   │   ├── report\_generator.py

│   │   └── feedback\_service.py

│   ├── models/                # Entità di dominio (Entity)

│   │   ├── \_\_init\_\_.py

│   │   ├── tald\_item.py

│   │   ├── evaluation.py

│   │   ├── conversation.py

│   │   └── session\_state.py

│   └── views/                 # Componenti interfaccia (Boundary)

│       ├── \_\_init\_\_.py

│       ├── mode\_selection.py

│       ├── item\_selection.py

│       ├── chat\_interface.py

│       ├── evaluation\_form.py

│       ├── report\_view.py

│       └── feedback\_form.py

│       ├── style.css

└── docs/

&nbsp;   ├── RAD\_TALDLab.pdf        # Requirements Analysis Document

&nbsp;   └── TALD\_Manual.pdf        # Manuale scala TALD

```

\## Documentazione



\- \[Requirements Analysis Document](docs/RAD\_TALDLab.pdf) - Analisi dei requisiti completa

\- \[TALD Manual](docs/TALD\_Manual.pdf) - Manuale ufficiale della scala TALD



\## Note



Questo progetto è sviluppato a scopi didattici e formativi nell'ambito di una tesi universitaria. Non è destinato a uso clinico-diagnostico.

