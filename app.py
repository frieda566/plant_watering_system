import sqlite3
import threading
import tkinter as tk
from datetime import datetime

import pandas as pd
import queue
import json
import os
import serial.tools.list_ports

import serial

from ui_components import create_styled_button
from views.dashboard import show_dashboard
from views.history import show_history
from views.graphs import show_graphs
from views.lexicon import show_lexicon
from views.plant_health import show_plant_health


class PlantMonitoringApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Plant Monitoring System")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        self.colors = {
            "green_bg": "#677E52",
            "cream": "#F6E8B1",
            "dark_green": "#677E52",
            "lime": "#B7CA79",
            "sage": "#B0CC99",
            "brown": "#89725B",
        }

        self.root.configure(bg=self.colors["green_bg"])

        self.latest_data = {"moisture": 0, "temperature": 0, "humidity": 0}

        self.data_queue = queue.Queue()

        # History JSON
        self.history_file = "plant_history.json"

        # Load datasets
        self.health_df = pd.read_csv(
            "plant_health_ranges.csv",
            sep=";",
            skip_blank_lines=True,
            on_bad_lines="skip"
        )

        self.lexicon_df = pd.read_csv("plant_care_lexicon.csv")

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

        # optional: force specific port
        self.serial_port = '/dev/cu.usbmodem11401'  # insert the name of your port
        if self.serial_port is None:
            print("⚠ No Arduino detected. Running without live data.")
        else:
            try:
                self.serial = serial.Serial(self.serial_port, 9600, timeout=1)
                threading.Thread(target=self.read_serial_loop, daemon=True).start()
                print("✓ Serial connection established on:", self.serial_port)
            except:
                print("⚠ Could not open serial port.")

        # Build menu
        self.setup_main_menu()

    def setup_main_menu(self):

        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg=self.colors["green_bg"])
        frame.pack(fill="both", expand=True, padx=30, pady=30)

        tk.Label(
            frame,
            text="🌱 Plant Monitoring System",
            font=("Helvetica", 24, "bold"),
            bg=self.colors["green_bg"],
            fg="white"
        ).pack(pady=(20, 40))

        create_styled_button(frame, "📊 Dashboard",
                             lambda: show_dashboard(self))
        create_styled_button(frame, "📜 History",
                             lambda: show_history(self))
        create_styled_button(frame, "📈 Graphs",
                             lambda: show_graphs(self))
        create_styled_button(frame, "🌿 Lexicon",
                             lambda: show_lexicon(self))
        create_styled_button(frame, "🌱 My Plant",
                             lambda: show_plant_health(self))
        create_styled_button(frame, "❌ Exit", self.root.quit)

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

                    self.save_daily_reading()

            except serial.SerialException:
                print("Lost connection to Arduino!")
                self.serial_running = False
                break

            except Exception as e:
                print("Serial error:", e)

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

    # ---------------- Utility ----------------
    def clear_window(self):
        """Remove all widgets from the root window."""
        for widget in self.root.winfo_children():
            widget.destroy()
