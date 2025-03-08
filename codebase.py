import tkinter as tk
from tkinter import ttk, filedialog
from ttkthemes import ThemedTk
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import mplcursors
import json
import os

# Global variables
points = []
adjusted_points = []
input_points = []
current_theme = "arc"


# Traverse adjustment functions
def adjust_open_traverse(points):
    return points.copy() if len(points) >= 2 else points


def adjust_closed_traverse(points):
    if len(points) < 3:
        return points
    delta_e = sum(p2[0] - p1[0] for p1, p2 in zip(points[:-1], points[1:])) + (points[0][0] - points[-1][0])
    delta_n = sum(p2[1] - p1[1] for p1, p2 in zip(points[:-1], points[1:])) + (points[0][1] - points[-1][1])
    total_perimeter = sum(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) for p1, p2 in zip(points[:-1], points[1:])) + \
                      math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
    if total_perimeter == 0:
        return points
    adjusted = [points[0]]
    cumulative_dist = 0
    for i in range(1, len(points)):
        dist = math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        cumulative_dist += dist
        correction_e = -delta_e * (cumulative_dist / total_perimeter)
        correction_n = -delta_n * (cumulative_dist / total_perimeter)
        adjusted.append((points[i][0] + correction_e, points[i][1] + correction_n))
    return adjusted


def bearing_to_azimuth(bearing_str):
    try:
        bearing_str = bearing_str.upper().replace(" ", "")
        if not bearing_str:
            raise ValueError("Bearing cannot be empty.")
        try:
            return float(bearing_str)
        except ValueError:
            if not ("N" in bearing_str or "S" in bearing_str) or not ("E" in bearing_str or "W" in bearing_str):
                raise ValueError("Invalid format. Use e.g., 'N60E'.")
            angle = float(bearing_str[1:-1])
            if angle < 0 or angle > 90:
                raise ValueError("Angle must be 0-90°.")
            if "N" in bearing_str and "E" in bearing_str:
                return angle
            elif "S" in bearing_str and "E" in bearing_str:
                return 180 - angle
            elif "S" in bearing_str and "W" in bearing_str:
                return 180 + angle
            elif "N" in bearing_str and "W" in bearing_str:
                return 360 - angle
            raise ValueError("Invalid direction.")
    except ValueError as e:
        raise ValueError(str(e))


# Calculate Area (Shoelace Formula)
def calculate_area(points):
    if len(points) < 3:
        return 0
    area = 0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2


# Update Graph
def update_graph():
    ax.clear()
    if points:
        eastings, northings = zip(*points)
        eastings = np.array(eastings)
        northings = np.array(northings)
        ax.plot(eastings, northings, 'bo-', label="Original Traverse", alpha=0.5)
        scatter_orig = ax.scatter(eastings, northings, color="blue", label="Original Points")

        if adjusted_points:
            adj_eastings, adj_northings = zip(*adjusted_points)
            ax.plot(adj_eastings + (adj_eastings[0],), adj_northings + (adj_northings[0],),
                    'r--', label="Adjusted Traverse", alpha=0.7)
            scatter_adj = ax.scatter(adj_eastings, adj_northings, color="red", label="Adjusted Points")

        for i, (e, n) in enumerate(points):
            ax.annotate(f"P{i + 1}", (e, n), xytext=(5, 5), textcoords="offset points")

        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.set_title("Traverse Survey")
        ax.grid(True, linestyle="--", alpha=0.7)
        ax.legend()

        cursor = mplcursors.cursor([scatter_orig] + ([scatter_adj] if adjusted_points else []), hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"P{sel.index + 1}: ({points[sel.index][0]:.2f}, {points[sel.index][1]:.2f})" if sel.artist == scatter_orig
            else f"Adj P{sel.index + 1}: ({adjusted_points[sel.index][0]:.2f}, {adjusted_points[sel.index][1]:.2f})"))

        canvas.draw_idle()


