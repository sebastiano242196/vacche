import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os

# Importiamo la nostra funzione personalizzata dal file esterno
from dieta import calcola_razioni

class AppStalla:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Dati Stalla e Diete")
        self.root.geometry("1200x600")

        self.filepath = "vacche.csv" 
        
        # Le colonne di input aggiornate (senza i Target e senza THI)
        self.colonne = [
            "id", "Peso_Corporeo_kg", "BCS", "DIM_Giorni_Lattazione", "Parita",
            "Giorni_Gravidanza", "Produzione_Latte_kg", "Grasso_perc", "Proteine_perc",
            "SCC", "Ruminazione_min", "pH_Ruminale", "BHB_mmol_L", "Manure_Score"
        ]

        # Colonne da mostrare nella tabella principale (solo ID e Nome)
        self.display_columns = ["id", "name"]

        # Dizionario che conterrà tutti i dati completi letti dal CSV (key = id)
        self.tutti_i_dati = {}

        self.setup_ui()
        self.carica_csv()

    def setup_ui(self):
        # --- Barra dei Bottoni ---
        frame_btn = tk.Frame(self.root)
        frame_btn.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(frame_btn, text="Salva Modifiche", command=self.salva_csv, width=15, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="Aggiungi Vacca", command=self.aggiungi_record, width=15, bg="lightpink").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="Modifica Selezionata", command=self.modifica_record, width=20, bg="lightblue").pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_btn, text="Mostra Dieta", command=self.mostra_dieta, width=15, bg="orange", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=15)
        # Non usiamo più vacche_simple.csv: tutti i dati (name, model ecc.) vengono letti da `vacche.csv`
        # I dati completi saranno memorizzati in self.tutti_i_dati dal metodo carica_csv()

        # --- Tabella dei Dati (Treeview) ---
        frame_tabella = tk.Frame(self.root)
        frame_tabella.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_y = tk.Scrollbar(frame_tabella, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(frame_tabella, orient=tk.HORIZONTAL)

        # Mostriamo solo colonne ridotte (id e name) nella tabella principale
        self.tree = ttk.Treeview(frame_tabella, columns=self.display_columns, show="headings",
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.display_columns:
            # Rendi la colonna 'name' più larga
            width = 200 if col == 'name' else 120
            # Mostra intestazioni user-friendly
            label = 'Nome' if col == 'name' else 'ID'
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        # Quando la selezione cambia, apriamo la finestra di dettaglio per la vacca selezionata
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        # Variabili per evitare di aprire più finestre di dettaglio per la stessa vacca
        self._detail_window = None
        self._detail_item = None

        # Pannello laterale a destra per mostrare id/name e pulsante 3D
        right_panel = tk.Frame(self.root, width=260)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        tk.Label(right_panel, text='Selezione Vacca', font=("Arial", 11, "bold")).pack(pady=(5,10))
        self.lbl_selected_id = tk.Label(right_panel, text='ID: -')
        self.lbl_selected_id.pack(anchor='w', padx=5)
        self.lbl_selected_name = tk.Label(right_panel, text='Nome: -')
        self.lbl_selected_name.pack(anchor='w', padx=5, pady=(0,10))

        def open_3d_viewer():
            sel = self.tree.selection()
            if not sel:
                messagebox.showwarning('Attenzione', 'Seleziona prima una vacca dalla tabella.')
                return
            item = sel[0]
            valori = self.tree.item(item)['values']
            cow_id = valori[0]
            # Prendiamo il percorso del modello dal dizionario dei dati completi (caricato da vacche.csv)
            model_path = None
            dati = self.tutti_i_dati.get(cow_id, {})
            model_path = dati.get('model') if isinstance(dati, dict) else None
            if not model_path:
                messagebox.showwarning('Modello non trovato', f"Modello 3D non specificato per la vacca {cow_id}.")
                return
            # Risolvi path relativo alla cartella dello script
            model_abspath = os.path.abspath(os.path.join(os.path.dirname(__file__), model_path))
            if not os.path.exists(model_abspath):
                messagebox.showwarning('Modello non trovato', f"File modello non trovato:\n{model_abspath}")
                return
            # Apri il viewer HTML nel browser con query string ?model=path
            import webbrowser
            url = model_abspath.replace('\\','/')
            viewer = os.path.join('models','viewer.html')
            viewer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), viewer)).replace('\\','/')
            webbrowser.open(f'file:///{viewer_path}?model=file:///{url}')

        tk.Button(right_panel, text='Mostra 3D', command=open_3d_viewer, bg='lightblue').pack(pady=8)

    def on_select(self, event):
        selezionato = self.tree.selection()
        if not selezionato:
            return
        item_id = selezionato[0]
        # Aggiorna pannello laterale con id e name
        valori_vis = self.tree.item(item_id)['values']
        cow_id = valori_vis[0] if valori_vis else ''
        name = ''
        dati = self.tutti_i_dati.get(cow_id)
        if dati:
            name = dati.get('name','')
        else:
            # fallback: valore visualizzato
            if len(valori_vis) > 1:
                name = valori_vis[1]
        self.lbl_selected_id.config(text=f'ID: {cow_id}')
        self.lbl_selected_name.config(text=f'Nome: {name}')
        # Se è già aperta la finestra per lo stesso item non aprirne un'altra
        if self._detail_window is not None and self._detail_item == item_id:
            return
        self.apri_dettagli(item_id)

    def apri_dettagli(self, item_id):
        """Apre una finestra che mostra i dettagli della vacca selezionata e contiene il pulsante 'Mostra Dieta'."""
        valori = self.tree.item(item_id)['values']
        id_vacca = valori[0]

        # Chiudiamo eventuale finestra precedente
        if self._detail_window is not None:
            try:
                self._detail_window.destroy()
            except Exception:
                pass

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Dettagli Vacca: {id_vacca}")
        dialog.geometry("480x600")
        self._detail_window = dialog
        self._detail_item = item_id

        # Visualizziamo i valori come label (una riga per colonna)
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for i, col in enumerate(self.colonne):
            row = tk.Frame(frame)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=f"{col}", width=25, anchor='w').pack(side=tk.LEFT)
            val = valori[i] if i < len(valori) else ""
            tk.Label(row, text=str(val), anchor='w').pack(side=tk.LEFT, expand=True)

        # Pulsanti nella finestra di dettaglio
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)

        def mostra_dieta_locale():
            # Costruiamo il dizionario di input per il calcolo (escludendo 'id')
            input_dict = {}
            for i, col in enumerate(self.colonne):
                if col == 'id':
                    continue
                try:
                    input_dict[col] = float(valori[i])
                except Exception:
                    input_dict[col] = 0.0
            # Apri la finestra con il risultato della dieta
            self.mostra_dieta_from_values(id_vacca, input_dict)

        tk.Button(btn_frame, text="Mostra Dieta", command=mostra_dieta_locale, bg="orange").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Chiudi", command=lambda: (dialog.destroy(), setattr(self, '_detail_window', None), setattr(self, '_detail_item', None))).pack(side=tk.RIGHT, padx=5)

    def carica_csv(self):
        if not os.path.exists(self.filepath):
            messagebox.showwarning("File non trovato", f"Non ho trovato il file '{self.filepath}'.")
            return

        # Puliamo dati esistenti
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.tutti_i_dati.clear()

        try:
            with open(self.filepath, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    cow_id = row.get('id', '').strip()
                    # Salviamo il dizionario completo per uso interno, includendo eventuali colonne extra come 'name' e 'model'
                    dati_record = {col: (row.get(col, '').strip() if col in row else '') for col in self.colonne}
                    # campi opzionali
                    dati_record['name'] = row.get('name', '').strip() if 'name' in row else ''
                    dati_record['model'] = row.get('model', '').strip() if 'model' in row else ''
                    self.tutti_i_dati[cow_id] = dati_record
                    # Inseriamo nella tabella principale solo ID e Nome
                    self.tree.insert("", tk.END, values=(cow_id, dati_record.get('name','')))
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere il file:\n{e}")

    def salva_csv(self):
        try:
            # Salviamo il CSV usando i dati completi in self.tutti_i_dati
            with open(self.filepath, mode='w', newline='', encoding='utf-8') as file:
                # Se la colonna 'name' non è ancora in self.colonne, la aggiungiamo all'header
                header = ['id'] + [c for c in self.colonne if c != 'id']
                if 'name' not in header:
                    header.insert(1, 'name')
                writer = csv.DictWriter(file, fieldnames=header)
                writer.writeheader()
                for cow_id, data in self.tutti_i_dati.items():
                    # Prepara la riga combinando 'name' e le colonne originali
                    row = {'id': cow_id, 'name': data.get('name','')}
                    for c in self.colonne:
                        row[c] = data.get(c, '')
                    writer.writerow(row)
            messagebox.showinfo("Successo", "File aggiornato correttamente!")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")

    def modifica_record(self):
        selezionato = self.tree.selection()
        if not selezionato:
            messagebox.showwarning("Attenzione", "Seleziona prima una vacca dalla tabella per modificarla.")
            return

        item_id = selezionato[0]
        valori = self.tree.item(item_id)['values']
        cow_id = valori[0]
        dati = self.tutti_i_dati.get(cow_id, {})

        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Dati Vacca")
        dialog.geometry("500x700")

        entries = {}
        # Aggiungiamo anche il campo 'name' come primo campo modificabile
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15, pady=5)
        tk.Label(frame, text='name', width=25, anchor="w").pack(side=tk.LEFT)
        entry_name = tk.Entry(frame)
        entry_name.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        entry_name.insert(0, dati.get('name', ''))
        entries['name'] = entry_name

        for col in self.colonne:
            frame = tk.Frame(dialog)
            frame.pack(fill=tk.X, padx=15, pady=5)
            tk.Label(frame, text=col, width=25, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            entry.insert(0, str(dati.get(col, '')))
            entries[col] = entry

        def applica_modifiche():
            # Aggiorna i dati nel dizionario e nella riga della tabella
            nuovi = {col: entries[col].get() for col in entries}
            # Assicuriamoci di aggiornare la chiave id se viene cambiata
            new_id = nuovi.get('id', cow_id)
            # se l'id è cambiato, rimuoviamo la vecchia voce
            if new_id != cow_id:
                self.tutti_i_dati.pop(cow_id, None)
            # Salviamo i nuovi dati
            self.tutti_i_dati[new_id] = {c: nuovi.get(c, '') for c in self.colonne}
            self.tutti_i_dati[new_id]['name'] = nuovi.get('name', '')
            # Aggiorna la riga visibile (id e name)
            self.tree.item(item_id, values=(new_id, self.tutti_i_dati[new_id].get('name','')))
            dialog.destroy()

        tk.Button(dialog, text="Applica", command=applica_modifiche, bg="yellow").pack(pady=20)

    def aggiungi_record(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Aggiungi Nuova Vacca")
        dialog.geometry("500x700")

        entries = {}
        # Campo name
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15, pady=5)
        tk.Label(frame, text='name', width=25, anchor="w").pack(side=tk.LEFT)
        entry_name = tk.Entry(frame)
        entry_name.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        entries['name'] = entry_name

        for col in self.colonne:
            frame = tk.Frame(dialog)
            frame.pack(fill=tk.X, padx=15, pady=5)
            tk.Label(frame, text=col, width=25, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            if col != "id":
                entry.insert(0, "0")
            entries[col] = entry

        def inserisci_nuova():
            new_id = entries['id'].get().strip()
            if not new_id:
                messagebox.showwarning("Attenzione", "L'ID della vacca è obbligatorio!", parent=dialog)
                return
            if new_id in self.tutti_i_dati:
                messagebox.showwarning("Attenzione", "ID già presente!", parent=dialog)
                return
            # Costruisci il dizionario e salvalo
            dati = {c: entries[c].get() for c in self.colonne}
            dati['name'] = entries['name'].get()
            self.tutti_i_dati[new_id] = dati
            # Inserisci nella tabella principale solo id e name
            self.tree.insert("", tk.END, values=(new_id, dati.get('name','')))
            dialog.destroy()

        tk.Button(dialog, text="Aggiungi in Tabella", command=inserisci_nuova, bg="lightpink").pack(pady=20)

    def mostra_dieta(self):
            selezionato = self.tree.selection()
            if not selezionato:
                messagebox.showwarning("Attenzione", "Seleziona prima una vacca dalla tabella.")
                return

            item_id = selezionato[0]
            valori_vis = self.tree.item(item_id)['values']
            id_vacca = valori_vis[0]

            # Recupera i dati completi dal dizionario
            dati = self.tutti_i_dati.get(id_vacca)
            if dati is None:
                messagebox.showerror("Errore", "Dati completi non trovati per la vacca selezionata.")
                return

            # Raccoglie i dati in un dizionario numerico per il calcolo
            input_dict = {}
            for col in self.colonne:
                if col == 'id':
                    continue
                try:
                    input_dict[col] = float(dati.get(col, 0) if dati.get(col, '') != '' else 0.0)
                except Exception:
                    input_dict[col] = 0.0

            try:
                # --- CHIAMATA ALLA FUNZIONE DEL FILE ESTERNO ---
                risultato = calcola_razioni(input_dict)

                # --- CREAZIONE FINESTRA CUSTOM (Sostituisce il messagebox) ---
                win_dieta = tk.Toplevel(self.root)
                win_dieta.title("Risultato Calcolo Dieta")
                win_dieta.geometry("320x450")

                # Titolo
                tk.Label(win_dieta, text=f"ID Vacca: {id_vacca}", font=("Arial", 12, "bold")).pack(pady=10)

                # Frame per la griglia
                frame_dati = tk.Frame(win_dieta)
                frame_dati.pack(padx=20, fill=tk.BOTH, expand=True)

                # --- SEZIONE FORAGGI ---
                tk.Label(frame_dati, text="FORAGGI", font=("Arial", 10, "bold"), fg="darkgreen").grid(row=0, column=0, sticky="w", pady=(10, 5))

                foraggi = [
                    ("Erba Medica", risultato['Erba_Medica']),
                    ("Insilato Erba", risultato['Insilato_Erba']),
                    ("Fieno 1° Taglio", risultato['Fieno_1_Taglio']),
                    ("Fieno 2° Taglio", risultato['Fieno_2_Taglio']),
                    ("Fieno 3° Taglio", risultato['Fieno_3_Taglio'])
                ]

                riga = 1
                for nome, val in foraggi:
                    tk.Label(frame_dati, text=f"• {nome}:", font=("Arial", 10)).grid(row=riga, column=0, sticky="w", padx=10)
                    # Formattiamo il numero per avere sempre 2 decimali (es: 3.50 invece di 3.5)
                    tk.Label(frame_dati, text=f"{val:.2f} kg", font=("Arial", 10)).grid(row=riga, column=1, sticky="e")
                    riga += 1

                # --- SEZIONE CONCENTRATI ---
                tk.Label(frame_dati, text="CONCENTRATI", font=("Arial", 10, "bold"), fg="darkorange").grid(row=riga, column=0, sticky="w", pady=(15, 5))
                riga += 1

                concentrati = [
                    ("Mais", risultato['Mais']),
                    ("Orzo", risultato['Orzo']),
                    ("Soia", risultato['Soia']),
                    ("Crusca", risultato['Crusca']),
                    ("Mangimi Vari", risultato['Mangimi_Vari'])
                ]

                for nome, val in concentrati:
                    tk.Label(frame_dati, text=f"• {nome}:", font=("Arial", 10)).grid(row=riga, column=0, sticky="w", padx=10)
                    tk.Label(frame_dati, text=f"{val:.2f} kg", font=("Arial", 10)).grid(row=riga, column=1, sticky="e")
                    riga += 1

                # Permettiamo alla colonna di sinistra di espandersi, spingendo i numeri tutti a destra
                frame_dati.columnconfigure(0, weight=1)

                # Pulsante di chiusura
                tk.Button(win_dieta, text="Chiudi", command=win_dieta.destroy, width=15).pack(pady=15)

            except FileNotFoundError:
                messagebox.showerror("Errore", "Impossibile trovare 'modello_vacche.pkl'.\nAssicurati che sia nella stessa cartella.")
            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore durante il calcolo:\n{e}")

    def mostra_dieta_from_values(self, id_vacca, input_dict):
        """Mostra la finestra dieta a partire da un dizionario di input già pronto."""
        try:
            risultato = calcola_razioni(input_dict)

            win_dieta = tk.Toplevel(self.root)
            win_dieta.title("Risultato Calcolo Dieta")
            win_dieta.geometry("320x450")

            tk.Label(win_dieta, text=f"ID Vacca: {id_vacca}", font=("Arial", 12, "bold")).pack(pady=10)
            frame_dati = tk.Frame(win_dieta)
            frame_dati.pack(padx=20, fill=tk.BOTH, expand=True)

            tk.Label(frame_dati, text="FORAGGI", font=("Arial", 10, "bold"), fg="darkgreen").grid(row=0, column=0, sticky="w", pady=(10, 5))

            foraggi = [
                ("Erba Medica", risultato['Erba_Medica']),
                ("Insilato Erba", risultato['Insilato_Erba']),
                ("Fieno 1° Taglio", risultato['Fieno_1_Taglio']),
                ("Fieno 2° Taglio", risultato['Fieno_2_Taglio']),
                ("Fieno 3° Taglio", risultato['Fieno_3_Taglio'])
            ]

            riga = 1
            for nome, val in foraggi:
                tk.Label(frame_dati, text=f"• {nome}:", font=("Arial", 10)).grid(row=riga, column=0, sticky="w", padx=10)
                tk.Label(frame_dati, text=f"{val:.2f} kg", font=("Arial", 10)).grid(row=riga, column=1, sticky="e")
                riga += 1

            tk.Label(frame_dati, text="CONCENTRATI", font=("Arial", 10, "bold"), fg="darkorange").grid(row=riga, column=0, sticky="w", pady=(15, 5))
            riga += 1

            concentrati = [
                ("Mais", risultato['Mais']),
                ("Orzo", risultato['Orzo']),
                ("Soia", risultato['Soia']),
                ("Crusca", risultato['Crusca']),
                ("Mangimi Vari", risultato['Mangimi_Vari'])
            ]

            for nome, val in concentrati:
                tk.Label(frame_dati, text=f"• {nome}:", font=("Arial", 10)).grid(row=riga, column=0, sticky="w", padx=10)
                tk.Label(frame_dati, text=f"{val:.2f} kg", font=("Arial", 10)).grid(row=riga, column=1, sticky="e")
                riga += 1

            frame_dati.columnconfigure(0, weight=1)
            tk.Button(win_dieta, text="Chiudi", command=win_dieta.destroy, width=15).pack(pady=15)

        except FileNotFoundError:
            messagebox.showerror("Errore", "Impossibile trovare 'modello_vacche.pkl'.\nAssicurati che sia nella stessa cartella.")
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore durante il calcolo:\n{e}")
if __name__ == "__main__":
    root = tk.Tk()
    app = AppStalla(root)
    root.mainloop()