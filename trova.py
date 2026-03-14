import pandas as pd
import joblib 

def ottieni_dati_vacca(cow_id):

    # Caricamento del file CSV
    file_path='vacche.csv'
    df = pd.read_csv(file_path)
    
    # Filtra la riga corrispondente all'id fornito
    riga = df[df['id'] == cow_id]
    
    # Rimuove la colonna 'id' dal risultato, prende la prima riga trovata (iloc[0]) 
    # e la trasforma in un dizionario
    dati_dizionario = riga.drop(columns=['id']).iloc[0].to_dict()
    return dati_dizionario

def calcolo(input):
    # 1. Carica il modello
    modello = joblib.load('modello_vacche.pkl')
    
    # 3. Converti in DataFrame e ordina le colonne esattamente come nel modello
    input_df = pd.DataFrame([input])
    input_df = input_df[modello.feature_names_in_]

    # 4. Fai la predizione (restituisce un array 2D, es: [[12.5, 9.2]])
    previsione_array = modello.predict(input_df)
    
    # 5. Inserisci i risultati direttamente in un dizionario
    # valore -> (Massa, Giri)
    risultato_dict = {
        'Foraggi' : (round(float(previsione_array[0][0]), 2), round(float(previsione_array[0][0]), 2)),
        'Concentrati' : (round(float(previsione_array[0][1]), 2), round(float(previsione_array[0][1]), 2))
    }
    
    return risultato_dict

print (calcolo(ottieni_dati_vacca(987654321008)))