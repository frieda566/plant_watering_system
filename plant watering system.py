import serial
import sqlite3
import threading
import queue
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------- CONFIG ----------------
SERIAL_PORT = "/dev/cu.usbmodem1101"  # change to your port
BAUD_RATE = 9600

# ---------------- DATABASE ----------------
conn = sqlite3.connect("plant_data.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS readings (
    timestamp TEXT,
    moisture INTEGER,
    temperature INTEGER,
    humidity INTEGER
)
""")
conn.commit()

# ---------------- THREAD-SAFE QUEUE ----------------
data_queue = queue.Queue()

# ---------------- SERIAL READER THREAD ----------------
def serial_reader():
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print("Serial error:", e)
        return

    latest = {"moisture": 0, "temperature": 0, "humidity": 0}
    while True:
        try:
            line = arduino.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if line.startswith("MOISTURE:"):
                latest["moisture"] = int(line.split(":")[1])
            elif line.startswith("TEMPERATURE:"):
                latest["temperature"] = int(line.split(":")[1])
            elif line.startswith("HUMIDITY:"):
                latest["humidity"] = int(line.split(":")[1])
                # once all three are present, push to queue & save DB
                data_queue.put(latest.copy())
                cur.execute(
                    "INSERT INTO readings VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(),
                     latest["moisture"],
                     latest["temperature"],
                     latest["humidity"])
                )
                conn.commit()
        except Exception as e:
            print("Serial error:", e)

threading.Thread(target=serial_reader, daemon=True).start()

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Plant Monitoring System")
root.geometry("700x600")
root.configure(bg="#c8f7c5")

title = tk.Label(root, text="🌱 Plant Monitoring System",
                 font=("Arial", 22, "bold"),
                 bg="#c8f7c5", fg="#0652DD")
title.pack(pady=10)

# Container for pages
container = tk.Frame(root, bg="#c8f7c5")
container.pack(fill="both", expand=True)

latest_data = {"moisture": 0, "temperature": 0, "humidity": 0}

# ---------------- PAGES ----------------
# --- Dashboard Page ---
dashboard_frame = tk.Frame(container, bg="#c8f7c5")
moisture_label = tk.Label(dashboard_frame, text="Soil Moisture: --%",
                          font=("Arial", 18), bg="#c8f7c5")
temperature_label = tk.Label(dashboard_frame, text="Temperature: --°C",
                             font=("Arial", 18), bg="#c8f7c5")
humidity_label = tk.Label(dashboard_frame, text="Humidity: --%",
                          font=("Arial", 18), bg="#c8f7c5")
moisture_label.pack(pady=5)
temperature_label.pack(pady=5)
humidity_label.pack(pady=5)

# --- History Page ---
history_frame = tk.Frame(container, bg="#c8f7c5")
history_table = ttk.Treeview(history_frame,
                             columns=("time","moisture","temp","hum"),
                             show="headings")
history_table.heading("time", text="Timestamp")
history_table.heading("moisture", text="Moisture (%)")
history_table.heading("temp", text="Temperature (°C)")
history_table.heading("hum", text="Humidity (%)")
history_table.pack(fill="both", expand=True)

# --- Graphs Page ---
graphs_frame = tk.Frame(container, bg="#c8f7c5")

# Global references for live graph update
canvas_widget = None
fig = None
ax1 = ax2 = ax3 = None

# ---------------- PAGE SWITCHING ----------------
def show_frame(frame):
    for f in (dashboard_frame, history_frame, graphs_frame):
        f.pack_forget()
    frame.pack(fill="both", expand=True)

# ---------------- DASHBOARD UPDATE ----------------
def update_dashboard():
    # read from queue
    try:
        while not data_queue.empty():
            latest = data_queue.get_nowait()
            latest_data.update(latest)
    except queue.Empty:
        pass

    moisture_label.config(text=f"Soil Moisture: {latest_data['moisture']}%")
    temperature_label.config(text=f"Temperature: {latest_data['temperature']}°C")
    humidity_label.config(text=f"Humidity: {latest_data['humidity']}%")
    root.after(1000, update_dashboard)

# ---------------- HISTORY UPDATE ----------------
def update_history():
    for row in history_table.get_children():
        history_table.delete(row)
    cur.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 300")
    for row in cur.fetchall():
        history_table.insert("", "end", values=row)

# ---------------- GRAPHS UPDATE ----------------
def init_graphs():
    """Initialize matplotlib figure & axes once."""
    global fig, ax1, ax2, ax3, canvas_widget
    fig, (ax1, ax2, ax3) = plt.subplots(3,1,figsize=(7,6))
    fig.tight_layout(pad=3)

    canvas_widget = FigureCanvasTkAgg(fig, master=graphs_frame)
    canvas_widget.draw()
    canvas_widget.get_tk_widget().pack(fill="both", expand=True)
    update_graphs()  # start live updates

def update_graphs():
    global fig, ax1, ax2, ax3, canvas_widget
    # Clear previous plots
    ax1.cla()
    ax2.cla()
    ax3.cla()

    # Fetch all readings
    cur.execute("SELECT timestamp, moisture, temperature, humidity FROM readings ORDER BY timestamp ASC")
    rows = cur.fetchall()
    if len(rows) == 0:
        ax1.set_title("No data yet")
        ax2.set_title("No data yet")
        ax3.set_title("No data yet")
    else:
        timestamps = [datetime.fromisoformat(r[0]) for r in rows]
        moisture = [r[1] for r in rows]
        temperature = [r[2] for r in rows]
        humidity = [r[3] for r in rows]

        ax1.plot(timestamps, moisture, color='blue')
        ax1.set_title("Soil Moisture Over Time")
        ax1.set_ylabel("%")

        ax2.plot(timestamps, temperature, color='red')
        ax2.set_title("Temperature Over Time")
        ax2.set_ylabel("°C")

        ax3.plot(timestamps, humidity, color='green')
        ax3.set_title("Humidity Over Time")
        ax3.set_ylabel("%")

    canvas_widget.draw()
    root.after(3000, update_graphs)  # update every 3 seconds

# ---------------- BUTTONS ----------------
button_frame = tk.Frame(root, bg="#c8f7c5")
button_frame.pack(pady=10)
tk.Button(button_frame, text="Dashboard", bg="#74b9ff", fg="white",
          command=lambda: show_frame(dashboard_frame)).grid(row=0,column=0,padx=5)
tk.Button(button_frame, text="History", bg="#74b9ff", fg="white",
          command=lambda:[show_frame(history_frame), update_history()]).grid(row=0,column=1,padx=5)
tk.Button(button_frame, text="Graphs", bg="#55efc4", fg="black",
          command=lambda:[show_frame(graphs_frame), init_graphs()]).grid(row=0,column=2,padx=5)

# ---------------- STARTUP ----------------
show_frame(dashboard_frame)
update_dashboard()
root.mainloop()
