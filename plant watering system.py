import serial
import sqlite3
import threading
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt

# --------------------------
# CONFIG
# --------------------------
SERIAL_PORT = "/dev/cu.usbmodem11101"     # <-- CHANGE THIS TO YOUR COM PORT
BAUD_RATE = 9600

# --------------------------
# DATABASE SETUP
# --------------------------
conn = sqlite3.connect("plant_data.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS readings (
    timestamp TEXT,
    moisture INTEGER,
    water_dist INTEGER
)
""")
conn.commit()

# --------------------------
# READ FROM ARDUINO THREAD
# --------------------------
arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
latest_data = {"moisture": None, "water_dist": None}

def serial_reader():
    global latest_data
    while True:
        try:
            line = arduino.readline().decode().strip()
            if not line:
                continue

            if line.startswith("MOISTURE:"):
                latest_data["moisture"] = int(line.split(":")[1])
            elif line.startswith("WATER_DIST:"):
                latest_data["water_dist"] = int(line.split(":")[1])

            # Save to DB when both values are present
            if latest_data["moisture"] is not None and latest_data["water_dist"] is not None:
                cur.execute(
                    "INSERT INTO readings VALUES (?, ?, ?)",
                    (datetime.now().isoformat(),
                     latest_data["moisture"],
                     latest_data["water_dist"])
                )
                conn.commit()

        except:
            pass

threading.Thread(target=serial_reader, daemon=True).start()

# --------------------------
# GUI SETUP
# --------------------------
root = tk.Tk()
root.title("Plant Watering System Dashboard")
root.geometry("500x430")
root.configure(bg="#c8f7c5")  # Light green background

title = tk.Label(root,
                 text="Plant Monitoring Dashboard",
                 font=("Arial", 20, "bold"),
                 bg="#c8f7c5",
                 fg="#0652DD")   # blue
title.pack(pady=10)

frame = tk.Frame(root, bg="#c8f7c5")
frame.pack(pady=20)

moisture_label = tk.Label(frame, text="Soil Moisture: --%", font=("Arial", 16), bg="#c8f7c5")
water_label = tk.Label(frame, text="Water Tank Distance: -- cm", font=("Arial", 16), bg="#c8f7c5")

moisture_label.pack(pady=5)
water_label.pack(pady=5)

# --------------------------
# GUI UPDATE LOOP
# --------------------------
def update_gui():
    if latest_data["moisture"] is not None:
        moisture_label.config(text=f"Soil Moisture: {latest_data['moisture']}%")
    if latest_data["water_dist"] is not None:
        water_label.config(text=f"Water Tank Distance: {latest_data['water_dist']} cm")
    root.after(1000, update_gui)

update_gui()

# --------------------------
# HISTORY WINDOW
# --------------------------
def open_history():
    win = tk.Toplevel(root)
    win.title("Reading History")
    win.geometry("500x400")

    tree = ttk.Treeview(win, columns=("time", "moisture", "dist"), show="headings")
    tree.heading("time", text="Timestamp")
    tree.heading("moisture", text="Moisture")
    tree.heading("dist", text="Water Distance")
    tree.pack(fill="both", expand=True)

    cur.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 200")
    for row in cur.fetchall():
        tree.insert("", "end", values=row)

# --------------------------
# GRAPH WINDOW
# --------------------------
def open_graphs():
    cur.execute("SELECT timestamp, moisture, water_dist FROM readings ORDER BY timestamp ASC")
    rows = cur.fetchall()

    if len(rows) < 2:
        print("Not enough data for graphs.")
        return

    timestamps = [datetime.fromisoformat(r[0]) for r in rows]
    moisture = [r[1] for r in rows]
    water = [r[2] for r in rows]

    plt.figure(figsize=(10,6))

    # Moisture graph
    plt.subplot(2,1,1)
    plt.plot(timestamps, moisture)
    plt.title("Soil Moisture Over Time")
    plt.ylabel("Moisture (%)")

    # Water distance graph
    plt.subplot(2,1,2)
    plt.plot(timestamps, water)
    plt.title("Water Level Distance Over Time")
    plt.ylabel("Distance (cm)")

    plt.tight_layout()
    plt.show()

# --------------------------
# BUTTONS
# --------------------------
history_btn = tk.Button(root,
                        text="View History",
                        font=("Arial", 14),
                        bg="#74b9ff", fg="white",
                        command=open_history)
history_btn.pack(pady=10)

graph_btn = tk.Button(root,
                      text="View Graphs",
                      font=("Arial", 14),
                      bg="#55efc4", fg="black",
                      command=open_graphs)
graph_btn.pack(pady=10)

root.mainloop()