# Compute Traverse
def compute_traverse():
    global points, adjusted_points
    points.clear()
    adjusted_points.clear()
    result_label.config(text="Computing...")
    root.update_idletasks()
    try:
        if not input_points:
            raise ValueError("No points entered.")
        easting = float(input_points[0][0] or 0)
        northing = float(input_points[0][1] or 0)
        points.append((easting, northing))
        for i, (_, _, bearing_str, distance_str) in enumerate(input_points):
            easting = points[-1][0] if i > 0 else easting
            northing = points[-1][1] if i > 0 else northing
            bearing_str = bearing_str or ""
            distance = float(distance_str or 0)
            if not bearing_str and i != 0:
                continue
            if distance <= 0 and i != 0:
                raise ValueError(f"Distance must be positive at point {i + 1}.")
            azimuth = bearing_to_azimuth(bearing_str)
            delta_e = distance * math.sin(math.radians(azimuth))
            delta_n = distance * math.cos(math.radians(azimuth))
            new_easting = easting + delta_e
            new_northing = northing + delta_n
            if i != 0:
                points.append((new_easting, new_northing))

        traverse_type = traverse_var.get()
        adjusted_points = adjust_open_traverse(points) if traverse_type == "Open" else adjust_closed_traverse(points)
        update_graph()
        result_label.config(text=f"Computed {len(points)} points.")
    except ValueError as e:
        result_label.config(text=f"Error: {str(e)}")


# Calculate Area
def compute_area():
    if traverse_var.get() != "Closed" or not adjusted_points:
        result_label.config(text="Area calculation requires a closed traverse.")
        return
    area = calculate_area(adjusted_points)
    result_label.config(text=f"Area: {area:.2f} sq.m")


# Add Point
def add_point():
    try:
        easting = entry_easting.get()
        northing = entry_northing.get()
        bearing = entry_bearing.get()
        distance = entry_distance.get()
        if bearing and float(distance or 0) < 0:
            raise ValueError("Distance must be positive.")
        input_points.append((easting, northing, bearing, distance))
        tree.insert("", "end", values=(easting, northing, bearing, distance))
        entry_easting.delete(0, tk.END)
        entry_northing.delete(0, tk.END)
        entry_bearing.delete(0, tk.END)
        entry_distance.delete(0, tk.END)
        result_label.config(text=f"Added point {len(input_points)}")
    except ValueError as e:
        result_label.config(text=f"Error: {str(e)}")


# Remove Last Point
def remove_point():
    if input_points:
        input_points.pop()
        tree.delete(tree.get_children()[-1])
        result_label.config(text=f"Removed last point. {len(input_points)} points remain.")


# Save Project
def save_project():
    if not input_points:
        result_label.config(text="No points to save.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON files", "*.json")],
                                             title="Save Project")
    if file_path:
        try:
            with open(file_path, 'w') as f:
                json.dump({"traverse_type": traverse_var.get(), "points": input_points}, f, indent=4)
            result_label.config(text=f"Saved to {os.path.basename(file_path)}")
        except Exception as e:
            result_label.config(text=f"Save error: {str(e)}")


# Load Project
def load_project():
    global input_points
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Load Project")
    if file_path:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            input_points = data["points"]
            traverse_var.set(data["traverse_type"])
            tree.delete(*tree.get_children())
            for point in input_points:
                tree.insert("", "end", values=point)
            points.clear()
            adjusted_points.clear()
            update_graph()
            result_label.config(text=f"Loaded {os.path.basename(file_path)}")
        except Exception as e:
            result_label.config(text=f"Load error: {str(e)}")


# Delete Project
def delete_project():
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title="Delete Project")
    if file_path:
        try:
            os.remove(file_path)
            result_label.config(text=f"Deleted {os.path.basename(file_path)}")
        except Exception as e:
            result_label.config(text=f"Delete error: {str(e)}")


# Clear All
def clear_graph():
    global points, adjusted_points, input_points
    points.clear()
    adjusted_points.clear()
    input_points.clear()
    tree.delete(*tree.get_children())
    ax.clear()
    canvas.draw()
    result_label.config(text="Ready")


# Toggle Theme
def toggle_theme():
    global current_theme
    current_theme = "equilux" if current_theme == "arc" else "arc"
    root.set_theme(current_theme)
    toggle_button.config(text=f"{'Light' if current_theme == 'equilux' else 'Dark'} Mode")
    style.configure("TFrame", background="#f0f0f0" if current_theme == "arc" else "#2e2e2e")
    update_graph()


# GUI Setup
root = ThemedTk(theme="arc")
root.title("Survey Calculator")
root.geometry("1200x800")
root.resizable(True, True)

style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 12))
style.configure("TButton", font=("Helvetica", 12, "bold"), padding=8)
style.configure("TFrame", background="#f0f0f0", borderwidth=1, relief="flat")
style.configure("Treeview", font=("Helvetica", 11), rowheight=25)
style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

