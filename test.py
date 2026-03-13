import pandas as pd
import joblib

rapportoForaggi = 0.1 # kg al giro
rapportoConcentrati = 0.1 # kg al giro

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
        'Foraggi' : (round(float(previsione_array[0][0]), 2), round(float(previsione_array[0][0]), 2)/rapportoForaggi),
        'Concentrati' : (round(float(previsione_array[0][1]), 2), round(float(previsione_array[0][1]), 2)/rapportoConcentrati)
    }
    
    return risultato_dict


mia_vacca = {
        'Peso_Corporeo_kg': 652.0,
        'BCS': 3.28,
        'DIM_Giorni_Lattazione': 258.0,
        'Parita': 1.0,
        'Giorni_Gravidanza': 172.0,
        'Produzione_Latte_kg': 31.3,
        'Grasso_perc': 4.17,
        'Proteine_perc': 3.3,
        'SCC': 294000.0,
        'Ruminazione_min': 426.0,
        'pH_Ruminale': 6.61,
        'BHB_mmol_L': 0.68,
        'Manure_Score': 3.0,
        'THI': 56.0
    }

# Stampa il dizionario
print(calcolo(mia_vacca))