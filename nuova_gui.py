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
        self.root.title("Dashboard Gestione Stalla e Diete - Professional")
        self.root.geometry("1400x900")
        
        # Colori Tema Professional
        self.bg_color = "#f4f7f6"
        self.primary_color = "#2c3e50"
        self.secondary_color = "#18bc9c"
        self.accent_color = "#e74c3c"
        self.text_color = "#333333"
        self.panel_bg = "#ffffff"
        
        self.root.configure(bg=self.bg_color)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background="#ffffff",
                        foreground=self.text_color,
                        rowheight=35,
                        fieldbackground="#ffffff",
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", 
                        background=self.primary_color, 
                        foreground="white", 
                        font=("Segoe UI", 11, "bold"))
        style.map("Treeview", 
                  background=[("selected", self.secondary_color)])

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

    def create_modern_button(self, parent, text, command, bg_color, fg_color="white", width=15):
        btn = tk.Button(parent, text=text, command=command, width=width, 
                        bg=bg_color, fg=fg_color, font=("Segoe UI", 10, "bold"),
                        relief="flat", borderwidth=0, padx=10, pady=8, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self._lighten_color(bg_color)))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color))
        return btn

    def _lighten_color(self, hex_color):
        # A simple method to lighten a hex color
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c * 1.2)) for c in rgb)
        return '#%02x%02x%02x' % rgb

    def setup_ui(self):
        # --- Header ---
        header_frame = tk.Frame(self.root, bg=self.primary_color, height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_label = tk.Label(header_frame, text="Sistema Gestione Stalla Integrato", 
                                bg=self.primary_color, fg="white", font=("Segoe UI", 16, "bold"))
        header_label.pack(side=tk.LEFT, padx=20, pady=15)

        # --- Barra dei Bottoni ---
        frame_btn = tk.Frame(self.root, bg=self.bg_color)
        frame_btn.pack(fill=tk.X, padx=20, pady=15)

        self.create_modern_button(frame_btn, "💾 Salva Dati", self.salva_csv, self.secondary_color).pack(side=tk.LEFT, padx=5)
        self.create_modern_button(frame_btn, "➕ Nuova Vacca", self.aggiungi_record, "#3498db").pack(side=tk.LEFT, padx=5)
        self.create_modern_button(frame_btn, "✏️ Modifica", self.modifica_record, "#f39c12").pack(side=tk.LEFT, padx=5)
        
        # Pulsanti di destra
        self.create_modern_button(frame_btn, "📊 Mostra Dieta", self.mostra_dieta, "#d35400", width=18).pack(side=tk.RIGHT, padx=5)
        self.create_modern_button(frame_btn, "📋 Gestione Pasti", self.apri_gestione_pasti, "#9b59b6", width=18).pack(side=tk.RIGHT, padx=5)

        # --- Frame Centrale (Tabella + Pannello Laterale) ---
        frame_centrale = tk.Frame(self.root, bg=self.bg_color)
        frame_centrale.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # --- Sezione Tabella ---
        frame_tabella_container = tk.Frame(frame_centrale, bg=self.panel_bg, highlightbackground="#ddd", highlightthickness=1)
        frame_tabella_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_tabella = tk.Label(frame_tabella_container, text="Registro Capi in Stalla", 
                               bg=self.panel_bg, fg=self.primary_color, font=("Segoe UI", 12, "bold"))
        title_tabella.pack(anchor="w", padx=15, pady=(15, 5))

        frame_tabella = tk.Frame(frame_tabella_container, bg=self.panel_bg)
        frame_tabella.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        scroll_y = ttk.Scrollbar(frame_tabella, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(frame_tabella, orient=tk.HORIZONTAL)

        self.tree = ttk.Treeview(frame_tabella, columns=self.display_columns, show="headings",
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for col in self.display_columns:
            width = 300 if col == 'name' else 150
            label = 'Nome Identificativo' if col == 'name' else 'Matricola (ID)'
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self._detail_window = None
        self._detail_item = None

        # --- Pannello laterale a destra ---
        right_panel = tk.Frame(frame_centrale, width=320, bg=self.panel_bg, highlightbackground="#ddd", highlightthickness=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        right_panel.pack_propagate(False)

        title_detail = tk.Label(right_panel, text='Dettaglio Selezione', bg=self.panel_bg, fg=self.primary_color, font=("Segoe UI", 12, "bold"))
        title_detail.pack(anchor='w', padx=15, pady=(15, 10))
        
        info_frame = tk.Frame(right_panel, bg="#f8f9fa", padx=10, pady=10)
        info_frame.pack(fill=tk.X, padx=15, pady=5)

        self.lbl_selected_id = tk.Label(info_frame, text='Matricola: -', bg="#f8f9fa", font=("Segoe UI", 10))
        self.lbl_selected_id.pack(anchor='w', pady=2)
        self.lbl_selected_name = tk.Label(info_frame, text='Nome: -', bg="#f8f9fa", font=("Segoe UI", 10, "bold"))
        self.lbl_selected_name.pack(anchor='w', pady=2)

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

        self.create_modern_button(right_panel, "🐄 Visualizza Modello 3D", open_3d_viewer, "#34495e").pack(fill=tk.X, padx=15, pady=15)
        
        separator = ttk.Separator(right_panel, orient='horizontal')
        separator.pack(fill=tk.X, padx=15, pady=10)
        
        mangiatoia_title = tk.Label(right_panel, text='Controllo Mangiatoia', bg=self.panel_bg, fg=self.primary_color, font=("Segoe UI", 12, "bold"))
        mangiatoia_title.pack(anchor='w', padx=15, pady=(10, 5))
        
        self.btn_mangiatoia = self.create_modern_button(right_panel, "▶ Avvia Sistema Autom.", self.toggle_mangiatoia, self.secondary_color)
        self.btn_mangiatoia.pack(fill=tk.X, padx=15, pady=10)

        # --- TERMINALE LOG GUI ---
        frame_log = tk.Frame(right_panel, bg=self.panel_bg)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        tk.Label(frame_log, text="Log di Sistema", bg=self.panel_bg, fg="#7f8c8d", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.log_text = tk.Text(frame_log, bg="#1e1e1e", fg="#4af626", font=("Consolas", 9), relief="flat")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text.config(state=tk.DISABLED)

    # --- NUOVA SEZIONE: GESTIONE PASTI ---
    def apri_gestione_pasti(self):
        """Apre una finestra per visualizzare e modificare il registro_pasti.csv"""
        win_pasti = tk.Toplevel(self.root)
        win_pasti.title("Gestione Registro Pasti")
        win_pasti.geometry("800x500")
        win_pasti.configure(bg="#f4f7f6")

        header_frame = tk.Frame(win_pasti, bg="#8e44ad", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        tk.Label(header_frame, text="Registro Alimentazione", bg="#8e44ad", fg="white", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=20, pady=15)

        colonne_pasti = ["id", "data", "foraggi_kg", "concentrati_kg"]

        # Tabella
        frame_tab_container = tk.Frame(win_pasti, bg="#ffffff", highlightbackground="#ddd", highlightthickness=1)
        frame_tab_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 10))

        scroll_y = ttk.Scrollbar(frame_tab_container, orient=tk.VERTICAL)
        tree_pasti = ttk.Treeview(frame_tab_container, columns=colonne_pasti, show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=tree_pasti.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_pasti.pack(fill=tk.BOTH, expand=True)

        intestazioni = {"id": "ID Vacca", "data": "Data ed Ora", "foraggi_kg": "Foraggi Erogati (kg)", "concentrati_kg": "Concentrati Erogati (kg)"}
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
        btn_frame = tk.Frame(win_pasti, bg="#f4f7f6")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

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
            if not selezionato:
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
            dialog.title("Modifica Registrazione")
            dialog.geometry("380x300")
            dialog.configure(bg="#ffffff")

            tk.Label(dialog, text="Aggiorna Dati Erogazione", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg="#2c3e50").pack(pady=15)

            entries = {}
            for i, col in enumerate(colonne_pasti):
                f = tk.Frame(dialog, bg="#ffffff")
                f.pack(fill=tk.X, padx=20, pady=5)
                tk.Label(f, text=intestazioni[col], width=18, anchor="w", bg="#ffffff", font=("Segoe UI", 9, "bold"), fg="#34495e").pack(side=tk.LEFT)
                entry = tk.Entry(f, font=("Segoe UI", 10), bg="#f8f9fa", relief="solid")
                entry.pack(side=tk.RIGHT, expand=True, fill=tk.X, ipady=3)
                entry.insert(0, str(valori_attuali[i]))
                entries[col] = entry

            def applica():
                nuovi = [entries[c].get() for c in colonne_pasti]
                tree_pasti.item(item_id, values=nuovi)
                dialog.destroy()

            btn_frame_dialog = tk.Frame(dialog, bg="#ffffff")
            btn_frame_dialog.pack(pady=20)
            self.create_modern_button(btn_frame_dialog, "Salva Modifiche", applica, "#f39c12", width=15).pack(side=tk.LEFT, padx=5)
            self.create_modern_button(btn_frame_dialog, "Annulla", dialog.destroy, "#95a5a6", width=10).pack(side=tk.RIGHT, padx=5)

        self.create_modern_button(btn_frame, "💾 Salva Storico su File", salva_registro, "#16a085", width=22).pack(side=tk.LEFT, padx=5)
        self.create_modern_button(btn_frame, "✏️ Modifica Valori", modifica_selezionato, "#2980b9", width=18).pack(side=tk.LEFT, padx=5)
        self.create_modern_button(btn_frame, "🗑 Elimina Record", elimina_selezionato, "#c0392b", width=18).pack(side=tk.LEFT, padx=5)

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
        self.lbl_selected_id.config(text=f'Matricola: {cow_id}')
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
        dialog.title(f"Scheda Dettaglio - Matricola {id_vacca}")
        dialog.geometry("550x750")
        dialog.configure(bg="#f4f7f6")
        self._detail_window = dialog
        self._detail_item = item_id

        header = tk.Frame(dialog, bg="#2c3e50", height=50)
        header.pack(fill=tk.X, side=tk.TOP)
        tk.Label(header, text=f"Dati Vacca: {id_vacca}", bg="#2c3e50", fg="white", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=15, pady=10)

        main_frame = tk.Frame(dialog, bg="#ffffff", highlightbackground="#ddd", highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        dati = self.tutti_i_dati.get(id_vacca, {})

        for i, col in enumerate(self.colonne):
            bg_col = "#f8f9fa" if i % 2 == 0 else "#ffffff"
            row = tk.Frame(main_frame, bg=bg_col)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{col.replace('_', ' ').title()}", width=25, anchor='w', bg=bg_col, font=("Segoe UI", 10, "bold"), fg="#34495e").pack(side=tk.LEFT, padx=10, pady=8)
            val = dati.get(col, "-")
            tk.Label(row, text=str(val), anchor='w', bg=bg_col, font=("Segoe UI", 10), fg="#2c3e50").pack(side=tk.LEFT, expand=True, padx=10)

        btn_frame = tk.Frame(dialog, bg="#f4f7f6")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        def mostra_dieta_locale():
            input_dict = {}
            for col in self.colonne:
                if col == 'id': continue
                try: input_dict[col] = float(dati.get(col, 0))
                except Exception: input_dict[col] = 0.0
            self.mostra_dieta_from_values(id_vacca, input_dict)

        self.create_modern_button(btn_frame, "📊 Calcola Dieta Ottimale", mostra_dieta_locale, "#e67e22", width=25).pack(side=tk.LEFT, pady=10)
        self.create_modern_button(btn_frame, "✖ Chiudi", lambda: (dialog.destroy(), setattr(self, '_detail_window', None), setattr(self, '_detail_item', None)), "#95a5a6", width=15).pack(side=tk.RIGHT, pady=10)

    def carica_csv(self):
        if not os.path.exists(self.filepath):
            messagebox.showwarning("File non trovato", f"Non ho trovato il file '{self.filepath}'.")
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.tutti_i_dati.clear()
        try:
            with open(self.filepath, newline='', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Rimuoviamo il BOM in caso sia presente anche se abbiamo usato utf-8-sig
                    # e iteriamo per trovare l'id ignorando possibili caratteri invisibili
                    id_key = next((k for k in row.keys() if k and k.strip().lower() == 'id'), None)
                    if id_key is None:
                        continue # Se non c'è una colonna ID valida, salto la riga

                    cow_id = str(row.get(id_key, '')).strip()
                    if not cow_id: # Salta righe vuote
                        continue

                    dati_record = {}
                    for col in self.colonne:
                        # cerchiamo la colonna corrispondente indipendentemente da spazi o BOM
                        col_key = next((k for k in row.keys() if k and k.strip().lower() == col.lower()), col)
                        dati_record[col] = str(row.get(col_key, '')).strip()

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
        dialog.title("Modifica Anagrafica e Dati di Stalla")
        dialog.geometry("600x800")
        dialog.configure(bg="#f4f7f6")
        
        header_frame = tk.Frame(dialog, bg="#2980b9", height=50)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        tk.Label(header_frame, text=f"Aggiornamento Dati - Matricola {cow_id}", bg="#2980b9", fg="white", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=15, pady=10)

        main_frame = tk.Frame(dialog, bg="#ffffff", highlightbackground="#ddd", highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(main_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", padx=5)

        entries = {}
        
        f_name = tk.Frame(scrollable_frame, bg="#f8f9fa", padx=10, pady=8)
        f_name.pack(fill=tk.X, pady=2)
        tk.Label(f_name, text='Nome Identificativo', width=25, anchor="w", bg="#f8f9fa", font=("Segoe UI", 9, "bold"), fg="#34495e").pack(side=tk.LEFT)
        entry_name = tk.Entry(f_name, font=("Segoe UI", 10), bg="#ffffff", relief="solid")
        entry_name.pack(side=tk.RIGHT, expand=True, fill=tk.X, ipady=4)
        entry_name.insert(0, dati.get('name', ''))
        entries['name'] = entry_name

        for i, col in enumerate(self.colonne):
            bg_col = "#ffffff" if i % 2 == 0 else "#f8f9fa"
            frame = tk.Frame(scrollable_frame, bg=bg_col, padx=10, pady=8)
            frame.pack(fill=tk.X, pady=2)
            tk.Label(frame, text=col.replace('_', ' ').title(), width=25, anchor="w", bg=bg_col, font=("Segoe UI", 9, "bold"), fg="#34495e").pack(side=tk.LEFT)
            entry = tk.Entry(frame, font=("Segoe UI", 10), bg="#ffffff", relief="solid")
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X, ipady=4)
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

        btn_container = tk.Frame(dialog, bg="#f4f7f6")
        btn_container.pack(fill=tk.X, pady=(0, 20))
        self.create_modern_button(btn_container, "✓ Salva Conferme", applica_modifiche, "#27ae60", width=20).pack(pady=10)

    def aggiungi_record(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Registrazione Nuovo Capo in Stalla")
        dialog.geometry("600x800")
        dialog.configure(bg="#f4f7f6")
        
        header_frame = tk.Frame(dialog, bg="#16a085", height=50)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        tk.Label(header_frame, text="Inserimento Nuova Scheda Anagrafica", bg="#16a085", fg="white", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=15, pady=10)

        main_frame = tk.Frame(dialog, bg="#ffffff", highlightbackground="#ddd", highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(main_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", padx=5)

        entries = {}
        
        f_name = tk.Frame(scrollable_frame, bg="#f8f9fa", padx=10, pady=8)
        f_name.pack(fill=tk.X, pady=2)
        tk.Label(f_name, text='Nome Identificativo', width=25, anchor="w", bg="#f8f9fa", font=("Segoe UI", 9, "bold"), fg="#34495e").pack(side=tk.LEFT)
        entry_name = tk.Entry(f_name, font=("Segoe UI", 10), bg="#ffffff", relief="solid")
        entry_name.pack(side=tk.RIGHT, expand=True, fill=tk.X, ipady=4)
        entries['name'] = entry_name

        for i, col in enumerate(self.colonne):
            bg_col = "#ffffff" if i % 2 == 0 else "#f8f9fa"
            frame = tk.Frame(scrollable_frame, bg=bg_col, padx=10, pady=8)
            frame.pack(fill=tk.X, pady=2)
            tk.Label(frame, text=col.replace('_', ' ').title(), width=25, anchor="w", bg=bg_col, font=("Segoe UI", 9, "bold"), fg="#34495e").pack(side=tk.LEFT)
            entry = tk.Entry(frame, font=("Segoe UI", 10), bg="#ffffff", relief="solid")
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X, ipady=4)
            entries[col] = entry

        def salva_nuovo():
            try:
                nuovi = {col: entries[col].get() for col in entries}
                new_id = nuovi.get('id', '').strip()
                if not new_id:
                    messagebox.showerror("Errore", "L'ID è obbligatorio!", parent=dialog)
                    return
                if new_id in self.tutti_i_dati:
                    messagebox.showerror("Errore", f"L'ID {new_id} esiste già!", parent=dialog)
                    return
                
                self.tutti_i_dati[new_id] = {c: nuovi.get(c, '') for c in self.colonne}
                self.tutti_i_dati[new_id]['name'] = nuovi.get('name', '')
                self.tree.insert("", tk.END, values=(new_id, self.tutti_i_dati[new_id]['name']))
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Errore", str(e), parent=dialog)

        btn_container = tk.Frame(dialog, bg="#f4f7f6")
        btn_container.pack(fill=tk.X, pady=(0, 20))
        self.create_modern_button(btn_container, "✓ Registra Capo", salva_nuovo, "#e67e22", width=20).pack(pady=10)

    def mostra_dieta(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Attenzione', 'Seleziona prima una vacca dalla tabella.')
            return
        item = sel[0]
        valori = self.tree.item(item)['values']
        cow_id = str(valori[0])
        dati = self.tutti_i_dati.get(cow_id, {})
        input_dict = {}
        for col in self.colonne:
            if col == 'id': continue
            try: input_dict[col] = float(dati.get(col, 0))
            except Exception: input_dict[col] = 0.0
        self.mostra_dieta_from_values(cow_id, input_dict)

    def mostra_dieta_from_values(self, id_vacca, input_dict):
        try:
            from dieta import calcola_razioni
            risultati = calcola_razioni(input_dict)
            
            top = tk.Toplevel(self.root)
            top.title(f"Piano Alimentare - Matricola {id_vacca}")
            top.geometry("700x550")
            top.configure(bg="#f4f7f6")
            
            header = tk.Frame(top, bg="#d35400", height=60)
            header.pack(fill=tk.X, side=tk.TOP)
            tk.Label(header, text=f"Distribuzione Dieta Consigliata per {id_vacca}", bg="#d35400", fg="white", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=20, pady=15)
            
            main_frame = tk.Frame(top, bg="#ffffff", highlightbackground="#ddd", highlightthickness=1)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
            
            cat_frame = tk.Frame(main_frame, bg="#ffffff")
            cat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            foraggi = {k:v for k,v in risultati.items() if 'forage' in k.lower() or 'silage' in k.lower() or 'hay' in k.lower()}
            concentrati = {k:v for k,v in risultati.items() if k not in foraggi}
            
            frame_foraggi = tk.Frame(cat_frame, bg="#e8f8f5", highlightbackground="#a3e4d7", highlightthickness=1)
            frame_foraggi.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            tk.Label(frame_foraggi, text="Foraggi / Fibra", font=("Segoe UI", 12, "bold"), bg="#1abc9c", fg="white").pack(fill=tk.X)
            
            frame_conc = tk.Frame(cat_frame, bg="#fef9e7", highlightbackground="#f9e79f", highlightthickness=1)
            frame_conc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            tk.Label(frame_conc, text="Concentrati / Integrazioni", font=("Segoe UI", 12, "bold"), bg="#f1c40f", fg="#333333").pack(fill=tk.X)
            
            for k, val in foraggi.items():
                row = tk.Frame(frame_foraggi, bg="#e8f8f5")
                row.pack(fill=tk.X, padx=15, pady=6)
                tk.Label(row, text=k.replace('_', ' ').title() + ":", bg="#e8f8f5", font=("Segoe UI", 10, "bold"), fg="#2c3e50", anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=f"{val:.2f} kg", bg="#e8f8f5", font=("Segoe UI", 10), fg="#34495e").pack(side=tk.RIGHT)
                
            for k, val in concentrati.items():
                row = tk.Frame(frame_conc, bg="#fef9e7")
                row.pack(fill=tk.X, padx=15, pady=6)
                tk.Label(row, text=k.replace('_', ' ').title() + ":", bg="#fef9e7", font=("Segoe UI", 10, "bold"), fg="#2c3e50", anchor="w").pack(side=tk.LEFT)
                tk.Label(row, text=f"{val:.2f} kg", bg="#fef9e7", font=("Segoe UI", 10), fg="#34495e").pack(side=tk.RIGHT)
            
            tot = sum(risultati.values())
            tot_frame = tk.Frame(main_frame, bg="#f8f9fa", highlightbackground="#bdc3c7", highlightthickness=1)
            tot_frame.pack(fill=tk.X, padx=20, pady=15)
            tk.Label(tot_frame, text=f"Totale Stimato: {tot:.2f} kg/giorno", font=("Segoe UI", 14, "bold"), bg="#f8f9fa", fg="#c0392b").pack(pady=15)

            btn_frame = tk.Frame(top, bg="#f4f7f6")
            btn_frame.pack(fill=tk.X, padx=25, pady=(0, 20))
            self.create_modern_button(btn_frame, "Stampa / Esporta", lambda: messagebox.showinfo("Esportazione", "Funzionalità in sviluppo.", parent=top), "#3498db", width=20).pack(side=tk.LEFT, pady=10)
            self.create_modern_button(btn_frame, "✖ Chiudi Riepilogo", top.destroy, "#95a5a6", width=20).pack(side=tk.RIGHT, pady=10)
            
        except Exception as e:
            messagebox.showerror('Errore Modello', f'Errore calcolo:\n{e}')

    # --- LOGICA HARDWARE E TERMINALE ---
    
    def log(self, messaggio):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {messaggio}")
        
    def aggiorna_terminale_gui(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self.aggiorna_terminale_gui)

    def toggle_mangiatoia(self):
        if not self.mangiatoia_running:
            self.mangiatoia_running = True
            self.btn_mangiatoia.config(text="⏹ Ferma Sistema Autom.", bg="#e74c3c")
            self.log("Avvio del Job Mangiatoia in background...")
            if not HARDWARE_AVAILABLE:
                self.log("-> HARDWARE NON RILEVATO. Modalità SIMULAZIONE attiva.")
            self.thread_mangiatoia = threading.Thread(target=self.loop_hardware_mangiatoia, daemon=True)
            self.thread_mangiatoia.start()
        else:
            self.mangiatoia_running = False
            self.btn_mangiatoia.config(text="▶ Avvia Sistema Autom.", bg=self.secondary_color)
            self.log("Arresto del Job Mangiatoia richiesto...")

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
