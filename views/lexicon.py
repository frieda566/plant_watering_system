import tkinter as tk
from tkinter import ttk, font
from ui_components import create_styled_button, create_styled_scrollbar


def show_lexicon(app):
    # Display the plant lexicon with a searchable list of plants
    # Clear current UI
    for widget in app.root.winfo_children():
        widget.destroy()

    # Main frame
    main_frame = tk.Frame(app.root, bg=app.colors["cream"])
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Header
    header_frame = tk.Frame(main_frame, bg=app.colors["cream"])
    header_frame.pack(fill="x", pady=(10, 0))

    title_font = font.Font(family="Helvetica", size=20, weight="bold")

    tk.Label(
        header_frame,
        text="🌿 Lexicon",
        font=title_font,
        bg=app.colors["cream"],
        fg=app.colors["dark_green"]
    ).pack()

    # ---------------- Search Bar ----------------
    app.search_var = tk.StringVar()
    app.search_var.trace("w", lambda *args: filter_plants(app))  # Updates as user types

    search_container = tk.Frame(main_frame, bg=app.colors["cream"])
    search_container.pack(pady=(10, 20))

    search_entry = tk.Entry(
        search_container,
        textvariable=app.search_var,
        width=50,
        font=("Helvetica", 12),
        bg=app.colors["lime"],
        fg=app.colors["dark_green"],
        relief="flat",
        bd=5,
        insertbackground=app.colors["dark_green"]
    )

    search_entry.pack(pady=5)

    # # ---------------- Scrollable Plant List ----------------
    app.scroll_container = tk.Frame(main_frame, bg=app.colors["cream"])
    app.scroll_container.pack(fill="both", expand=True)

    canvas = tk.Canvas(
        app.scroll_container,
        bg=app.colors["cream"],
        highlightthickness=0
    )

    scrollbar = create_styled_scrollbar(app.scroll_container)
    scrollbar.config(command=canvas.yview)

    canvas.configure(yscrollcommand=scrollbar.set)
    # Frame inside canvas to hold plant cards
    app.scroll_frame = tk.Frame(canvas, bg=app.colors["cream"])

    canvas_window = canvas.create_window(
        (0, 0),
        window=app.scroll_frame,
        anchor="nw"
    )

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Scroll behavior
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)

    app.scroll_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    # Render plant cards
    app.plant_cards = []

    for _, row in app.lexicon_df.iterrows():
        # Card container
        card = tk.Frame(
            app.scroll_frame,
            bg=app.colors["brown"],
            bd=0,
            relief="ridge"
        )

        card.pack(fill="x", pady=5, padx=5)
        # Inner frame for plant info and button
        inner = tk.Frame(
            card,
            bg=app.colors["sage"],
            padx=10,
            pady=10
        )

        inner.pack(fill="x", expand=True)

        inner.pack_propagate(False)
        inner.config(height=60)

        # Plant name label
        name_label = tk.Label(
            inner,
            text=row["Plant Name"],
            font=("Helvetica", 14, "bold"),
            bg=app.colors["sage"],
            fg=app.colors["dark_green"],
            anchor="w"
        )

        name_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Button border
        outer_btn = tk.Frame(inner, bg=app.colors["brown"])
        outer_btn.pack(side="right", padx=10)

        inner_btn = tk.Frame(outer_btn, bg=app.colors["lime"])
        inner_btn.pack(padx=3, pady=3)

        details_btn = tk.Button(
            inner_btn,
            text="Details",
            font=("Helvetica", 12, "bold"),
            bg=app.colors["lime"],
            fg=app.colors["dark_green"],
            relief="flat",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
            command=lambda r=row: show_lexicon_popup(app, r)
        )

        details_btn.pack()

        # Hover effects
        details_btn.bind(
            "<Enter>",
            lambda e, btn=details_btn, frame=inner_btn:
            (btn.config(bg=app.colors["sage"]),
             frame.config(bg=app.colors["sage"]))
        )

        details_btn.bind(
            "<Leave>",
            lambda e, btn=details_btn, frame=inner_btn:
            (btn.config(bg=app.colors["lime"]),
             frame.config(bg=app.colors["lime"]))
        )
        # Store cards for filtering
        app.plant_cards.append((card, row["Plant Name"].lower()))

    # Back button
    create_styled_button(
        main_frame,
        "← Back to Menu",
        app.setup_main_menu
    )


def filter_plants(app):
    # Filter displayed plant cards based on search query
    query = app.search_var.get().lower()

    for card, name in app.plant_cards:

        if query in name:
            card.pack(fill="x", pady=5, padx=5)
        else:
            card.pack_forget()


def show_lexicon_popup(app, row):
    # Display detailed information about a specific plant in a popup window
    popup = tk.Toplevel(app.root)

    popup.title(row["Plant Name"])
    popup.configure(bg=app.colors["cream"])
    popup.geometry("500x500")
    # Scrollable canvas
    canvas = tk.Canvas(
        popup,
        bg=app.colors["cream"],
        highlightthickness=0
    )

    scrollbar = create_styled_scrollbar(popup)

    scrollbar.config(command=canvas.yview)

    scroll_frame = tk.Frame(canvas, bg=app.colors["cream"])

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def add_info_line(parent, headline, value):
        # Helper function to add info lines with separators
        tk.Label(
            parent,
            text=headline,
            font=("Helvetica", 14, "bold"),
            bg=app.colors["cream"],
            fg=app.colors["dark_green"],
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(
            parent,
            text=value,
            font=("Helvetica", 12),
            bg=app.colors["cream"],
            fg=app.colors["dark_green"],
            anchor="w",
            justify="left",
            wraplength=450
        ).pack(fill="x", padx=20, pady=(0, 5))

        ttk.Separator(parent, orient="horizontal").pack(
            fill="x",
            padx=10,
            pady=5
        )

    # Add plant info fields
    add_info_line(scroll_frame, "🌞 Light Preferences:", row['Light Preferences'])
    add_info_line(scroll_frame, "💧 Watering:", row['Watering'])
    add_info_line(scroll_frame, "🪴 Soil Type / Drainage:", row.get('Soil Type/Drainage', 'N/A'))
    add_info_line(scroll_frame, "🌡️ Temp / Humidity:", row.get('Temp / Humidity', 'N/A'))
    add_info_line(scroll_frame, "📏 Height Growth:", row.get('Height Growth', 'N/A'))
    add_info_line(scroll_frame, "⚠️ Common Problems:", row.get('Common Problems', 'N/A'))
    add_info_line(scroll_frame, "🌱 Propagation:", row.get('Propagation', 'N/A'))
    add_info_line(scroll_frame, "☠️ Toxicity:", row.get('Toxicity', 'N/A'))
    # Close button
    create_styled_button(
        scroll_frame,
        "✓ Close",
        popup.destroy
    )
