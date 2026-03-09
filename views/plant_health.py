import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from ui_components import create_styled_button


def show_plant_health(app):

    for widget in app.root.winfo_children():
        widget.destroy()

    frame = tk.Frame(app.root, bg=app.colors["cream"])
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(
        frame,
        text="🌱 Weekly Plant Health",
        font=("Helvetica", 20, "bold"),
        bg=app.colors["cream"],
        fg=app.colors["dark_green"]
    ).pack(pady=10)

    tk.Label(
        frame,
        text="Select your plant:",
        bg=app.colors["cream"],
        fg=app.colors["dark_green"],
        font=("Helvetica", 14)
    ).pack(pady=5)

    plant_var = tk.StringVar()

    plant_names = app.lexicon_df["Plant Name"].tolist()

    dropdown = ttk.Combobox(
        frame,
        textvariable=plant_var,
        values=plant_names,
        state="readonly",
        width=30
    )
    dropdown.pack(pady=10)

    create_styled_button(
        frame,
        "Generate Health Report",
        lambda: generate_health_report(app, plant_var.get(), frame)
    )

    create_styled_button(
        frame,
        "← Back to Menu",
        app.setup_main_menu
    )


def get_last_week_data(app):

    history = app.load_history()

    now = datetime.now()
    week_ago = now - timedelta(days=7)

    week_data = [
        d for d in history
        if datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") >= week_ago
        and d["temperature"] > 0
        and d["humidity"] > 0
        and d["moisture"] > 0
    ]

    return week_data


def get_optimal_ranges(app, plant_name):

    plant_name_clean = plant_name.strip().lower()

    row = app.health_df[
        app.health_df["Plant Name"].str.strip().str.lower() == plant_name_clean
    ]

    if row.empty:
        return None

    row = row.iloc[0]

    return {
        "temperature": (row["Temperature Min"], row["Temperature Max"]),
        "humidity": (row["Humidity Min"], row["Humidity Max"]),
        "moisture": (30, 60)
    }


def analyze_week(app, week_data, optimal):

    avg_temp = sum(d["temperature"] for d in week_data) / len(week_data)
    avg_hum = sum(d["humidity"] for d in week_data) / len(week_data)
    avg_moist = sum(d["moisture"] for d in week_data) / len(week_data)

    return [
        f"🌡 Temperature ({avg_temp:.1f}°C): {compare_value(avg_temp, *optimal['temperature'])}",
        f"💧 Humidity ({avg_hum:.1f}%): {compare_value(avg_hum, *optimal['humidity'])}",
        f"🌱 Soil Moisture ({avg_moist:.1f}%): {compare_value(avg_moist, *optimal['moisture'])}"
    ]


def generate_health_report(app, plant_name, parent):

    if not plant_name:
        return

    plant_row = app.lexicon_df[
        app.lexicon_df["Plant Name"] == plant_name
    ].iloc[0]

    optimal = get_optimal_ranges(app, plant_name)
    week_data = get_last_week_data(app)

    if not optimal:

        tk.Label(
            parent,
            text="No health reference data available for this plant.",
            bg=app.colors["cream"],
            fg=app.colors["dark_green"]
        ).pack()

        return

    if not week_data:

        tk.Label(
            parent,
            text="No weekly data available yet.",
            bg=app.colors["cream"],
            fg=app.colors["dark_green"]
        ).pack()

        return

    feedback = analyze_week(app, week_data, optimal)

    report_frame = tk.Frame(
        parent,
        bg=app.colors["sage"],
        padx=15,
        pady=15
    )

    report_frame.pack(fill="x", pady=20)

    tk.Label(
        report_frame,
        text=f"Weekly Health Report for {plant_name}",
        font=("Helvetica", 16, "bold"),
        bg=app.colors["sage"],
        fg=app.colors["dark_green"]
    ).pack(pady=5)

    for line in feedback:

        tk.Label(
            report_frame,
            text=line,
            bg=app.colors["sage"],
            fg=app.colors["dark_green"],
            font=("Helvetica", 12),
            anchor="w"
        ).pack(fill="x")


def compare_value(value, min_val, max_val):

    if value < min_val:
        return "⚠ Too low"

    elif value > max_val:
        return "⚠ Too high"

    return "✔ Optimal"