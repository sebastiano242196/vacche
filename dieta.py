import pandas as pd
import joblib

def calcola_razioni(dati_vacca):
    """
    Riceve un dizionario con i dati della vacca, elabora la predizione
    e restituisce un dizionario con i 10 ingredienti della dieta.
    """
    # 1. Carica il modello
    modello = joblib.load('modello_vacche.pkl')
    
    # 2. Converti i dati in DataFrame
    input_df = pd.DataFrame([dati_vacca])
    
    # 3. Ordina le colonne come nel modello
    input_df = input_df[modello.feature_names_in_]

    # 4. Fai la predizione
    previsione_array = modello.predict(input_df)
    
    # 5. Estrai e formatta i 10 risultati (arrotondati a 2 decimali)
    # L'array [0] contiene i 10 valori nell'ordine in cui il modello è stato addestrato
    risultati = previsione_array[0]
    
    return {
        'Erba_Medica': round(float(risultati[0]), 2),
        'Insilato_Erba': round(float(risultati[1]), 2),
        'Fieno_1_Taglio': round(float(risultati[2]), 2),
        'Fieno_2_Taglio': round(float(risultati[3]), 2),
        'Fieno_3_Taglio': round(float(risultati[4]), 2),
        'Mais': round(float(risultati[5]), 2),
        'Orzo': round(float(risultati[6]), 2),
        'Soia': round(float(risultati[7]), 2),
        'Crusca': round(float(risultati[8]), 2),
        'Mangimi_Vari': round(float(risultati[9]), 2)
    }