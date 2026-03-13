import serial
import time
from mfrc522 import SimpleMFRC522

import pandas as pd
import joblib

rapportoForaggi = 0.1 # kg al giro
rapportoConcentrati = 0.1 # kg al giro

def ottieni_dati_vacca(cow_id):

    # Caricamento del file CSV
    file_path='/home/admin/vacche/vacche.csv'
    df = pd.read_csv(file_path)
    
    # Filtra la riga corrispondente all'id fornito
    riga = df[df['id'] == cow_id]
    
    # Rimuove la colonna 'id' dal risultato, prende la prima riga trovata (iloc[0]) 
    # e la trasforma in un dizionario
    dati_dizionario = riga.drop(columns=['id']).iloc[0].to_dict()
    return dati_dizionario

def calcolo(input):
    # 1. Carica il modello
    modello = joblib.load('/home/admin/vacche/modello_vacche.pkl')
    
    # 3. Converti in DataFrame e ordina le colonne esattamente come nel modello
    input_df = pd.DataFrame([input])
    input_df = input_df[modello.feature_names_in_]

    # 4. Fai la predizione (restituisce un array 2D, es: [[12.5, 9.2]])
    previsione_array = modello.predict(input_df)
    
    # 5. Inserisci i risultati direttamente in un dizionario
    # valore -> (Massa, Giri)
    risultato_dict = {
        'Foraggi' : (round(float(previsione_array[0][0]), 2), round(float(previsione_array[0][0]), 2)/rapportoForaggi),
        'Concentrati' : (round(float(previsione_array[0][1]), 2), round(float(previsione_array[0][1]), 2)/rapportoConcentrati)
    }
    
    return risultato_dict
    
# inizializza lettore RFID
reader = SimpleMFRC522()

# Configurazione porta seriale
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)  # attende Arduino

def muovi_motore(giri):
    """Invia il numero di giri all'Arduino"""
    comando = f"{giri}\n"
    ser.write(comando.encode('utf-8'))
    print(f"Inviato comando: {giri} giri")

def controlla_condizione():
    """Controlla se viene letto un tag RFID"""
    print("Avvicina il tag RFID...")
    id, text = reader.read()  # questo blocca finché non rileva il tag
    print("Tag rilevato UID:", id)
    return id

try:
    while True:
        ID = controlla_condizione()
        if ID:
            # UTILIZZARE FUNZIONE CALCOLO
            print(ID)
            numero_giri = calcolo(ottieni_dati_vacca(ID))["Foraggi"][1]
            #numero_giri = input("Inserisci quanti giri vuoi far fare: ")
            try:
                valore = float(numero_giri)
                muovi_motore(valore)
            except ValueError:
                print("Errore: Inserisci un numero valido!")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nChiusura programma...")
    ser.close()
