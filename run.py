import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# -------------------------------
# Open SQLite File
# -------------------------------
def open_db():
    global conn, cursor
    
    filepath = filedialog.askopenfilename(
        title="Select SQLite Database",
        filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")]
    )

    if filepath:
        db_path.set(filepath)
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            load_tables()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open database:\n{e}")


# -------------------------------
# Load All Tables
# -------------------------------
def load_tables():
    table_list.delete(*table_list.get_children())

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for t in tables:
        table_list.insert("", tk.END, values=[t[0]])


# -------------------------------
# Load Columns + Rows of Selected Table
# -------------------------------
def show_table_data(event):
    selected = table_list.selection()
    if not selected:
        return
    
    table_name = table_list.item(selected[0], "values")[0]

    # Clear old data
    for col in data_view.get_children():
        data_view.delete(col)

    data_view["columns"] = []
    data_view["show"] = "headings"

    try:
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]

        # Set columns in TreeView
        data_view["columns"] = columns
        for col in columns:
            data_view.heading(col, text=col)
            data_view.column(col, width=120)

        # Fetch rows
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()

        for row in rows:
            data_view.insert("", tk.END, values=row)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to read table:\n{e}")


# -------------------------------
# MAIN GUI
# -------------------------------
root = tk.Tk()
root.title("SQLite Viewer (Tkinter)")
root.geometry("900x600")

db_path = tk.StringVar()

# Top Frame
top_frame = tk.Frame(root)
top_frame.pack(fill="x", pady=10)

tk.Label(top_frame, text="Database:").pack(side="left", padx=5)
tk.Entry(top_frame, textvariable=db_path, width=50).pack(side="left", padx=5)
tk.Button(top_frame, text="Browse", command=open_db).pack(side="left")

# Table List
table_frame = tk.LabelFrame(root, text="Tables", padx=5, pady=5)
table_frame.pack(side="left", fill="y")

table_list = ttk.Treeview(table_frame, columns=["Table"], show="headings", height=20)
table_list.heading("Table", text="Table Name")
table_list.column("Table", width=150)
table_list.bind("<<TreeviewSelect>>", show_table_data)
table_list.pack(side="left", fill="y")

# Data View
data_frame = tk.LabelFrame(root, text="Table Data", padx=5, pady=5)
data_frame.pack(side="right", fill="both", expand=True)

data_view = ttk.Treeview(data_frame)
data_view.pack(fill="both", expand=True)

root.mainloop()
