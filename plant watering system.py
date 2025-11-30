import tkinter as tk
from tkinter import ttk, font
import sqlite3, threading, queue, pandas as pd
from datetime import datetime

class PlantMonitoringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plant Monitoring System")
        self._original_bg = "#55aa55"  # main menu background green
        self.root.configure(bg=self._original_bg)

        # ---------- Colors ----------
        self.colors = {
            "green_bg": "#677E52",  # main menu
            "cream": "#F6E8B1",  # popup / internal frames
            "dark_green": "#677E52",
            "lime": "#B7CA79",
            "sage": "#B0CC99",
            "brown": "#89725B",
        }

        # ---------- Data / DB ----------
        self.data_queue = queue.Queue()
        self.latest_data = {"moisture": 0, "temperature": 0, "humidity": 0}
        self.conn = sqlite3.connect("plant_data.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                timestamp TEXT, moisture INTEGER, temperature INTEGER, humidity INTEGER
            )
        """)
        self.conn.commit()

        # ---------- Load Lexicon ----------
        self.lexicon_df = pd.read_csv("plant_care_lexicon.csv")
        self.lexicon_df.columns = [c.strip() for c in self.lexicon_df.columns]
        # sort alphabetically
        self.lexicon_df = self.lexicon_df.sort_values(by="Plant Name", key=lambda col: col.str.lower())

        # ---------- Main Menu ----------
        self.setup_main_menu()

    # ---------------- Main Menu ----------------
    def setup_main_menu(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.configure(bg=self.colors["green_bg"])

        # master frame
        main_frame = tk.Frame(self.root, bg=self.colors["green_bg"])
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)

        # headline
        title_font = font.Font(family="Helvetica", size=24, weight="bold")
        tk.Label(main_frame, text="🌱 Plant Monitoring System",
                 font=title_font, bg=self.colors["green_bg"], fg="white").pack(pady=(20,40))

        # menu buttons
        button_frame = tk.Frame(main_frame, bg=self.colors["green_bg"])
        button_frame.pack()

        self.create_styled_button(button_frame, "📊 Dashboard", self.show_dashboard)
        self.create_styled_button(button_frame, "📜 History", self.show_history)
        self.create_styled_button(button_frame, "📈 Graphs", self.show_graphs)
        self.create_styled_button(button_frame, "🌿 Lexicon", self.show_lexicon)
        self.create_styled_button(button_frame, "❌ Exit", self.root.quit)

    # ---------------- Styled Button ----------------
    def create_styled_button(self, parent, text, command):
        outer = tk.Frame(parent, bg=self.colors["brown"])
        outer.pack(pady=8)
        inner = tk.Frame(outer, bg=self.colors["lime"])
        inner.pack(padx=3, pady=3)
        btn = tk.Button(inner, text=text, font=("Helvetica", 14, "bold"),
                        bg=self.colors["lime"], fg=self.colors["dark_green"],
                        relief="flat", bd=0, padx=20, pady=12,
                        cursor="hand2", command=command)
        btn.pack()
        # hover effect
        btn.bind("<Enter>", lambda e: (btn.config(bg=self.colors["sage"]), inner.config(bg=self.colors["sage"])))
        btn.bind("<Leave>", lambda e: (btn.config(bg=self.colors["lime"]), inner.config(bg=self.colors["lime"])))
        return btn

    #----------------- Styled Scrollbar ---------------
    # custom vertical scrollbar styled to palette
    def create_styled_scrollbar(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Vertical.TScrollbar",
            background=self.colors["sage"],
            troughcolor=self.colors["cream"],
            bordercolor=self.colors["brown"],
            arrowcolor=self.colors["dark_green"],
            darkcolor=self.colors["brown"],
            lightcolor=self.colors["lime"],
        )
        return ttk.Scrollbar(parent, orient="vertical", style="Custom.Vertical.TScrollbar")

    # ---------------- Back to Menu ----------------
    def back_to_menu_button(self, parent):
        self.create_styled_button(parent, "← Back to Menu", self.setup_main_menu)

    # ---------------- Dashboard ----------------
    def show_dashboard(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="📊 Dashboard", font=("Helvetica", 20, "bold"),
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack(pady=10)

        # live data labels
        self.moisture_label = tk.Label(frame, text="Soil Moisture: --%",
                                       font=("Helvetica", 16), bg=self.colors["cream"])
        self.temperature_label = tk.Label(frame, text="Temperature: --°C",
                                          font=("Helvetica", 16), bg=self.colors["cream"])
        self.humidity_label = tk.Label(frame, text="Humidity: --%",
                                       font=("Helvetica", 16), bg=self.colors["cream"])
        for lbl in (self.moisture_label, self.temperature_label, self.humidity_label):
            lbl.pack(pady=5)

        self.back_to_menu_button(frame)
        self.update_dashboard()

    def update_dashboard(self):
        if hasattr(self, "moisture_label") and self.moisture_label.winfo_exists():
            self.moisture_label.config(text=f"Soil Moisture: {self.latest_data['moisture']}%")
            self.temperature_label.config(text=f"Temperature: {self.latest_data['temperature']}°C")
            self.humidity_label.config(text=f"Humidity: {self.latest_data['humidity']}%")
            self.root.after(1000, self.update_dashboard)

    # ---------------- History ----------------
    def show_history(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="📜 History", font=("Helvetica", 20, "bold"),
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack(pady=10)

        table = ttk.Treeview(frame, columns=("time","moisture","temp","hum"), show="headings")
        table.heading("time", text="Timestamp")
        table.heading("moisture", text="Moisture (%)")
        table.heading("temp", text="Temperature (°C)")
        table.heading("hum", text="Humidity (%)")
        table.pack(fill="both", expand=True)
        self.history_table = table
        self.update_history()

        self.back_to_menu_button(frame)

    def update_history(self):
        if hasattr(self, "history_table") and self.history_table.winfo_exists():
            for row in self.history_table.get_children():
                self.history_table.delete(row)
            self.cur.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 100")
            for row in self.cur.fetchall():
                self.history_table.insert("", "end", values=row)
            self.root.after(3000, self.update_history)

    # ---------------- Graphs ----------------
    def show_graphs(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="📈 Graphs", font=("Helvetica", 20, "bold"),
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack(pady=10)

        # placeholder: can embed matplotlib graph here
        tk.Label(frame, text="Graphs would appear here", bg=self.colors["cream"]).pack(pady=50)

        self.back_to_menu_button(frame)

    # ---------------- Lexicon ----------------
    def show_lexicon(self):
        self.clear_window()

        main_frame = tk.Frame(self.root, bg=self.colors["cream"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header_frame = tk.Frame(main_frame, bg=self.colors["cream"])
        header_frame.pack(fill="x", pady=(10, 0))
        title_font = font.Font(family="Helvetica", size=20, weight="bold")
        tk.Label(header_frame, text="🌿 Lexicon", font=title_font,
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack()

        # Search bar
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_plants)  # <--- updated

        search_container = tk.Frame(main_frame, bg=self.colors["cream"])
        search_container.pack(pady=(10, 20))
        search_entry = tk.Entry(search_container, textvariable=self.search_var, width=50,
                                font=("Helvetica", 12), bg=self.colors["lime"],
                                fg=self.colors["dark_green"], relief="flat", bd=5,
                                insertbackground=self.colors["dark_green"])
        search_entry.pack(pady=5)

        # Scrollable container for plants
        self.scroll_container = tk.Frame(main_frame, bg=self.colors["cream"])
        self.scroll_container.pack(fill="both", expand=True)

        canvas = tk.Canvas(self.scroll_container, bg=self.colors["cream"], highlightthickness=0)
        scrollbar = self.create_styled_scrollbar(self.scroll_container)
        scrollbar.config(command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        self.scroll_frame = tk.Frame(canvas, bg=self.colors["cream"])
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Render all plant cards
        self.plant_cards = []  # store references to cards for filtering
        for _, row in self.lexicon_df.iterrows():
            card = tk.Frame(self.scroll_frame, bg=self.colors["brown"], bd=0, relief="ridge")
            card.pack(fill="x", pady=5, padx=5)

            inner = tk.Frame(card, bg=self.colors["sage"], padx=5, pady=5)
            inner.pack(fill="both", expand=True)

            tk.Label(inner, text=row["Plant Name"], font=("Helvetica", 14, "bold"),
                     bg=self.colors["sage"], fg=self.colors["dark_green"]).pack(side="left", padx=10)

            tk.Button(inner, text="Details", font=("Helvetica", 12, "bold"),
                      bg=self.colors["lime"], fg=self.colors["dark_green"],
                      relief="flat", bd=0, cursor="hand2",
                      command=lambda r=row: self.show_lexicon_popup(r)).pack(side="right", padx=10)

            self.plant_cards.append((card, row["Plant Name"].lower()))

        # Back button
        self.back_to_menu_button(main_frame)

    # ---------------- Lexicon Filter ----------------
    def filter_plants(self, *args):
        query = self.search_var.get().lower()
        for card, name in self.plant_cards:
            if query in name:
                card.pack(fill="x", pady=5, padx=5)
            else:
                card.pack_forget()

    # ---------------- Lexicon Popup ----------------
    def show_lexicon_popup(self, row):
        popup = tk.Toplevel(self.root)
        popup.title(row["Plant Name"])
        popup.configure(bg=self.colors["cream"])
        popup.geometry("500x500")  # larger size

        # Scrollable container
        canvas = tk.Canvas(popup, bg=self.colors["cream"], highlightthickness=0)
        scrollbar = self.create_styled_scrollbar(popup)
        scrollbar.config(command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors["cream"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def add_info_line(parent, headline, value):
            # headline label
            tk.Label(parent, text=headline, font=("Helvetica", 14, "bold"),
                     bg=self.colors["cream"], fg=self.colors["dark_green"], anchor="w").pack(fill="x", padx=10,
                                                                                             pady=(10, 0))
            # value label
            tk.Label(parent, text=value, font=("Helvetica", 12),
                     bg=self.colors["cream"], fg=self.colors["dark_green"], anchor="w", justify="left",
                     wraplength=450).pack(fill="x", padx=20, pady=(0, 5))
            # horizontal line separator
            ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=10, pady=5)

        # full plant info
        add_info_line(scroll_frame, "🌞 Light Preferences:", row['Light Preferences'])
        add_info_line(scroll_frame, "💧 Watering:", row['Watering'])
        add_info_line(scroll_frame, "🪴 Soil Type / Drainage:", row.get('Soil Type/Drainage', 'N/A'))
        add_info_line(scroll_frame, "🌡️ Temp / Humidity:", row.get('Temp / Humidity', 'N/A'))
        add_info_line(scroll_frame, "📏 Height Growth:", row.get('Height Growth', 'N/A'))
        add_info_line(scroll_frame, "⚠️ Common Problems:", row.get('Common Problems', 'N/A'))
        add_info_line(scroll_frame, "🌱 Propagation:", row.get('Propagation', 'N/A'))
        add_info_line(scroll_frame, "☠️ Toxicity:", row.get('Toxicity', 'N/A'))

        # Close button
        self.create_styled_button(scroll_frame, "✓ Close", popup.destroy)

    # ---------------- Utility ----------------
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

# ---------------- Launch ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PlantMonitoringApp(root)
    root.mainloop()

