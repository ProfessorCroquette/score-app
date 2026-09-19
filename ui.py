"""Tkinter UI for the exam score calculator with inline editing."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from calc import (
    rank_students, summary, normalize_weights,
    SCHEMES, DEFAULT_SCHEME_NAME,
)
from excel import write_results


COMPONENTS = ["NHS", "PTS", "PAS"]                 # fixed components
EDITABLE = ["nis", "name"] + COMPONENTS            # cells the user can edit
COLUMNS = ["nis", "name"] + COMPONENTS + ["weighted", "grade"]

COL_LABELS = {
    "nis": "NIS",
    "name": "Name",
    "NHS": "NHS",
    "PTS": "PTS",
    "PAS": "PAS",
    "weighted": "Final",
    "grade": "Grade",
}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Exam Score Calculator")
        self.root.geometry("950x650")

        # {tree_item_id: {"nis": str, "name": str, "NHS": str, "PTS": str, "PAS": str}}
        self.rows = {}
        self.results = []
        self.summary_data = {}
        self.scheme_name = DEFAULT_SCHEME_NAME
        self._edit_widget = None       # currently open inline editor

        self.build_toolbar()
        self.build_table()
        self.build_weights()
        self.build_status()

    # ---------------- layout ----------------

    def build_toolbar(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="x")

        ttk.Button(frame, text="+ Add Row",
                   command=self.add_row).pack(side="left")
        ttk.Button(frame, text="Remove Selected",
                   command=self.remove_selected).pack(side="left", padx=5)
        ttk.Button(frame, text="Calculate",
                   command=self.calculate).pack(side="left", padx=5)
        ttk.Button(frame, text="Export to Excel",
                   command=self.export_file).pack(side="left")

    def build_table(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(frame, columns=COLUMNS,
                                 show="headings", height=14)
        for col in COLUMNS:
            anchor = "w" if col == "name" else "center"
            width = 150 if col == "name" else 90
            self.tree.heading(col, text=COL_LABELS[col])
            self.tree.column(col, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.on_double_click)

    def build_weights(self):
        frame = ttk.LabelFrame(self.root, text="Weights & Scheme", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        self.weight_vars = {}
        defaults = {"NHS": "50", "PTS": "30", "PAS": "20"}    # ← your scheme

        for i, comp in enumerate(COMPONENTS):
            ttk.Label(frame, text=f"{comp}:").grid(
                row=0, column=i * 3, sticky="e", padx=(0, 2))
            var = tk.StringVar(value=defaults[comp])
            ttk.Entry(frame, textvariable=var, width=6).grid(
                row=0, column=i * 3 + 1, sticky="w")
            ttk.Label(frame, text="%").grid(
                row=0, column=i * 3 + 2, sticky="w", padx=(2, 15))
            self.weight_vars[comp] = var

        # preset buttons
        ttk.Label(frame, text="Presets:").grid(
            row=1, column=0, sticky="e", pady=(8, 0))
        presets = ttk.Frame(frame)
        presets.grid(row=1, column=1, columnspan=6, sticky="w", pady=(8, 0))
        for label, values in [
            ("50/30/20", (50, 30, 20)),      # ← your preset, first
            ("30/30/40", (30, 30, 40)),
            ("20/30/50", (20, 30, 50)),
            ("40/30/30", (40, 30, 30)),
        ]:
            ttk.Button(presets, text=label, width=10,
                       command=lambda v=values: self.apply_preset(v)
                       ).pack(side="left", padx=2)

        # scheme picker
        ttk.Label(frame, text="Scheme:").grid(
            row=2, column=0, sticky="e", pady=(8, 0))
        self.scheme_var = tk.StringVar(value=self.scheme_name)
        combo = ttk.Combobox(frame, textvariable=self.scheme_var,
                             values=list(SCHEMES.keys()),
                             state="readonly", width=12)
        combo.grid(row=2, column=1, sticky="w", pady=(8, 0))
        combo.bind("<<ComboboxSelected>>", self.on_scheme_change)

    def build_status(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="x")
        self.status_var = tk.StringVar(
            value="Ready. Click '+ Add Row' to begin.")
        ttk.Label(frame, textvariable=self.status_var).pack(side="left")

    # ---------------- actions ----------------

    def add_row(self):
        item = self.tree.insert(
            "", "end", values=("", "", "", "", "", "", ""))
        self.rows[item] = {
            "nis": "", "name": "", "NHS": "", "PTS": "", "PAS": "",
        }
        self.tree.selection_set(item)
        self.tree.focus(item)

    def remove_selected(self):
        for item in self.tree.selection():
            self.rows.pop(item, None)
            self.tree.delete(item)
        self.status_var.set("Row(s) removed.")

    def apply_preset(self, values):
        for comp, v in zip(COMPONENTS, values):
            self.weight_vars[comp].set(str(v))

    def on_scheme_change(self, event=None):
        self.scheme_name = self.scheme_var.get()

    def calculate(self):
        # gather student records from rows
        students = []
        for item, data in self.rows.items():
            nis = (data.get("nis") or "").strip()
            name = (data.get("name") or "").strip()
            if not nis and not name:
                continue    # skip fully empty rows

            record = {"nis": nis, "name": name}
            for comp in COMPONENTS:
                try:
                    record[comp] = float(data.get(comp) or 0)
                except ValueError:
                    record[comp] = 0.0
            students.append(record)

        if not students:
            messagebox.showinfo("Nothing to calculate",
                                "Add at least one student.")
            return

        # read weights
        try:
            raw = {c: float(v.get() or 0)
                   for c, v in self.weight_vars.items()}
        except ValueError:
            messagebox.showerror("Invalid weights",
                                 "Weights must be numbers.")
            return

        if sum(raw.values()) <= 0:
            messagebox.showerror("Invalid weights",
                                 "Weights must sum to more than 0.")
            return

        weights = normalize_weights(raw)
        scheme = SCHEMES[self.scheme_name]

        self.results = rank_students(students, weights, scheme)
        self.summary_data = summary(self.results, scheme)

        self.refresh_final_columns()

        s = self.summary_data
        self.status_var.set(
            f"Average: {s['average']:.2f}  |  "
            f"Pass: {s['passing']}/{s['total']} "
            f"({s['pass_rate'] * 100:.0f}%)"
        )

    def refresh_final_columns(self):
        """Match results back to rows by (nis, name) and fill Final/Grade."""
        lookup = {}
        for r in self.results:
            key = (r.get("nis", "").strip(), r.get("name", "").strip())
            lookup[key] = r

        for item, data in self.rows.items():
            key = ((data.get("nis") or "").strip(),
                   (data.get("name") or "").strip())
            r = lookup.get(key)
            if r is None:
                self.tree.set(item, "weighted", "")
                self.tree.set(item, "grade", "")
                continue
            self.tree.set(item, "weighted", f"{r['weighted']:.2f}")
            self.tree.set(item, "grade", r["grade"])

    def export_file(self):
        if not self.results:
            messagebox.showinfo("Nothing to export",
                                "Click Calculate first.")
            return

        default = f"results_{datetime.now():%Y%m%d_%H%M}.xlsx"
        path = filedialog.asksaveasfilename(
            title="Save results",
            defaultextension=".xlsx",
            initialfile=default,
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not path:
            return

        try:
            write_results(
                path,
                COMPONENTS,
                self.results,
                self.summary_data,
                self.scheme_name,
            )
        except Exception as e:
            messagebox.showerror("Export error", str(e))
            return

        messagebox.showinfo("Export done", f"Saved to:\n{path}")

    # ---------------- inline editing ----------------

    def on_double_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        item = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)     # "#1", "#2", ...
        if not item or not col_id:
            return

        col_index = int(col_id[1:]) - 1
        col_name = self.tree["columns"][col_index]

        if col_name not in EDITABLE:
            return    # Final/Grade are read-only

        self.start_edit(item, col_name)

    def start_edit(self, item, col_name):
        # close any previous editor
        if self._edit_widget is not None:
            self._edit_widget.destroy()
            self._edit_widget = None

        bbox = self.tree.bbox(item, col_name)
        if not bbox:
            return
        x, y, w, h = bbox

        current = self.tree.set(item, col_name)
        var = tk.StringVar(value=current)

        entry = ttk.Entry(self.tree, textvariable=var)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(event=None):
            new_val = var.get()
            self.tree.set(item, col_name, new_val)
            if item in self.rows:
                self.rows[item][col_name] = new_val
            entry.destroy()
            self._edit_widget = None

        def cancel(event=None):
            entry.destroy()
            self._edit_widget = None

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", cancel)

        self._edit_widget = entry


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run()
