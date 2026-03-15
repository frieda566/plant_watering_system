import tkinter as tk
from datetime import datetime, timedelta
from ui_components import create_styled_button


# Main function to display plant health interface
def show_plant_health(app):
    # Clear previous content in root window
    for widget in app.root.winfo_children():
        widget.destroy()
    # Main frame with background color
    frame = tk.Frame(app.root, bg=app.colors["cream"])
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    # Title label
    tk.Label(
        frame,
        text="🌱 Weekly Plant Health",
        font=("Helvetica", 20, "bold"),
        bg=app.colors["cream"],
        fg=app.colors["dark_green"]
    ).pack(pady=10)
    # Search bar label
    tk.Label(
        frame,
        text="Search your plant:",
        bg=app.colors["cream"],
        fg=app.colors["dark_green"],
        font=("Helvetica", 14, "bold")
    ).pack(pady=(5, 2))

    # Search variable
    app.health_search_var = tk.StringVar()
    app.health_search_var.trace("w", lambda *args: filter_health_plants(app))

    # Styled search bar
    search_entry = tk.Entry(
        frame,
        textvariable=app.health_search_var,
        width=30,
        font=("Helvetica", 11),
        bg=app.colors["lime"],
        fg=app.colors["dark_green"],
        relief="flat",
        bd=4,
        insertbackground=app.colors["dark_green"]
    )
    search_entry.pack(pady=5)
    search_entry.focus_set()

    # Results container
    app.results_frame = tk.Frame(
        frame,
        bg=app.colors["cream"],
        padx=5,
        pady=5
    )
    app.results_frame.pack(pady=5)

    create_styled_button(
        frame,
        "← Back to Menu",
        app.setup_main_menu
    )


# Filter plants based on search query
def filter_health_plants(app):
    query = app.health_search_var.get().lower()

    # Clear previous results
    for widget in app.results_frame.winfo_children():
        widget.destroy()

    if not query:
        return
    # find matches in plant lexicon (max 6 results)
    matches = [
                  name for name in app.lexicon_df["Plant Name"]
                  if query in name.lower()
              ][:6]

    for plant in matches:
        # label for each search result
        lbl = tk.Label(
            app.results_frame,
            text=plant,
            font=("Helvetica", 11),
            bg=app.colors["sage"],
            fg=app.colors["dark_green"],
            anchor="w",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        lbl.pack(fill="x", pady=1)

        # Click event
        lbl.bind(
            "<Button-1>",
            lambda e, p=plant: generate_health_report(app, p, app.results_frame.master)
        )

        # Hover effect
        def on_enter(e, widget=lbl):
            widget.config(bg=app.colors["lime"])

        def on_leave(e, widget=lbl):
            widget.config(bg=app.colors["sage"])

        lbl.bind("<Enter>", on_enter)
        lbl.bind("<Leave>", on_leave)


# Retrieve last 7 days of sensor data
def get_last_week_data(app):
    history = app.load_history()

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    # Filter data for the last week and valid measurements
    week_data = [
        d for d in history
        if datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S") >= week_ago
           and d["temperature"] > 0
           and d["humidity"] > 0
           and d["moisture"] > 0
    ]

    return week_data


# Get optimal ranges for a given plant
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


# Analyze the week's data against optimal ranges
def analyze_week(app, week_data, optimal):
    avg_temp = sum(d["temperature"] for d in week_data) / len(week_data)
    avg_hum = sum(d["humidity"] for d in week_data) / len(week_data)
    avg_moist = sum(d["moisture"] for d in week_data) / len(week_data)

    return [
        f"🌡 Temperature ({avg_temp:.1f}°C): {compare_value(avg_temp, *optimal['temperature'])}",
        f"💧 Humidity ({avg_hum:.1f}%): {compare_value(avg_hum, *optimal['humidity'])}",
        f"🌱 Soil Moisture ({avg_moist:.1f}%): {compare_value(avg_moist, *optimal['moisture'])}"
    ]


# Generate detailed health report for a plant
def generate_health_report(app, plant_name, parent):
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
    # Handle missing weekly data
    if not week_data:
        tk.Label(
            parent,
            text="No weekly data available yet.",
            bg=app.colors["cream"],
            fg=app.colors["dark_green"]
        ).pack()

        return
    # Analyze week and prepare feedback
    feedback = analyze_week(app, week_data, optimal)
    # Frame to hold report
    report_frame = tk.Frame(
        parent,
        bg=app.colors["sage"],
        padx=15,
        pady=15
    )

    report_frame.pack(fill="x", pady=20)
    # Report title
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


# Compare a value to min/max and return feedback
def compare_value(value, min_val, max_val):
    if value < min_val:
        return "⚠ Too low"

    elif value > max_val:
        return "⚠ Too high"

    return "✔ Optimal"
