import pandas as pd

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

