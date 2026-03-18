import serial
import time
import pandas as pd
import joblib
import os
from datetime import datetime
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

# --- COSTANTI ---
rapportoForaggi = 22.5 / 1000
rapportoConcentrati = 22.5 / 1000
COOLDOWN_TEMPO = 10  # Secondi per silenziare letture multiple

# --- PERCORSI FILE ---
print("Caricamento dati e modello in corso...")
file_path_csv = '/home/admin/vacche/vacche.csv'
file_path_modello = '/home/admin/vacche/modello_vacche.pkl'
file_path_registro = '/home/admin/vacche/registro_pasti.csv'

# Caricamento file e modello
df = pd.read_csv(file_path_csv)
df['id'] = df['id'].astype(str)
modello = joblib.load(file_path_modello)

# Dizionario per evitare letture doppie immediate
ultime_letture = {}

# --- INIZIALIZZAZIONE HARDWARE ---
print("Inizializzazione lettore RFID e Seriale...")
reader = SimpleMFRC522()

try:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2)  # attende il riavvio di Arduino
except serial.SerialException:
    print("ERRORE: Impossibile connettersi ad Arduino. Controlla il cavo o la porta USB.")
    exit()

# --- FUNZIONI DI REGISTRO ---

def ha_gia_mangiato_oggi(cow_id):
    """Controlla se la vacca ha già mangiato nella data odierna."""
    if not os.path.exists(file_path_registro):
        return False
        
    oggi = datetime.now().strftime('%Y-%m-%d')
    cow_id_str = str(cow_id)
    
    df_pasti = pd.read_csv(file_path_registro)
    
    filtro = (df_pasti['id'].astype(str) == cow_id_str) & (df_pasti['data'] == oggi)
    return not df_pasti[filtro].empty

def registra_pasto(cow_id, kg_foraggi, kg_concentrati):
    """Salva ID, Data e le quantità di razione in kg nel CSV."""
    oggi = datetime.now().strftime('%Y-%m-%d')
    file_esiste = os.path.exists(file_path_registro)
    
    with open(file_path_registro, 'a') as f:
        if not file_esiste:
            f.write("id,data,foraggi_kg,concentrati_kg\n")
        f.write(f"{cow_id},{oggi},{kg_foraggi},{kg_concentrati}\n")

# --- ALTRE FUNZIONI ---

def ottieni_dati_vacca(cow_id):
    """Cerca i parametri della vacca nel database precaricato."""
    cow_id_str = str(cow_id)
    riga = df[df['id'] == cow_id_str]
    if riga.empty:
        return None
    return riga.drop(columns=['id']).iloc[0].to_dict()

def calcolo(input_dict):
    """Calcola la razione (Massa e Giri) usando il modello di Machine Learning."""
    input_df = pd.DataFrame([input_dict])
    input_df = input_df[modello.feature_names_in_]
    previsione_array = modello.predict(input_df)
    
    risultato_dict = {
        'Foraggi': (round(float(previsione_array[0][0]), 2), round(float(previsione_array[0][0]), 2) / rapportoForaggi),
        'Concentrati': (round(float(previsione_array[0][1]), 2), round(float(previsione_array[0][1]), 2) / rapportoConcentrati)
    }
    return risultato_dict

def muovi_motore(giri):
    """Invia ad Arduino il numero di giri formattato a 2 decimali."""
    comando = f"{giri:.2f}\n" 
    ser.write(comando.encode('utf-8'))
    print(f"-> Inviato comando ad Arduino: {comando.strip()} giri")

# --- CICLO PRINCIPALE ---
print("\nSistema pronto! Avvicina il tag RFID...")

try:
    while True:
        # Legge SOLO l'ID per evitare l'AUTH ERROR
        id = reader.read_id()
        
        # Filtro Anti-Spam
        tempo_attuale = time.time()
        if id in ultime_letture and (tempo_attuale - ultime_letture[id]) < COOLDOWN_TEMPO:
            time.sleep(0.5)
            continue
            
        ultime_letture[id] = tempo_attuale
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tag rilevato UID: {id}")
        
        dati_vacca = ottieni_dati_vacca(id)
        if dati_vacca is None:
            print(f"ATTENZIONE: Nessuna vacca trovata nel CSV con ID {id}.")
            continue
            
        if ha_gia_mangiato_oggi(id):
            print(f"STOP: La vacca {id} ha già ricevuto la sua razione oggi.")
            continue
            
        print("Calcolo razione in corso...")
        risultati_razione = calcolo(dati_vacca)
        
        kg_foraggi = risultati_razione["Foraggi"][0]
        numero_giri_foraggi = risultati_razione["Foraggi"][1]
        kg_concentrati = risultati_razione["Concentrati"][0]
        
        try:
            valore = float(numero_giri_foraggi)
            muovi_motore(valore)
            
            registra_pasto(id, kg_foraggi, kg_concentrati)
            print(f"Pasto registrato! Dati salvati: {kg_foraggi} kg Foraggi, {kg_concentrati} kg Concentrati.")
            
        except ValueError:
            print("ERRORE: Il calcolo non ha generato un numero di giri valido!")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nInterruzione da tastiera (Ctrl+C). Chiusura programma...")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
    GPIO.cleanup()
    print("Porta seriale chiusa e pin GPIO ripuliti correttamente.")
