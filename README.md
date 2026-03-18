# Gestione Dati Stalla e Calcolo Diete (progetto)

Questo repository contiene strumenti per gestire i dati delle vacche in stalla e per calcolare razioni alimentari tramite un modello di Machine Learning.

## Panoramica dei file

- `gui_vacche.py` — Interfaccia grafica (Tkinter) per visualizzare/modificare il CSV `vacche.csv` e per mostrare la dieta calcolata per una vacca selezionata.
- `dieta.py` — Funzione `calcola_razioni(dati_vacca)` che carica il modello serializzato (`modello_vacche.pkl`) e restituisce i 10 ingredienti della dieta (foraggi + concentrati).
- `modello_vacche.pkl` — File binario contenente il modello di ML (scikit-learn / joblib). Necessario per la predizione.
- `vacche.csv` — Database in formato CSV con le righe delle vacche. Deve contenere la colonna `id` e le colonne dei parametri usati dal modello.
- `registro_pasti.csv` — File di registro degli alimenti somministrati (usato da `comandoGiri.py`).
- `comandoGiri.py` — Script pensato per l'ambiente Raspberry Pi + lettore RFID + Arduino: legge tag, calcola razione dal modello e invia comandi seriali ad Arduino. Usa `mfrc522`, `RPi.GPIO` e `pyserial`.
- `trova.py`, `test.py` — script di supporto/usati per testare il modello e recuperare dati dal CSV.

## Requisiti

- Python 3.10+ (consigliato).
- Pacchetti Python (un esempio è in `requirements.txt`). I principali sono:
  - pandas, numpy, joblib, scikit-learn, pyserial

Attenzione: `mfrc522` e `RPi.GPIO` sono specifici per Raspberry Pi e possono fallire su Windows. Rimuoverli da `requirements.txt` se si lavora su Windows.

## Struttura attesa di `vacche.csv`

La GUI e gli script si aspettano almeno queste colonne (header):

id,Peso_Corporeo_kg,BCS,DIM_Giorni_Lattazione,Parita,Giorni_Gravidanza,Produzione_Latte_kg,Grasso_perc,Proteine_perc,SCC,Ruminazione_min,pH_Ruminale,BHB_mmol_L,Manure_Score

Esempio di riga:

987654321008,652,3.28,258,1,172,31.3,4.17,3.3,294000,426,6.61,0.68,3

Nota: l'elenco esatto di colonne da passare al modello viene preso in `modello.feature_names_in_` al momento della predizione.

## Installazione e avvio (Windows, PowerShell)

1. Aprire PowerShell e posizionarsi nella cartella del progetto, es:
   Set-Location -LiteralPath "C:\Users\<utente>\Downloads\vacche\vacche"

2. Creare e attivare l'ambiente virtuale:
   python -m venv .\venv
   .\venv\Scripts\Activate.ps1
   (se la politica di esecuzione blocca lo script: eseguire PowerShell come admin e lanciare `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

3. Installare le dipendenze:
   pip install -r requirements.txt

4. Avviare l'interfaccia grafica:
   python gui_vacche.py

## Uso

- GUI (`gui_vacche.py`): aprire, selezionare una vacca dalla tabella, premere "Mostra Dieta" per calcolare e visualizzare la razione. Il calcolo chiama `dieta.calcola_razioni` che carica `modello_vacche.pkl`.

- Script per hardware (`comandoGiri.py`): da eseguire su Raspberry Pi dove sono collegati lettore RFID e Arduino. Controllare i percorsi dei file (variabili `file_path_csv`, `file_path_modello`, `file_path_registro`) e la porta seriale (es. `/dev/ttyACM0`).

## Debug e problemi comuni

- Errore: "Impossibile trovare 'modello_vacche.pkl'": assicurarsi che il file sia nella stessa cartella in cui si esegue lo script.
- Errori durante `pip install` di `RPi.GPIO` o `mfrc522`: sono normali su Windows. Rimuovere quelle righe da `requirements.txt` o installare solo su Raspberry Pi.
- Se la GUI non mostra dati: verificare che `vacche.csv` esista e che l'header corrisponda alle colonne attese.
- Per vedere/esportare le dipendenze installate: `pip freeze > requirements.txt`.

## Consigli

- Mantenere `modello_vacche.pkl` e `vacche.csv` aggiornati e sincronizzati con le colonne che il modello si aspetta.
- Testare il calcolo in locale con `test.py` prima di collegare l'hardware.

## Licenza

Nessuna licenza specificata nel repository. Aggiungere un file `LICENSE` se si desidera pubblicare con una licenza esplicita.

---

Se vuoi, aggiorno il README con esempi di output, istruzioni per il training del modello o un file `Makefile`/`tasks.json` per automatizzare i comandi di setup.
