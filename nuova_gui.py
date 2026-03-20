import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import pandas as pd
from datetime import datetime
import threading
import queue
import time

# Importiamo la nostra funzione personalizzata dal file esterno
from dieta import calcola_razioni

# --- TENTATIVO DI IMPORTAZIONE HARDWARE RASPBERRY ---
try:
    import serial
    from mfrc522 import SimpleMFRC522
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

class AppStalla:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Dati Stalla e Diete")
        self.root.geometry("1200x800")

        self.filepath = "vacche.csv" 
        self.file_path_registro = "registro_pasti.csv"
        
        self.colonne = [
            "id", "Peso_Corporeo_kg", "BCS", "DIM_Giorni_Lattazione", "Parita",
            "Giorni_Gravidanza", "Produzione_Latte_kg", "Grasso_perc", "Proteine_perc",
            "SCC", "Ruminazione_min", "pH_Ruminale", "BHB_mmol_L", "Manure_Score"
        ]

        self.display_columns = ["id", "name"]
        self.tutti_i_dati = {}

        # Variabili per il controllo della Mangiatoia
        self.mangiatoia_running = False
        self.thread_mangiatoia = None
        self.log_queue = queue.Queue()
        
        # Costanti Mangiatoia
        self.rapportoForaggi = 22.5 / 100
        self.rapportoConcentrati = 22.5 / 100
        self.COOLDOWN_TEMPO = 10 

        self.setup_ui()
        self.carica_csv()
        
        self.aggiorna_terminale_gui()

    def setup_ui(self):
        # --- Barra dei Bottoni ---
        frame_btn = tk.Frame(self.root)
        frame_btn.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(frame_btn, text="Salva Modifiche", command=self.salva_csv, width=15, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="Aggiungi Vacca", command=self.aggiungi_record, width=15, bg="lightpink").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="Modifica Selezionata", command=self.modifica_record, width=20, bg="lightblue").pack(side=tk.LEFT, padx=5)
        
        # Pulsanti di destra
        tk.Button(frame_btn, text="Mostra Dieta", command=self.mostra_dieta, width=15, bg="orange", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=15)
        
        # NUOVO PULSANTE: Gestione Pasti
        tk.Button(frame_btn, text="Gestione Pasti", command=self.apri_gestione_pasti, width=15, bg="plum", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=5)

        # --- Frame Centrale (Tabella + Pannello Laterale) ---
        frame_centrale = tk.Frame(self.root)
        frame_centrale.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- Tabella dei Dati (Treeview) ---
        frame_tabella = tk.Frame(frame_centrale)
        frame_tabella.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = tk.Scrollbar(frame_tabella, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(frame_tabella, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(frame_tabella, columns=self.display_columns, show="headings",
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.display_columns:
            width = 200 if col == 'name' else 120
            label = 'Nome' if col == 'name' else 'ID'
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self._detail_window = None
        self._detail_item = None

        # --- Pannello laterale a destra ---
        right_panel = tk.Frame(frame_centrale, width=260)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

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
            cow_id = str(valori[0])
            model_path = None
            dati = self.tutti_i_dati.get(cow_id, {})
            model_path = dati.get('model') if isinstance(dati, dict) else None
            if not model_path:
                messagebox.showwarning('Modello non trovato', f"Modello 3D non specificato per la vacca {cow_id}.")
                return
            model_abspath = os.path.abspath(os.path.join(os.path.dirname(__file__), model_path))
            if not os.path.exists(model_abspath):
                messagebox.showwarning('Modello non trovato', f"File modello non trovato:\n{model_abspath}")
                return
            import webbrowser
            url = model_abspath.replace('\\','/')
            viewer = os.path.join('models','viewer.html')
            viewer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), viewer)).replace('\\','/')
            webbrowser.open(f'file:///{viewer_path}?model=file:///{url}')

        tk.Button(right_panel, text='Mostra 3D', command=open_3d_viewer, bg='lightblue').pack(pady=8)
        
        tk.Label(right_panel, text="-"*30).pack(pady=10)
        
        self.btn_mangiatoia = tk.Button(right_panel, text="▶ Avvia Mangiatoia", command=self.toggle_mangiatoia, bg="mediumseagreen", fg="white", font=("Arial", 11, "bold"))
        self.btn_mangiatoia.pack(pady=10, fill=tk.X)

        # --- TERMINALE LOG GUI ---
        frame_log = tk.LabelFrame(self.root, text="Terminale Mangiatoia", font=("Arial", 10, "bold"))
        frame_log.pack(fill=tk.X, padx=10, pady=(0, 10), side=tk.BOTTOM)
        
        self.log_text = tk.Text(frame_log, height=10, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.log_text.pack(fill=tk.X, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

    # --- NUOVA SEZIONE: GESTIONE PASTI ---
    def apri_gestione_pasti(self):
        """Apre una finestra per visualizzare e modificare il registro_pasti.csv"""
        win_pasti = tk.Toplevel(self.root)
        win_pasti.title("Gestione Registro Pasti")
        win_pasti.geometry("700x450")

        colonne_pasti = ["id", "data", "foraggi_kg", "concentrati_kg"]

        # Tabella
        frame_tab = tk.Frame(win_pasti)
        frame_tab.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_y = tk.Scrollbar(frame_tab, orient=tk.VERTICAL)
        tree_pasti = ttk.Treeview(frame_tab, columns=colonne_pasti, show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=tree_pasti.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_pasti.pack(fill=tk.BOTH, expand=True)

        intestazioni = {"id": "ID Vacca", "data": "Data", "foraggi_kg": "Foraggi (kg)", "concentrati_kg": "Concentrati (kg)"}
        for col in colonne_pasti:
            tree_pasti.heading(col, text=intestazioni[col])
            tree_pasti.column(col, anchor=tk.CENTER)

        # Funzione di caricamento dati
        def carica_dati_pasti():
            for row in tree_pasti.get_children():
                tree_pasti.delete(row)
            if os.path.exists(self.file_path_registro):
                try:
                    with open(self.file_path_registro, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            tree_pasti.insert("", tk.END, values=(row.get('id',''), row.get('data',''), row.get('foraggi_kg',''), row.get('concentrati_kg','')))
                except Exception as e:
                    messagebox.showerror("Errore", f"Impossibile leggere il registro:\n{e}", parent=win_pasti)

        carica_dati_pasti()

        # Bottoni di controllo
        btn_frame = tk.Frame(win_pasti)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def salva_registro():
            try:
                with open(self.file_path_registro, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(colonne_pasti)
                    for row_id in tree_pasti.get_children():
                        writer.writerow(tree_pasti.item(row_id)['values'])
                messagebox.showinfo("Successo", "Registro aggiornato correttamente!", parent=win_pasti)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}", parent=win_pasti)

        def elimina_selezionato():
            selezionato = tree_pasti.selection()
            if non selezionato:
                messagebox.showwarning("Attenzione", "Seleziona un pasto da eliminare.", parent=win_pasti)
                return
            for item in selezionato:
                tree_pasti.delete(item)

        def modifica_selezionato():
            selezionato = tree_pasti.selection()
            if not selezionato:
                messagebox.showwarning("Attenzione", "Seleziona un pasto da modificare.", parent=win_pasti)
                return
            
            item_id = selezionato[0]
            valori_attuali = tree_pasti.item(item_id)['values']

            dialog = tk.Toplevel(win_pasti)
            dialog.title("Modifica Pasto")
            dialog.geometry("300x250")

            entries = {}
            for i, col in enumerate(colonne_pasti):
                f = tk.Frame(dialog)
                f.pack(fill=tk.X, padx=15, pady=5)
                tk.Label(f, text=intestazioni[col], width=12, anchor="w").pack(side=tk.LEFT)
                entry = tk.Entry(f)
                entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
                entry.insert(0, str(valori_attuali[i]))
                entries[col] = entry

            def applica():
                nuovi = [entries[c].get() for c in colonne_pasti]
                tree_pasti.item(item_id, values=nuovi)
                dialog.destroy()

            tk.Button(dialog, text="Applica (Ricordati di Salvare)", command=applica, bg="yellow").pack(pady=15)

        tk.Button(btn_frame, text="Salva Registro Su File", command=salva_registro, bg="lightgreen", width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Modifica Selezionato", command=modifica_selezionato, bg="lightblue").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Elimina Selezionato", command=elimina_selezionato, bg="lightpink").pack(side=tk.LEFT, padx=5)

    # --- FUNZIONI DI LOGICA INTERFACCIA ORIGINALI ---
    def on_select(self, event):
        selezionato = self.tree.selection()
        if not selezionato: return
        item_id = selezionato[0]
        valori_vis = self.tree.item(item_id)['values']
        cow_id = str(valori_vis[0]) if valori_vis else ''
        name = ''
        dati = self.tutti_i_dati.get(cow_id)
        if dati:
            name = dati.get('name','')
        else:
            if len(valori_vis) > 1: name = valori_vis[1]
        self.lbl_selected_id.config(text=f'ID: {cow_id}')
        self.lbl_selected_name.config(text=f'Nome: {name}')
        if self._detail_window is not None and self._detail_item == item_id: return
        self.apri_dettagli(item_id)

    def apri_dettagli(self, item_id):
        valori = self.tree.item(item_id)['values']
        id_vacca = str(valori[0])
        if self._detail_window is not None:
            try: self._detail_window.destroy()
            except Exception: pass
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Dettagli Vacca: {id_vacca}")
        dialog.geometry("480x600")
        self._detail_window = dialog
        self._detail_item = item_id

        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        dati = self.tutti_i_dati.get(id_vacca, {})

        for col in self.colonne:
            row = tk.Frame(frame)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=f"{col}", width=25, anchor='w').pack(side=tk.LEFT)
            val = dati.get(col, "")
            tk.Label(row, text=str(val), anchor='w').pack(side=tk.LEFT, expand=True)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10)

        def mostra_dieta_locale():
            input_dict = {}
            for col in self.colonne:
                if col == 'id': continue
                try: input_dict[col] = float(dati.get(col, 0))
                except Exception: input_dict[col] = 0.0
            self.mostra_dieta_from_values(id_vacca, input_dict)

        tk.Button(btn_frame, text="Mostra Dieta", command=mostra_dieta_locale, bg="orange").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Chiudi", command=lambda: (dialog.destroy(), setattr(self, '_detail_window', None), setattr(self, '_detail_item', None))).pack(side=tk.RIGHT, padx=5)

    def carica_csv(self):
        if not os.path.exists(self.filepath):
            messagebox.showwarning("File non trovato", f"Non ho trovato il file '{self.filepath}'.")
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.tutti_i_dati.clear()
        try:
            with open(self.filepath, newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    cow_id = str(row.get('id', '')).strip()
                    dati_record = {col: (row.get(col, '').strip() if col in row else '') for col in self.colonne}
                    dati_record['name'] = row.get('name', '').strip() if 'name' in row else ''
                    dati_record['model'] = row.get('model', '').strip() if 'model' in row else ''
                    self.tutti_i_dati[cow_id] = dati_record
                    self.tree.insert("", tk.END, values=(cow_id, dati_record.get('name','')))
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere il file:\n{e}")

    def salva_csv(self):
        try:
            with open(self.filepath, mode='w', newline='', encoding='utf-8') as file:
                header = ['id'] + [c for c in self.colonne if c != 'id']
                if 'name' not in header: header.insert(1, 'name')
                writer = csv.DictWriter(file, fieldnames=header)
                writer.writeheader()
                for cow_id, data in self.tutti_i_dati.items():
                    row = {'id': cow_id, 'name': data.get('name','')}
                    for c in self.colonne: row[c] = data.get(c, '')
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
        cow_id = str(valori[0])
        dati = self.tutti_i_dati.get(cow_id, {})

        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Dati Vacca")
        dialog.geometry("500x700")
        entries = {}
        
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
            nuovi = {col: entries[col].get() for col in entries}
            new_id = str(nuovi.get('id', cow_id))
            if new_id != cow_id:
                self.tutti_i_dati.pop(cow_id, None)
            self.tutti_i_dati[new_id] = {c: nuovi.get(c, '') for c in self.colonne}
            self.tutti_i_dati[new_id]['name'] = nuovi.get('name', '')
            self.tree.item(item_id, values=(new_id, self.tutti_i_dati[new_id].get('name','')))
            dialog.destroy()

        tk.Button(dialog, text="Applica", command=applica_modifiche, bg="yellow").pack(pady=20)

    def aggiungi_record(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Aggiungi Nuova Vacca")
        dialog.geometry("500x700")
        entries = {}
        
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
            if col != "id": entry.insert(0, "0")
            entries[col] = entry

        def inserisci_nuova():
            new_id = entries['id'].get().strip()
            if not new_id:
                messagebox.showwarning("Attenzione", "L'ID della vacca è obbligatorio!", parent=dialog)
                return
            if new_id in self.tutti_i_dati:
                messagebox.showwarning("Attenzione", "ID già presente!", parent=dialog)
                return
            dati = {c: entries[c].get() for c in self.colonne}
            dati['name'] = entries['name'].get()
            self.tutti_i_dati[new_id] = dati
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
        id_vacca = str(valori_vis[0])
        dati = self.tutti_i_dati.get(id_vacca)
        if dati is None:
            messagebox.showerror("Errore", "Dati completi non trovati per la vacca selezionata.")
            return
            
        input_dict = {}
        for col in self.colonne:
            if col == 'id': continue
            try: input_dict[col] = float(dati.get(col, 0) if dati.get(col, '') != '' else 0.0)
            except Exception: input_dict[col] = 0.0
            
        self.mostra_dieta_from_values(id_vacca, input_dict)

    def mostra_dieta_from_values(self, id_vacca, input_dict):
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
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore durante il calcolo:\n{e}")

    # --- LOGICA HARDWARE E TERMINALE ---
    
    def log(self, messaggio):
        self.log_queue.put(messaggio)
        
    def aggiorna_terminale_gui(self):
        while not self.log_queue.empty():
            messaggio = self.log_queue.get()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, messaggio + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(100, self.aggiorna_terminale_gui)

    def toggle_mangiatoia(self):
        if not self.mangiatoia_running:
            self.mangiatoia_running = True
            self.btn_mangiatoia.config(text="⏹ Ferma Mangiatoia", bg="indianred")
            self.log(">>> INIZIALIZZAZIONE SISTEMA MANGIATOIA...")
            
            self.thread_mangiatoia = threading.Thread(target=self.loop_hardware_mangiatoia, daemon=True)
            self.thread_mangiatoia.start()
        else:
            self.mangiatoia_running = False
            self.btn_mangiatoia.config(text="▶ Avvia Mangiatoia", bg="mediumseagreen")
            self.log(">>> RICHIESTA DI ARRESTO MANGIATOIA IN CORSO...")

    def ha_gia_mangiato_oggi(self, cow_id):
        if not os.path.exists(self.file_path_registro):
            return False
        oggi = datetime.now().strftime('%Y-%m-%d')
        try:
            df_pasti = pd.read_csv(self.file_path_registro)
            filtro = (df_pasti['id'].astype(str) == str(cow_id)) & (df_pasti['data'] == oggi)
            return not df_pasti[filtro].empty
        except:
            return False

    def registra_pasto(self, cow_id, kg_foraggi, kg_concentrati):
        oggi = datetime.now().strftime('%Y-%m-%d')
        file_esiste = os.path.exists(self.file_path_registro)
        with open(self.file_path_registro, 'a', newline='') as f:
            if not file_esiste:
                f.write("id,data,foraggi_kg,concentrati_kg\n")
            f.write(f"{cow_id},{oggi},{kg_foraggi},{kg_concentrati}\n")

    def loop_hardware_mangiatoia(self):
        ser = None
        reader = None
        if HARDWARE_AVAILABLE:
            try:
                reader = SimpleMFRC522()
                ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
                time.sleep(2)
                self.log("✅ Hardware Connesso: Seriale e RFID pronti.")
            except Exception as e:
                self.log(f"❌ ERRORE HARDWARE: {e}")
                self.mangiatoia_running = False
                self.root.after(0, lambda: self.btn_mangiatoia.config(text="▶ Avvia Mangiatoia", bg="mediumseagreen"))
                return
        else:
            self.log("⚠️ MODALITA' SIMULATA (Hardware Raspberry non rilevato sul PC locale).")

        ultime_letture = {}
        self.log("\nSISTEMA PRONTO! In attesa di tag RFID...")

        while self.mangiatoia_running:
            id_letto = None
            
            if HARDWARE_AVAILABLE:
                id_letto, text = reader.read()
            else:
                time.sleep(5)
                # Scommenta questa riga se vuoi testare la simulazione inserendo un ID dal tuo CSV
                # id_letto = "100000000001" 

            if id_letto:
                id_str = str(id_letto)
                tempo_attuale = time.time()
                
                if id_str in ultime_letture and (tempo_attuale - ultime_letture[id_str]) < self.COOLDOWN_TEMPO:
                    time.sleep(0.5)
                    continue
                    
                ultime_letture[id_str] = tempo_attuale
                self.log(f"\n[{datetime.now().strftime('%H:%M:%S')}] Rilevato Tag: {id_str}")

                dati_vacca = self.tutti_i_dati.get(id_str)
                if dati_vacca is None:
                    self.log(f"ATTENZIONE: Nessuna vacca trovata in archivio con ID {id_str}.")
                    continue

                if self.ha_gia_mangiato_oggi(id_str):
                    self.log(f"STOP: La vacca {id_str} ha già mangiato oggi.")
                    continue

                self.log("Calcolo razione in corso...")
                
                input_dict = {}
                for col in self.colonne:
                    if col == 'id': continue
                    try: input_dict[col] = float(dati_vacca.get(col, 0))
                    except: input_dict[col] = 0.0
                
                try:
                    risultato = calcola_razioni(input_dict)
                    
                    kg_foraggi = round(risultato['Erba_Medica'] + risultato['Insilato_Erba'] + risultato['Fieno_1_Taglio'] + risultato['Fieno_2_Taglio'] + risultato['Fieno_3_Taglio'], 2)
                    kg_concentrati = round(risultato['Mais'] + risultato['Orzo'] + risultato['Soia'] + risultato['Crusca'] + risultato['Mangimi_Vari'], 2)
                    
                    giri_foraggi = kg_foraggi / self.rapportoForaggi
                    
                    if HARDWARE_AVAILABLE and ser:
                        comando = f"{giri_foraggi:.2f}\n" 
                        ser.write(comando.encode('utf-8'))
                        self.log(f"-> Inviato comando ad Arduino: {comando.strip()} giri")
                    else:
                        self.log(f"-> [SIMULAZIONE] Comando che verrebbe inviato ad Arduino: {giri_foraggi:.2f} giri")
                    
                    self.registra_pasto(id_str, kg_foraggi, kg_concentrati)
                    self.log(f"✅ PASTO EROGATO! ({kg_foraggi}kg Foraggi, {kg_concentrati}kg Concentrati).")
                    
                except Exception as e:
                    self.log(f"ERRORE di calcolo o invio: {e}")

            time.sleep(0.5)

        self.log(">>> MANGIATOIA ARRESTATA CORRETTAMENTE.")
        if HARDWARE_AVAILABLE and ser and ser.is_open:
            ser.close()
            GPIO.cleanup()
            self.log("Porte seriali e GPIO chiuse e pulite.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppStalla(root)
    root.mainloop()
