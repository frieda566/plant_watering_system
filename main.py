import tkinter as tk
from app import PlantMonitoringApp

# Start the interface
if __name__ == "__main__":
    root = tk.Tk()
    app = PlantMonitoringApp(root)
    root.mainloop()
