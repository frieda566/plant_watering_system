import tkinter as tk
from datetime import datetime
from ui_components import create_styled_button


def show_dashboard(app):
    """Display live dashboard with soil moisture, temperature, and humidity."""
    for widget in app.root.winfo_children():
        widget.destroy()

    frame = tk.Frame(app.root, bg=app.colors["cream"])
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(
        frame,
        text="📊 Dashboard",
        font=("Helvetica", 20, "bold"),
        bg=app.colors["cream"],
        fg=app.colors["dark_green"]
    ).pack(pady=20)

    # Live data labels container (placed in center)
    content = tk.Frame(frame, bg=app.colors["cream"])
    content.place(relx=0.5, rely=0.5, anchor="center")

    # Live data labels
    app.moisture_label = tk.Label(frame, text="Soil Moisture: --%",
                                  font=("Helvetica", 16, "bold"),
                                  bg=app.colors["cream"], fg=app.colors["brown"])
    app.temperature_label = tk.Label(frame, text="Temperature: --°C",
                                     font=("Helvetica", 16, "bold"),
                                     bg=app.colors["cream"], fg=app.colors["brown"])
    app.humidity_label = tk.Label(frame, text="Humidity: --%",
                                  font=("Helvetica", 16, "bold"),
                                  bg=app.colors["cream"], fg=app.colors["brown"])

    for lbl in (app.moisture_label, app.temperature_label, app.humidity_label):
        lbl.pack(pady=8)

    # Back button at bottom
    back_frame = tk.Frame(frame, bg=app.colors["cream"])
    back_frame.pack(side="bottom", pady=20)
    create_styled_button(back_frame, "← Back to Menu", app.setup_main_menu)

    update_dashboard(app)


def update_dashboard(app):
    """Update live readings every second."""
    if hasattr(app, "moisture_label") and app.moisture_label.winfo_exists():
        app.moisture_label.config(text=f"Soil Moisture: {app.latest_data['moisture']}%")
        app.temperature_label.config(text=f"Temperature: {app.latest_data['temperature']}°C")
        app.humidity_label.config(text=f"Humidity: {app.latest_data['humidity']}%")

        # Save daily reading at 2 PM
        app.save_daily_reading()

        # Schedule next update
        app.root.after(1000, lambda: update_dashboard(app))


def read_serial_loop(app):
    """Background thread reading Arduino messages."""
    while app.serial_running:
        try:
            line = app.serial.readline().decode().strip()
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
                app.latest_data = data

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                app.cur.execute(
                    "INSERT INTO readings (timestamp, moisture, temperature, humidity) VALUES (?, ?, ?, ?)",
                    (ts, data["moisture"], data["temperature"], data["humidity"])
                )
                app.conn.commit()

        except app.serial.SerialException:
            print("Lost connection to Arduino!")
            app.serial_running = False
            break

        except Exception as e:
            print("Serial error:", e)
