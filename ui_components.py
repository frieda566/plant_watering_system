import tkinter as tk
from tkinter import ttk


def create_styled_button(parent, text, command):
    # Create a reusable, styled button with custom colors and padding
    outer = tk.Frame(parent, bg="#89725B")
    outer.pack(pady=8)

    inner = tk.Frame(outer, bg="#B7CA79")
    inner.pack(padx=3, pady=3)

    btn = tk.Button(
        inner,
        text=text,
        font=("Helvetica", 14, "bold"),
        bg="#B7CA79",
        fg="#677E52",
        relief="flat",
        bd=0,
        padx=20,
        pady=12,
        cursor="hand2",
        command=command
    )

    btn.pack()

    return btn


def create_styled_scrollbar(parent):
    # Create a reusable, vertically oriented scrollbar with custom styling
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Custom.Vertical.TScrollbar",
        background="#B0CC99"
    )

    return ttk.Scrollbar(parent, orient="vertical", style="Custom.Vertical.TScrollbar")