# Main Layout
sidebar = ttk.Frame(root, padding="10", style="TFrame")
sidebar.pack(side=tk.LEFT, fill="y")

graph_frame = ttk.LabelFrame(root, text="Visualization", padding="10")
graph_frame.pack(side=tk.RIGHT, fill="both", expand=True)

# Sidebar Content
header = ttk.Label(sidebar, text="Survey Calculator", font=("Helvetica", 16, "bold"))
header.pack(pady=(0, 20))

input_frame = ttk.LabelFrame(sidebar, text="Add Point", padding="10")
input_frame.pack(fill="x", pady=5)

# Explicitly define Entry widgets
entry_easting = ttk.Entry(input_frame)
entry_northing = ttk.Entry(input_frame)
entry_bearing = ttk.Entry(input_frame)
entry_distance = ttk.Entry(input_frame)

ttk.Label(input_frame, text="Easting (m)").grid(row=0, column=0, padx=5, pady=5, sticky="w")
entry_easting.grid(row=0, column=1, padx=5, pady=5)
ttk.Label(input_frame, text="Northing (m)").grid(row=0, column=2, padx=5, pady=5, sticky="w")
entry_northing.grid(row=0, column=3, padx=5, pady=5)
ttk.Label(input_frame, text="Bearing (e.g., N60E)").grid(row=1, column=0, padx=5, pady=5, sticky="w")
entry_bearing.grid(row=1, column=1, padx=5, pady=5)
ttk.Label(input_frame, text="Distance (m)").grid(row=1, column=2, padx=5, pady=5, sticky="w")
entry_distance.grid(row=1, column=3, padx=5, pady=5)

ttk.Button(input_frame, text="Add", command=add_point).grid(row=2, column=0, columnspan=4, pady=10)

display_frame = ttk.LabelFrame(sidebar, text="Points", padding="10")
display_frame.pack(fill="both", expand=True, pady=5)
tree = ttk.Treeview(display_frame, columns=("Easting", "Northing", "Bearing", "Distance"), show="headings", height=8)
for col, text in zip(("Easting", "Northing", "Bearing", "Distance"),
                     ("Easting (m)", "Northing (m)", "Bearing", "Distance (m)")):
    tree.heading(col, text=text)
    tree.column(col, width=80, anchor="center")
tree.pack(fill="both", expand=True)
scrollbar = ttk.Scrollbar(display_frame, orient="vertical", command=tree.yview)
scrollbar.pack(side="right", fill="y")
tree.configure(yscrollcommand=scrollbar.set)

traverse_frame = ttk.LabelFrame(sidebar, text="Traverse Type", padding="10")
traverse_frame.pack(fill="x", pady=5)
traverse_var = tk.StringVar(value="Open")
ttk.Radiobutton(traverse_frame, text="Open", variable=traverse_var, value="Open").pack(side="left", padx=10)
ttk.Radiobutton(traverse_frame, text="Closed", variable=traverse_var, value="Closed").pack(side="left", padx=10)

action_frame = ttk.Frame(sidebar, padding="10")
action_frame.pack(fill="x", pady=5)
ttk.Button(action_frame, text="Compute", command=compute_traverse).pack(side="left", padx=5)
ttk.Button(action_frame, text="Area", command=compute_area).pack(side="left", padx=5)
ttk.Button(action_frame, text="Save", command=save_project).pack(side="left", padx=5)
ttk.Button(action_frame, text="Load", command=load_project).pack(side="left", padx=5)
ttk.Button(action_frame, text="Delete", command=delete_project).pack(side="left", padx=5)
ttk.Button(action_frame, text="Clear", command=clear_graph).pack(side="left", padx=5)

toggle_button = ttk.Button(sidebar, text="Dark Mode", command=toggle_theme)
toggle_button.pack(pady=10)

result_frame = ttk.LabelFrame(sidebar, text="Results", padding="10")
result_frame.pack(fill="x", pady=5)
result_label = ttk.Label(result_frame, text="Ready", wraplength=300, justify="center")
result_label.pack()

# Graph
fig, ax = plt.subplots(figsize=(8, 8))
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)
toolbar = NavigationToolbar2Tk(canvas, graph_frame)
toolbar.pack(fill="x")

root.protocol("WM_DELETE_WINDOW",
              lambda: (canvas.mpl_disconnect(ax._cid) if hasattr(ax, '_cid') else None, root.destroy())[1])
root.mainloop()
