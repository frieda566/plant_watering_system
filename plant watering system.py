import tkinter as tk
from tkinter import ttk, font
import sqlite3, threading, queue, pandas as pd
import json
import os
import serial
import serial.tools.list_ports
from datetime import datetime, timedelta


class PlantMonitoringApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plant Monitoring System")
        self._original_bg = "#55aa55"  # main menu background green
        self.root.configure(bg=self._original_bg)
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.latest_data = {"moisture": None, "temperature": None, "humidity": None}
        # ---------- Load Plant Health Ranges ----------
        self.health_df = pd.read_csv(
            "plant_health_ranges.csv",
            sep=';',
            skip_blank_lines=True,
            on_bad_lines='skip'
        )
        self.health_df.columns = [c.strip() for c in self.health_df.columns]
        self.health_df["Plant Name"] = self.health_df["Plant Name"].str.strip()

        # ---------- Colors ----------
        self.colors = {
            "green_bg": "#677E52",  # main menu
            "cream": "#F6E8B1",  # popup / internal frames
            "dark_green": "#677E52",
            "lime": "#B7CA79",
            "sage": "#B0CC99",
            "brown": "#89725B",
        }

        # history
        self.history_file = "plant_history.json"
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as f:
                json.dump([], f)  # start with empty list

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

        # --------- Serial Setup (Arduino) ---------
        self.serial_port = None
        self.serial_running = True

        # Try auto-detect Arduino COM port
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if "Arduino" in p.description or "CH340" in p.description:
                self.serial_port = p.device
                break

        self.serial_port = '/dev/cu.usbmodem11401'
        if self.serial_port is None:
            print("⚠ No Arduino detected. Running without live data.")
        else:
            try:
                self.serial = serial.Serial(self.serial_port, 9600, timeout=1)
                threading.Thread(target=self.read_serial_loop, daemon=True).start()
                print("✓ Serial connection established on:", self.serial_port)
            except:
                print("⚠ Could not open serial port.")

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
                 font=title_font, bg=self.colors["green_bg"], fg="white").pack(pady=(20, 40))

        # menu buttons
        button_frame = tk.Frame(main_frame, bg=self.colors["green_bg"])
        button_frame.pack()

        self.create_styled_button(button_frame, "📊 Dashboard", self.show_dashboard)
        self.create_styled_button(button_frame, "📜 History", self.show_history)
        self.create_styled_button(button_frame, "📈 Graphs", self.show_graphs)
        self.create_styled_button(button_frame, "🌿 Lexicon", self.show_lexicon)
        self.create_styled_button(button_frame, "🌱 My Plant", self.show_plant_health)
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

    # ----------------- Styled Scrollbar ---------------
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

    def save_daily_reading(self):
        now = datetime.now()
        # Only record if current time is 2 PM and not already saved today
        if now.hour == 14:
            data = []
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
                    data = json.load(f)

            # Check if already saved today
            today_str = now.strftime("%Y-%m-%d")
            if data and data[-1]["timestamp"].startswith(today_str):
                return  # already saved for today

            # Add new reading
            data.append({
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "moisture": self.latest_data["moisture"],
                "temperature": self.latest_data["temperature"],
                "humidity": self.latest_data["humidity"]
            })

            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=4)

    def load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                data = json.load(f)
            # reverse to show newest first
            data.sort(key=lambda x: x["timestamp"])
            return data
        return []

    # ---------------- Back to Menu ----------------
    def back_to_menu_button(self, parent):
        self.create_styled_button(parent, "← Back to Menu", self.setup_main_menu)

    # ---------------- Dashboard ----------------
    def show_dashboard(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="📊 Dashboard", font=("Helvetica", 20, "bold"),
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack(pady=20)

        # live data labels container (placed in exact center)
        content = tk.Frame(frame, bg=self.colors["cream"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        # live data labels
        self.moisture_label = tk.Label(frame, text="Soil Moisture: --%",
                                       font=("Helvetica", 16, "bold"), bg=self.colors["cream"], fg=self.colors["brown"])
        self.temperature_label = tk.Label(frame, text="Temperature: --°C",
                                          font=("Helvetica", 16, "bold"), bg=self.colors["cream"],
                                          fg=self.colors["brown"])
        self.humidity_label = tk.Label(frame, text="Humidity: --%",
                                       font=("Helvetica", 16, "bold"), bg=self.colors["cream"], fg=self.colors["brown"])
        for lbl in (self.moisture_label, self.temperature_label, self.humidity_label):
            lbl.pack(pady=8)

        # Back button at bottom
        back_frame = tk.Frame(frame, bg=self.colors["cream"])
        back_frame.pack(side="bottom", pady=20)
        self.back_to_menu_button(back_frame)
        self.update_dashboard()

    def update_dashboard(self):
        if hasattr(self, "moisture_label") and self.moisture_label.winfo_exists():
            self.moisture_label.config(text=f"Soil Moisture: {self.latest_data['moisture']}%")
            self.temperature_label.config(text=f"Temperature: {self.latest_data['temperature']}°C")
            self.humidity_label.config(text=f"Humidity: {self.latest_data['humidity']}%")

            # Save daily reading if 2 PM
            self.save_daily_reading()

            self.root.after(1000, self.update_dashboard)

    def read_serial_loop(self):
        """Background thread reading Arduino messages."""
        while self.serial_running:
            try:
                line = self.serial.readline().decode().strip()
                if not line:
                    continue

                # Arduino sends: M:45,T:22,H:55
                parts = line.split(",")
                data = {}

                for p in parts:
                    if p.startswith("M:"):
                        data["moisture"] = int(p[2:])
                    elif p.startswith("T:"):
                        data["temperature"] = int(p[2:])
                    elif p.startswith("H:"):
                        data["humidity"] = int(p[2:])

                if len(data) == 3:
                    self.latest_data = data

                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.cur.execute(
                        "INSERT INTO readings (timestamp, moisture, temperature, humidity) VALUES (?, ?, ?, ?)",
                        (ts, data["moisture"], data["temperature"], data["humidity"])
                    )
                    self.conn.commit()

            except serial.SerialException:
                print("Lost connection to Arduino!")
                self.serial_running = False
                break

            except Exception as e:
                print("Serial error:", e)

    # ---------------- History ----------------
    def show_history(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="📜 History", font=("Helvetica", 20, "bold"),
                 bg=self.colors["cream"], fg=self.colors["dark_green"]).pack(pady=10)

        style = ttk.Style()
        style.theme_use("clam")  # ensure custom styles work

        # Configure the Treeview headings
        style.configure(
            "Treeview.Heading",
            font=("Helvetica", 12, "bold"),  # bold Helvetica
            foreground=self.colors["dark_green"],  # text color
            background=self.colors["sage"]  # optional background for header
        )

        table = ttk.Treeview(frame, columns=("time", "moisture", "temp", "hum"), show="headings")
        table.heading("time", text="Timestamp")
        table.heading("moisture", text="Moisture (%)")
        table.heading("temp", text="Temperature (°C)")
        table.heading("hum", text="Humidity (%)")
        table.pack(fill="both", expand=True)
        self.history_table = table

        # Define a tag for brown text
        table.tag_configure("brown_text", foreground=self.colors["brown"])

        # populate table from JSON
        for row in self.load_history():
            table.insert("", "end", values=(row["timestamp"], row["moisture"], row["temperature"], row["humidity"]),
                         tags=("brown_text",))

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
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        self.clear_window()

        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            frame, text="📈 Graphs",
            font=("Helvetica", 20, "bold"),
            bg=self.colors["cream"], fg=self.colors["dark_green"]
        ).pack(pady=10)

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "CustomNotebook.TNotebook",
            background=self.colors["cream"],
            borderwidth=0
        )

        style.configure(
            "CustomNotebook.TNotebook.Tab",
            background=self.colors["sage"],
            foreground=self.colors["dark_green"],
            padding=[10, 5]
        )

        style.map(
            "CustomNotebook.TNotebook.Tab",
            background=[("selected", self.colors["lime"])],
            foreground=[("selected", self.colors["dark_green"])]
        )

        # ---- Load History Data ----
        history = self.load_history()
        if not history:
            tk.Label(frame, text="No data available yet!",
                     bg=self.colors["cream"], fg=self.colors["dark_green"],
                     font=("Helvetica", 14)).pack()
            self.back_to_menu_button(frame)
            return

        # Extract values
        timestamps = [item["timestamp"] for item in history]
        moisture = [item["moisture"] for item in history]
        temperature = [item["temperature"] for item in history]
        humidity = [item["humidity"] for item in history]

        # ---------- Notebook (Tabs) ----------
        notebook = ttk.Notebook(frame, style="CustomNotebook.TNotebook")
        notebook.pack(fill="both", expand=True)

        # Create three tabs
        tab1 = tk.Frame(notebook, bg=self.colors["cream"])
        tab2 = tk.Frame(notebook, bg=self.colors["cream"])
        tab3 = tk.Frame(notebook, bg=self.colors["cream"])

        notebook.add(tab1, text="Moisture")
        notebook.add(tab2, text="Temperature")
        notebook.add(tab3, text="Humidity")

        # ----- Helper function to draw graph -----
        def draw_graph(tab, y_values, ylabel, title):
            fig = plt.Figure(figsize=(7, 4), dpi=100)
            ax = fig.add_subplot(111)

            # plot line
            ax.plot(timestamps, y_values, marker="o", linewidth=2, color=self.colors["sage"])

            # title
            ax.set_title(title, fontsize=14, color=self.colors["dark_green"], fontweight="bold")

            # labels
            ax.set_ylabel(ylabel, fontsize=12, color=self.colors["brown"])
            ax.set_xlabel("Time", fontsize=12, color=self.colors["brown"])

            # ticks
            ax.tick_params(axis="x", rotation=45, colors=self.colors["brown"])
            ax.tick_params(axis="y", colors=self.colors["brown"])

            # frame / rectangle around the plot
            for spine in ax.spines.values():
                spine.set_color(self.colors["dark_green"])

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

        # Draw each graph
        draw_graph(tab1, moisture, "Moisture (%)", "Moisture Over Time")
        draw_graph(tab2, temperature, "Temperature (°C)", "Temperature Over Time")
        draw_graph(tab3, humidity, "Humidity (%)", "Humidity Over Time")

        # Back button
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
        canvas_window = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Update scroll region and make scroll_frame expand with canvas width
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        self.scroll_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        # Render all plant cards
        self.plant_cards = []  # store references to cards for filtering
        for _, row in self.lexicon_df.iterrows():
            card = tk.Frame(self.scroll_frame, bg=self.colors["brown"], bd=0, relief="ridge")
            card.pack(fill="x", pady=5, padx=5)

            inner = tk.Frame(card, bg=self.colors["sage"], padx=10, pady=10)
            inner.pack(fill="x", expand=True)

            # prevent Tkinter from shrinking the frame
            inner.pack_propagate(False)
            inner.config(height=60)

            # Plant name label with weight to expand
            name_label = tk.Label(inner, text=row["Plant Name"], font=("Helvetica", 14, "bold"),
                                  bg=self.colors["sage"], fg=self.colors["dark_green"], anchor="w")
            name_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

            # Details button with fixed width
            # Remove the old details_btn code and replace with:

            # Create outer brown border frame
            outer_btn = tk.Frame(inner, bg=self.colors["brown"])
            outer_btn.pack(side="right", padx=10)

            # Create inner lime frame
            inner_btn = tk.Frame(outer_btn, bg=self.colors["lime"])
            inner_btn.pack(padx=3, pady=3)

            # Create button
            details_btn = tk.Button(inner_btn, text="Details",
                                    font=("Helvetica", 12, "bold"),
                                    bg=self.colors["lime"],
                                    fg=self.colors["dark_green"],
                                    relief="flat", bd=0, padx=15, pady=8,
                                    cursor="hand2",
                                    command=lambda r=row: self.show_lexicon_popup(r))
            details_btn.pack()

            # Hover effects
            details_btn.bind("<Enter>", lambda e, btn=details_btn, frame=inner_btn:
            (btn.config(bg=self.colors["sage"]), frame.config(bg=self.colors["sage"])))
            details_btn.bind("<Leave>", lambda e, btn=details_btn, frame=inner_btn:
            (btn.config(bg=self.colors["lime"]), frame.config(bg=self.colors["lime"])))

            # Hover effect for button
            details_btn.bind("<Enter>", lambda e, btn=details_btn: btn.config(bg=self.colors["sage"]))
            details_btn.bind("<Leave>", lambda e, btn=details_btn: btn.config(bg=self.colors["lime"]))

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

    def show_plant_health(self):
        self.clear_window()

        frame = tk.Frame(self.root, bg=self.colors["cream"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            frame, text="🌱 Weekly Plant Health",
            font=("Helvetica", 20, "bold"),
            bg=self.colors["cream"], fg=self.colors["dark_green"]
        ).pack(pady=10)

        tk.Label(
            frame, text="Select your plant:",
            bg=self.colors["cream"], fg=self.colors["dark_green"],
            font=("Helvetica", 14)
        ).pack(pady=5)

        plant_var = tk.StringVar()
        plant_names = self.lexicon_df["Plant Name"].tolist()

        dropdown = ttk.Combobox(
            frame, textvariable=plant_var,
            values=plant_names, state="readonly", width=30
        )
        dropdown.pack(pady=10)

        self.create_styled_button(
            frame,
            "Generate Health Report",
            lambda: self.generate_health_report(plant_var.get(), frame)
        )

        self.back_to_menu_button(frame)

    def get_last_week_data(self):
        history = self.load_history()
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        # Only include entries in the last 7 days and ignore zeros
        week_data = [
            d for d in history
            if datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") >= week_ago
               and d["temperature"] > 0 and d["humidity"] > 0
               and d["moisture"] > 0
        ]
        return week_data

    def get_optimal_ranges(self, plant_name):
        plant_name_clean = plant_name.strip().lower()
        row = self.health_df[
            self.health_df["Plant Name"].str.strip().str.lower() == plant_name_clean
            ]

        if row.empty:
            return None  # plant not found

        row = row.iloc[0]

        return {
            "temperature": (row["Temperature Min"], row["Temperature Max"]),
            "humidity": (row["Humidity Min"], row["Humidity Max"]),
            "moisture": (30, 60)  # average ideal percentage of soil moisture level for houseplants
        }

    def analyze_week(self, week_data, optimal):
        avg_temp = sum(d["temperature"] for d in week_data) / len(week_data)
        avg_hum = sum(d["humidity"] for d in week_data) / len(week_data)
        avg_moist = sum(d["moisture"] for d in week_data) / len(week_data)

        return [
            f"🌡 Temperature ({avg_temp:.1f}°C): {self.compare_value(avg_temp, *optimal['temperature'])}",
            f"💧 Humidity ({avg_hum:.1f}%): {self.compare_value(avg_hum, *optimal['humidity'])}",
            f"🌱 Soil Moisture ({avg_moist:.1f}%): {self.compare_value(avg_moist, *optimal['moisture'])}"
        ]

    def generate_health_report(self, plant_name, parent):
        if not plant_name:
            return

        plant_row = self.lexicon_df[self.lexicon_df["Plant Name"] == plant_name].iloc[0]
        optimal = self.get_optimal_ranges(plant_name)
        week_data = self.get_last_week_data()

        if not optimal:
            tk.Label(
                parent,
                text="No health reference data available for this plant.",
                bg=self.colors["cream"],
                fg=self.colors["dark_green"]
            ).pack()
            return

        if not week_data:
            tk.Label(
                parent, text="No weekly data available yet.",
                bg=self.colors["cream"], fg=self.colors["dark_green"]
            ).pack()
            return

        feedback = self.analyze_week(week_data, optimal)

        report_frame = tk.Frame(parent, bg=self.colors["sage"], padx=15, pady=15)
        report_frame.pack(fill="x", pady=20)

        tk.Label(
            report_frame,
            text=f"Weekly Health Report for {plant_name}",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["sage"], fg=self.colors["dark_green"]
        ).pack(pady=5)

        for line in feedback:
            tk.Label(
                report_frame,
                text=line,
                bg=self.colors["sage"], fg=self.colors["dark_green"],
                font=("Helvetica", 12), anchor="w"
            ).pack(fill="x")

    def compare_value(self, value, min_val, max_val):
        if value < min_val:
            return "⚠ Too low"
        elif value > max_val:
            return "⚠ Too high"
        return "✔ Optimal"

    # ---------------- Utility ----------------
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()


# ---------------- Launch ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PlantMonitoringApp(root)
    root.mainloop()
