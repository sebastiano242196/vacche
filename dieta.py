import pandas as pd
import joblib

def calcola_razioni(dati_vacca):
    """
    Riceve un dizionario con i dati della vacca, elabora la predizione
    e restituisce un dizionario con Foraggi e Concentrati.
    """
    # 1. Carica il modello
    modello = joblib.load('modello_vacche.pkl')
    
    # 2. Converti i dati in DataFrame
    input_df = pd.DataFrame([dati_vacca])
    
    # 3. Ordina le colonne come nel modello
    input_df = input_df[modello.feature_names_in_]

    # 4. Fai la predizione
    previsione_array = modello.predict(input_df)
    
    # 5. Formatta i risultati
    val_foraggi = round(float(previsione_array[0][0]), 2)
    val_concentrati = round(float(previsione_array[0][1]), 2)
    
    return {
        'Foraggi': (val_foraggi, val_foraggi),
        'Concentrati': (val_concentrati, val_concentrati)
    }