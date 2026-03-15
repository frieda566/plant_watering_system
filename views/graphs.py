import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ui_components import create_styled_button


def show_graphs(app):
    # Display graphs for moisture, temperature, and humidity over time
    # Clear current UI
    app.clear_window()
    # Main frame
    frame = tk.Frame(app.root, bg=app.colors["cream"])
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    # Title label
    tk.Label(
        frame,
        text="📈 Graphs",
        font=("Helvetica", 20, "bold"),
        bg=app.colors["cream"],
        fg=app.colors["dark_green"]
    ).pack(pady=10)

    # ---------------- Notebook Style ----------------
    style = ttk.Style()
    style.theme_use("clam")  # Needed for color customization

    style.configure(
        "CustomNotebook.TNotebook",
        background=app.colors["cream"],
        borderwidth=0
    )
    style.configure(
        "CustomNotebook.TNotebook.Tab",
        background=app.colors["sage"],
        foreground=app.colors["dark_green"],
        padding=[10, 5]
    )
    style.map(
        "CustomNotebook.TNotebook.Tab",
        background=[("selected", app.colors["lime"])],
        foreground=[("selected", app.colors["dark_green"])]
    )

    # ---- Load History Data ----
    history = app.load_history()
    if not history:
        tk.Label(
            frame,
            text="No data available yet!",
            bg=app.colors["cream"],
            fg=app.colors["dark_green"],
            font=("Helvetica", 14)
        ).pack()
        create_styled_button(frame, "← Back to Menu", app.setup_main_menu)
        return

    # Extract values
    timestamps = [item["timestamp"] for item in history]
    moisture = [item["moisture"] for item in history]
    temperature = [item["temperature"] for item in history]
    humidity = [item["humidity"] for item in history]

    # ---------- Notebook (Tabs) ----------
    notebook = ttk.Notebook(frame, style="CustomNotebook.TNotebook")
    notebook.pack(fill="both", expand=True)

    tab1 = tk.Frame(notebook, bg=app.colors["cream"])
    tab2 = tk.Frame(notebook, bg=app.colors["cream"])
    tab3 = tk.Frame(notebook, bg=app.colors["cream"])

    notebook.add(tab1, text="Moisture")
    notebook.add(tab2, text="Temperature")
    notebook.add(tab3, text="Humidity")

    # ----- Helper function to draw graph -----
    def draw_graph(tab, y_values, ylabel, title):
        fig = plt.Figure(figsize=(7, 4), dpi=100)
        ax = fig.add_subplot(111)

        # Plot line
        ax.plot(timestamps, y_values, marker="o", linewidth=2, color=app.colors["sage"])

        # Title
        ax.set_title(title, fontsize=14, color=app.colors["dark_green"], fontweight="bold")

        # Labels
        ax.set_ylabel(ylabel, fontsize=12, color=app.colors["brown"])
        ax.set_xlabel("Time", fontsize=12, color=app.colors["brown"])

        # Ticks
        ax.tick_params(axis="x", rotation=45, colors=app.colors["brown"])
        ax.tick_params(axis="y", colors=app.colors["brown"])

        # Frame / rectangle around the plot
        for spine in ax.spines.values():
            spine.set_color(app.colors["dark_green"])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

    # Draw each graph
    draw_graph(tab1, moisture, "Moisture (%)", "Moisture Over Time")
    draw_graph(tab2, temperature, "Temperature (°C)", "Temperature Over Time")
    draw_graph(tab3, humidity, "Humidity (%)", "Humidity Over Time")

    # Back button
    create_styled_button(frame, "← Back to Menu", app.setup_main_menu)
