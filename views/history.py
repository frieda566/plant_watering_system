import tkinter as tk
from tkinter import ttk

from ui_components import create_styled_button


def show_history(app):
    # Display the plant history in a styled table with a back button
    # Clear current UI
    app.clear_window()
    # Main frame
    frame = tk.Frame(app.root, bg=app.colors["cream"])
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title label
    tk.Label(frame, text="📜 History", font=("Helvetica", 20, "bold"),
             bg=app.colors["cream"], fg=app.colors["dark_green"]).pack(pady=10)

    # Treeview style
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Treeview.Heading",
        font=("Helvetica", 12, "bold"),
        foreground=app.colors["dark_green"],
        background=app.colors["sage"]
    )

    # History table
    table = ttk.Treeview(frame, columns=("time", "moisture", "temp", "hum"), show="headings")
    table.heading("time", text="Timestamp")
    table.heading("moisture", text="Moisture (%)")
    table.heading("temp", text="Temperature (°C)")
    table.heading("hum", text="Humidity (%)")
    table.pack(fill="both", expand=True)
    # Store table in app for later updates
    app.history_table = table
    # Tag for coloring text
    table.tag_configure("brown_text", foreground=app.colors["brown"])

    # Populate table from JSON file
    for row in app.load_history():  # load_history() reads plant_history.json
        table.insert("", "end", values=(row["timestamp"], row["moisture"], row["temperature"], row["humidity"]),
                     tags=("brown_text",))

    # Back button
    create_styled_button(frame, "← Back to Menu", app.setup_main_menu)


def update_history(app):
    # Refresh the history table every 3 seconds with updated JSON data
    if hasattr(app, "history_table") and app.history_table.winfo_exists():
        # Clear table
        for row in app.history_table.get_children():
            app.history_table.delete(row)
        # Re-populate from JSON (instead of DB)
        for row in app.load_history():
            app.history_table.insert("", "end",
                                     values=(row["timestamp"], row["moisture"], row["temperature"], row["humidity"]),
                                     tags=("brown_text",))
        # Refresh every 3 seconds
        app.root.after(3000, lambda: update_history(app))
