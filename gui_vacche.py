import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os

class AppStalla:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Dati Stalla")
        self.root.geometry("1200x600")

        # Imposta il nome del file che si aspetta di trovare nella stessa cartella
        self.filepath = "vacche.csv" 
        
        self.colonne = [
            "id", "Peso_Corporeo_kg", "BCS", "DIM_Giorni_Lattazione", "Parita",
            "Giorni_Gravidanza", "Produzione_Latte_kg", "Grasso_perc", "Proteine_perc",
            "SCC", "Ruminazione_min", "pH_Ruminale", "BHB_mmol_L", "Manure_Score", "THI"
        ]

        self.setup_ui()
        # Carica i dati automaticamente all'avvio
        self.carica_csv()

    def setup_ui(self):
        # --- Barra dei Bottoni ---
        frame_btn = tk.Frame(self.root)
        frame_btn.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(frame_btn, text="Salva Modifiche su CSV", command=self.salva_csv, width=25, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="Modifica Vacca Selezionata", command=self.modifica_record, width=25, bg="lightblue").pack(side=tk.LEFT, padx=5)
        # Nuovo pulsante per aggiungere una vacca
        tk.Button(frame_btn, text="Aggiungi Vacca", command=self.aggiungi_record, width=20, bg="lightpink").pack(side=tk.LEFT, padx=5)

        # --- Tabella dei Dati (Treeview) ---
        frame_tabella = tk.Frame(self.root)
        frame_tabella.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_y = tk.Scrollbar(frame_tabella, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(frame_tabella, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(frame_tabella, columns=self.colonne, show="headings",
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.colonne:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.CENTER)

        # Doppio clic su una riga per modificarla
        self.tree.bind("<Double-1>", lambda event: self.modifica_record())

    def carica_csv(self):
        if not os.path.exists(self.filepath):
            messagebox.showwarning("File non trovato", f"Non ho trovato il file '{self.filepath}' nella cartella corrente.\nAssicurati che il nome sia corretto o inizia ad aggiungere nuove vacche.")
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            with open(self.filepath, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    valori = [row.get(col, "") for col in self.colonne]
                    self.tree.insert("", tk.END, values=valori)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere il file:\n{e}")

    def salva_csv(self):
        try:
            with open(self.filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(self.colonne)  # Scrive l'intestazione
                for row_id in self.tree.get_children():
                    row_data = self.tree.item(row_id)['values']
                    writer.writerow(row_data)
            messagebox.showinfo("Successo", "File aggiornato correttamente!")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")

    def modifica_record(self):
        selezionato = self.tree.selection()
        if not selezionato:
            messagebox.showwarning("Attenzione", "Seleziona prima una vacca dalla tabella per modificarla.")
            return

        item_id = selezionato[0]
        valori_attuali = self.tree.item(item_id)['values']

        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Dati Vacca")
        dialog.geometry("450x650")

        entries = {}
        for i, col in enumerate(self.colonne):
            frame = tk.Frame(dialog)
            frame.pack(fill=tk.X, padx=15, pady=5)
            tk.Label(frame, text=col, width=25, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            entry.insert(0, str(valori_attuali[i]))
            entries[col] = entry

        def applica_modifiche():
            nuovi_valori = [entries[col].get() for col in self.colonne]
            self.tree.item(item_id, values=nuovi_valori)
            dialog.destroy()

        tk.Button(dialog, text="Applica (Ricordati poi di Salvare)", command=applica_modifiche, bg="yellow").pack(pady=20)

    def aggiungi_record(self):
        # Finestra per l'inserimento di una nuova vacca
        dialog = tk.Toplevel(self.root)
        dialog.title("Aggiungi Nuova Vacca")
        dialog.geometry("450x650")

        entries = {}
        for col in self.colonne:
            frame = tk.Frame(dialog)
            frame.pack(fill=tk.X, padx=15, pady=5)
            tk.Label(frame, text=col, width=25, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            # Inseriamo uno "0" di default per praticità, tranne per l'ID che lasciamo vuoto
            if col != "id":
                entry.insert(0, "0")
            entries[col] = entry

        def inserisci_nuova():
            nuovi_valori = [entries[col].get() for col in self.colonne]
            
            # Controllo basilare: assicurarsi che almeno l'ID sia stato inserito
            if not nuovi_valori[0].strip():
                messagebox.showwarning("Attenzione", "L'ID della vacca è obbligatorio!", parent=dialog)
                return
                
            # Inserisce la nuova riga in fondo alla tabella
            self.tree.insert("", tk.END, values=nuovi_valori)
            dialog.destroy()

        tk.Button(dialog, text="Aggiungi in Tabella", command=inserisci_nuova, bg="lightpink").pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppStalla(root)
    root.mainloop()