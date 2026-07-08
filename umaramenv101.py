import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
from PIL import Image, ImageTk

training_types = ["スピード", "スタミナ", "パワー", "根性", "賢さ", "お出かけ", "お休み", "レース"]
ramen_types = ["なし", "札幌", "函館", "新潟", "福島", "中山", "東京", "京都", "中京", "阪神", "小倉"]

train_abbr = {
    "スピード": "スピ", "スタミナ": "スタ", "パワー": "パワ",
    "根性": "根", "賢さ": "賢", "お出かけ": "出",
    "お休み": "休", "レース": "レース"
}

TRAIN_COLORS = {
    "スピード": "#d0ebff", "スタミナ": "#fff3bf", "パワー": "#ffe3e3",
    "根性": "#e7f5ff", "賢さ": "#e2f0d9", "お出かけ": "#fff9db",
    "お休み": "#f8f9fa", "レース": "#ffe8cc",
}

RAMEN_COLORS = {
    "なし": "#f1f3f5", "札幌": "#fff3bf", "函館": "#d0ebff",
    "新潟": "#e2f0d9", "福島": "#fff9db", "中山": "#ffe3e3",
    "東京": "#e7f5ff", "京都": "#f3d9fa", "中京": "#fff3bf",
    "阪神": "#ffe8cc", "小倉": "#d0ebff",
}


def get_turn_info(turn):
    if turn <= 12:
        if turn == 12:
            return "デビュー前", "12ターン（デビュー戦）"
        else:
            return "デビュー前", f"{turn}ターン"
    elif turn <= 24:
        display_turn = turn - 12
        return f"1年目 {display_turn}", get_month_str(turn)
    elif turn <= 48:
        display_turn = turn - 24
        return f"2年目 {display_turn}", get_month_str(turn)
    elif turn <= 72:
        display_turn = turn - 48
        return f"3年目 {display_turn}", get_month_str(turn)
    else:
        ura_turn = turn - 72
        return f"URA {ura_turn}", "URA"


def get_month_str(turn):
    if 13 <= turn <= 24:
        base = ["7月前半", "7月後半", "8月前半", "8月後半", "9月前半", "9月後半",
                "10月前半", "10月後半", "11月前半", "11月後半", "12月前半", "12月後半"]
        return base[turn - 13]
    else:
        base_months = [
            "1月前半", "1月後半", "2月前半", "2月後半", "3月前半", "3月後半",
            "4月前半", "4月後半", "5月前半", "5月後半", "6月前半", "6月後半",
            "7月前半", "7月後半", "8月前半", "8月後半", "9月前半", "9月後半",
            "10月前半", "10月後半", "11月前半", "11月後半", "12月前半", "12月後半"
        ]
        idx = (turn - 25) % 24
        return base_months[idx]


def init_db():
    conn = sqlite3.connect('umamusume.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (turn INTEGER PRIMARY KEY, training TEXT, ramen TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS meta
                 (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()


class UmaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ウマ娘 3年育成記録アプリ")
        self.root.geometry("1600x1000")
        self.root.configure(bg="white")

        init_db()
        self.cells = {}

        self.skill_pt_var = tk.StringVar(value="0")
        self.excitement_pt_var = tk.StringVar(value="0")
        self.evaluation_var = tk.StringVar(value="0")

        self.original_image = None
        self.current_photo = None
        self.image_label = None
        self.last_screenshot_path = None  # ← 追加：最後に読み込んだパスを保持

        self.create_ui()
        self.load_all_data()
        self.load_meta_values()

    def create_ui(self):
        main_pane = ttk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.create_pre_debut_tab(notebook)
        self.create_year_tab(notebook, 1, after_debut=True)
        self.create_year_tab(notebook, 2)
        self.create_year_tab(notebook, 3)

        ura_tab = ttk.Frame(notebook)
        notebook.add(ura_tab, text="URA期間")
        self.create_ura_tab(ura_tab)

        bottom_frame = ttk.LabelFrame(left_frame, text="期間別集計", padding=10)
        bottom_frame.pack(fill="x", padx=5, pady=5)

        control_frame = ttk.Frame(bottom_frame)
        control_frame.pack(fill="x", pady=(0, 8))

        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side="left")

        ttk.Button(btn_frame, text="⚠ 全記録消去", command=self.clear_all_data).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="記録を書き出す", command=self.export_data).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="記録を読み込む", command=self.import_data).pack(side="left", padx=5)

        input_frame = ttk.Frame(control_frame)
        input_frame.pack(side="right", padx=10)

        ttk.Label(input_frame, text="獲得スキポ", font=("Helvetica", 9)).pack(side="left", padx=(0, 4))
        self.skill_entry = ttk.Entry(input_frame, textvariable=self.skill_pt_var, width=12, justify="right")
        self.skill_entry.pack(side="left", padx=(0, 15))
        self.skill_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("skill_pt", self.skill_pt_var))

        ttk.Label(input_frame, text="総盛り上がりpt", font=("Helvetica", 9)).pack(side="left", padx=(0, 4))
        self.excite_entry = ttk.Entry(input_frame, textvariable=self.excitement_pt_var, width=12, justify="right")
        self.excite_entry.pack(side="left", padx=(0, 15))
        self.excite_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("excitement_pt", self.excitement_pt_var))

        ttk.Label(input_frame, text="評価点", font=("Helvetica", 9)).pack(side="left", padx=(0, 4))
        self.eval_entry = ttk.Entry(input_frame, textvariable=self.evaluation_var, width=12, justify="right")
        self.eval_entry.pack(side="left")
        self.eval_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("evaluation_score", self.evaluation_var))

        ttk.Label(bottom_frame, text="【トレーニング】（カッコ内はラーメン同時）", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.train_frame = ttk.Frame(bottom_frame)
        self.train_frame.pack(fill="x", pady=4)

        ttk.Label(bottom_frame, text="【ラーメン】", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(12, 6))
        self.ramen_frame = ttk.Frame(bottom_frame)
        self.ramen_frame.pack(fill="x", pady=4)

        right_frame = ttk.Frame(main_pane, width=400)
        right_frame.pack_propagate(False)
        main_pane.add(right_frame, weight=0)

        self.image_label = ttk.Label(right_frame, background="white")
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame_img = ttk.Frame(right_frame)
        btn_frame_img.pack(pady=5)
        ttk.Button(btn_frame_img, text="スクリーンショットを読み込む", command=self.load_screenshot).pack()

        self.root.bind("<Configure>", self.on_window_resize)

    def load_screenshot(self):
        file_path = filedialog.askopenfilename(
            title="Uma Musumeのスクリーンショットを選択",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if file_path:
            try:
                self.original_image = Image.open(file_path)
                self.last_screenshot_path = file_path
                self.save_meta("last_screenshot_path", file_path)   # DBに保存
                self.update_image()
                messagebox.showinfo("成功", "スクリーンショットを読み込み、保存しました")
            except Exception as e:
                messagebox.showerror("エラー", f"画像を読み込めませんでした。\n{e}")

    # ------------------- 以下は変更なし -------------------
    def create_pre_debut_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="デビュー前")
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        grid = ttk.Frame(frame)
        grid.pack(expand=True, fill="both")
        for i in range(12):
            turn = i + 1
            cell = self.create_cell(grid, turn)
            cell.grid(row=i//6, column=i%6, padx=6, pady=6, sticky="nsew")
            self.cells[turn] = cell
        for i in range(6):
            grid.columnconfigure(i, weight=1, uniform="cell")
        for i in range(2):
            grid.rowconfigure(i, weight=1, uniform="cell")

    def create_year_tab(self, notebook, year, after_debut=False):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=f"{year}年目")
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        grid = ttk.Frame(frame)
        grid.pack(expand=True, fill="both")
        if after_debut and year == 1:
            start, turns_count = 13, 12
        elif year == 2:
            start, turns_count = 25, 24
        elif year == 3:
            start, turns_count = 49, 24
        else:
            start, turns_count = 13, 24
        for i in range(turns_count):
            turn = start + i
            cell = self.create_cell(grid, turn)
            cell.grid(row=i//6, column=i%6, padx=6, pady=6, sticky="nsew")
            self.cells[turn] = cell
        for i in range(6):
            grid.columnconfigure(i, weight=1, uniform="cell")
        rows = 4 if turns_count == 24 else 2
        for i in range(rows):
            grid.rowconfigure(i, weight=1, uniform="cell")

    def create_ura_tab(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        grid = ttk.Frame(frame)
        grid.pack(expand=True, fill="both")
        for i in range(6):
            turn = 73 + i
            cell = self.create_cell(grid, turn)
            cell.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            self.cells[turn] = cell
        for i in range(6):
            grid.columnconfigure(i, weight=1, uniform="cell")
        grid.rowconfigure(0, weight=1)

    def create_cell(self, parent, turn):
        frame = ttk.Frame(parent, relief="ridge", borderwidth=2)
        turn_str, month_str = get_turn_info(turn)
        if turn <= 12:
            l1 = tk.Label(frame, text=turn_str, bg="#E0F0FF", font=("Helvetica", 10, "bold"), height=1)
            l1.pack(fill="x")
            l2 = tk.Label(frame, text=month_str, bg="#E0F0FF", font=("Helvetica", 9), height=1)
            l2.pack(fill="x")
        else:
            l1 = tk.Label(frame, text=turn_str, bg="#E0F0FF", font=("Helvetica", 11, "bold"), height=1)
            l1.pack(fill="x")
            l2 = tk.Label(frame, text=month_str, bg="#FFF0F5", font=("Helvetica", 10), height=1)
            l2.pack(fill="x")
        train_label = tk.Label(frame, text="", bg="white", font=("Helvetica", 10), height=1, anchor="w")
        train_label.pack(fill="x", padx=5)
        ramen_label = tk.Label(frame, text="", bg="white", font=("Helvetica", 10), height=1, anchor="w")
        ramen_label.pack(fill="x", padx=5)
        for widget in (frame, l1, l2, train_label, ramen_label):
            widget.bind("<Button-1>", lambda e, t=turn: self.show_record_dialog(t))
        return frame

    def show_record_dialog(self, turn):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"ターン {turn} の記録")
        dialog.geometry("400x280")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        turn_str, month_str = get_turn_info(turn)
        ttk.Label(dialog, text=f"{turn_str}　{month_str}", font=("Helvetica", 12, "bold")).pack(pady=15)
        ttk.Label(dialog, text="トレーニング:").pack(anchor="w", padx=40, pady=(5, 0))
        training_combo = ttk.Combobox(dialog, values=training_types, width=28, state="readonly")
        training_combo.pack(pady=5, padx=40, fill="x")
        ttk.Label(dialog, text="ラーメン:").pack(anchor="w", padx=40, pady=(12, 0))
        ramen_combo = ttk.Combobox(dialog, values=ramen_types, width=28, state="readonly")
        ramen_combo.pack(pady=5, padx=40, fill="x")

        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT training, ramen FROM records WHERE turn=?", (turn,))
        data = c.fetchone()
        conn.close()
        if data:
            training_combo.set(data[0] or "")
            ramen_combo.set(data[1] or "")

        special_trainings = {"お休み", "お出かけ", "レース"}

        def check_and_save(*args):
            training = training_combo.get().strip()
            ramen = ramen_combo.get().strip()
            if not training:
                return
            if training in special_trainings:
                self.save_record(turn, training, ramen or "なし", dialog)
                return
            if training and ramen and ramen != "":
                self.save_record(turn, training, ramen, dialog)

        training_combo.bind("<<ComboboxSelected>>", check_and_save)
        ramen_combo.bind("<<ComboboxSelected>>", check_and_save)

    def save_record(self, turn, training, ramen, dialog):
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO records (turn, training, ramen) VALUES (?,?,?)", (turn, training, ramen))
        conn.commit()
        conn.close()
        self.update_cell_display(turn, training, ramen)
        self.update_period_summary()
        dialog.destroy()

    def update_cell_display(self, turn, training, ramen):
        cell = self.cells.get(turn)
        if not cell:
            return
        labels = cell.winfo_children()
        if len(labels) >= 4:
            labels[-2].config(text=training or "")
            labels[-1].config(text=ramen if ramen != "なし" else "")

    def load_all_data(self):
        for cell in self.cells.values():
            labels = cell.winfo_children()
            if len(labels) >= 4:
                labels[-2].config(text="")
                labels[-1].config(text="")
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT turn, training, ramen FROM records")
        for turn, training, ramen in c.fetchall():
            if turn in self.cells:
                self.update_cell_display(turn, training, ramen)
        conn.close()
        self.update_period_summary()

    def clear_all_data(self):
        if messagebox.askyesno("全消去", "すべての記録を消去しますか？"):
            conn = sqlite3.connect('umamusume.db')
            c = conn.cursor()
            c.execute("DELETE FROM records")
            conn.commit()
            conn.close()
            self.load_all_data()
            messagebox.showinfo("完了", "全記録を消去しました")

    def export_data(self):
        file_path = filedialog.asksaveasfilename(title="記録を保存するファイルを選択", defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT turn, training, ramen FROM records ORDER BY turn")
        records = [{"turn": t, "training": tr, "ramen": r} for t, tr, r in c.fetchall()]
        conn.close()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完了", f"{len(records)}件の記録を書き出しました")
        except Exception as e:
            messagebox.showerror("エラー", f"書き出せませんでした。\n{e}")

    def import_data(self):
        file_path = filedialog.askopenfilename(title="読み込む記録ファイルを選択",
                                               filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルを読み込めませんでした。\n{e}")
            return
        if not isinstance(records, list):
            messagebox.showerror("エラー", "不正なファイル形式です")
            return
        if not messagebox.askyesno("確認", f"{len(records)}件の記録を読み込みますか？\n同じターンの記録は上書きされます。"):
            return
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        for rec in records:
            if isinstance(rec, dict) and "turn" in rec:
                c.execute("INSERT OR REPLACE INTO records (turn, training, ramen) VALUES (?,?,?)",
                          (rec["turn"], rec.get("training"), rec.get("ramen")))
        conn.commit()
        conn.close()
        self.load_all_data()
        messagebox.showinfo("完了", "記録を読み込みました")

    def load_meta_values(self):
        self.skill_pt_var.set(self._format_display(self.load_meta("skill_pt")))
        self.excitement_pt_var.set(self._format_display(self.load_meta("excitement_pt")))
        self.evaluation_var.set(self._format_display(self.load_meta("evaluation_score")))

        # スクリーンショットのパスを復元
        saved_path = self.load_meta("last_screenshot_path", "")
        if saved_path and saved_path != "None":
            try:
                self.original_image = Image.open(saved_path)
                self.last_screenshot_path = saved_path
                self.update_image()
            except Exception:
                # ファイルがなくなっていた場合はクリア
                self.save_meta("last_screenshot_path", "")

    def _format_display(self, val):
        try:
            return f"{int(val):,}"
        except:
            return "0"

    def format_and_save_meta(self, key, var):
        try:
            raw = int(var.get().replace(",", "").strip() or "0")
            if raw > 999999: raw = 999999
            var.set(f"{raw:,}")
            self.save_meta(key, raw)
        except:
            var.set("0")
            self.save_meta(key, 0)

    def save_meta(self, key, value):
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, str(value)))
        conn.commit()
        conn.close()

    def load_meta(self, key, default="0"):
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else default

    def update_period_summary(self):
        # （ここは変更なし・省略せずに全文残しています）
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT turn, training, ramen FROM records")
        data = c.fetchall()
        conn.close()

        periods = {
            "デビュー前": (1, 12),
            "1年目": (13, 24),
            "2年目": (25, 48),
            "3年目": (49, 72),
            "URA": (73, 78)
        }

        for widget in self.train_frame.winfo_children():
            widget.destroy()

        headers = ["期間"] + [train_abbr[t] for t in training_types]
        for col, header in enumerate(headers):
            ttk.Label(self.train_frame, text=header, font=("Helvetica", 9, "bold"),
                      background="#fff9db", anchor="center", width=9).grid(
                row=0, column=col, padx=1, pady=1, sticky="nsew")

        train_total = {t: 0 for t in training_types}
        paired_total = {t: 0 for t in training_types}

        for row_idx, (pname, (start, end)) in enumerate(periods.items(), start=1):
            counts = {t: 0 for t in training_types}
            paired = {t: 0 for t in training_types}
            for t, training, ramen in data:
                if start <= t <= end and training in counts:
                    counts[training] += 1
                    train_total[training] += 1
                    if ramen and ramen != "なし":
                        paired[training] += 1
                        paired_total[training] += 1

            ttk.Label(self.train_frame, text=pname, font=("Helvetica", 9), anchor="center", width=10).grid(
                row=row_idx, column=0, padx=1, pady=1, sticky="nsew")

            for col_idx, t in enumerate(training_types, start=1):
                val = counts[t]
                pval = paired[t]
                color = TRAIN_COLORS[t]

                cell_frame = ttk.Frame(self.train_frame)
                cell_frame.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")

                tk.Label(cell_frame, text=str(val), font=("Helvetica", 9), background=color, anchor="center", width=5).pack(side="left")
                tk.Label(cell_frame, text="" if t in ("お出かけ","お休み","レース") else f"({pval})", 
                         font=("Helvetica", 9, "bold"), foreground="#cc0000" if pval > 0 else "#666666", 
                         background=color, anchor="center", width=4).pack(side="left")

        # 合計行
        ttk.Label(self.train_frame, text="合計", font=("Helvetica", 9, "bold"), anchor="center", width=10).grid(
            row=len(periods)+1, column=0, padx=1, pady=1, sticky="nsew")
        for col_idx, t in enumerate(training_types, start=1):
            val = train_total[t]
            pval = paired_total[t]
            color = TRAIN_COLORS[t]
            cell_frame = ttk.Frame(self.train_frame)
            cell_frame.grid(row=len(periods)+1, column=col_idx, padx=1, pady=1, sticky="nsew")
            tk.Label(cell_frame, text=str(val), font=("Helvetica", 9, "bold"), background=color, anchor="center", width=5).pack(side="left")
            tk.Label(cell_frame, text="" if t in ("お出かけ","お休み","レース") else f"({pval})", 
                     font=("Helvetica", 9, "bold"), foreground="#cc0000" if pval > 0 else "#666666", 
                     background=color, anchor="center", width=4).pack(side="left")

        # ラーメン集計（省略せず全文）
        for widget in self.ramen_frame.winfo_children():
            widget.destroy()

        ramen_headers = ["期間"] + [r[:3] for r in ramen_types]
        for col, header in enumerate(ramen_headers):
            ttk.Label(self.ramen_frame, text=header, font=("Helvetica", 9, "bold"),
                      background="#e8e8e8", anchor="center", width=7).grid(
                row=0, column=col, padx=1, pady=1, sticky="nsew")

        ramen_total = {r: 0 for r in ramen_types}
        for row_idx, (pname, (start, end)) in enumerate(periods.items(), start=1):
            counts = {r: 0 for r in ramen_types}
            for t, _, ramen in data:
                if start <= t <= end and ramen in counts:
                    counts[ramen] += 1
                    ramen_total[ramen] += 1
            ttk.Label(self.ramen_frame, text=pname, font=("Helvetica", 9), anchor="center", width=10).grid(
                row=row_idx, column=0, padx=1, pady=1, sticky="nsew")
            for col_idx, r in enumerate(ramen_types, start=1):
                val = counts[r]
                color = RAMEN_COLORS[r] if val > 0 else "white"
                ttk.Label(self.ramen_frame, text=str(val), font=("Helvetica", 9),
                          background=color, anchor="center", width=5).grid(
                    row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")

        ttk.Label(self.ramen_frame, text="合計", font=("Helvetica", 9, "bold"), anchor="center", width=10).grid(
            row=len(periods)+1, column=0, padx=1, pady=1, sticky="nsew")
        for col_idx, r in enumerate(ramen_types, start=1):
            val = ramen_total[r]
            color = RAMEN_COLORS[r] if val > 0 else "white"
            ttk.Label(self.ramen_frame, text=str(val), font=("Helvetica", 9, "bold"),
                      background=color, anchor="center", width=5).grid(
                row=len(periods)+1, column=col_idx, padx=1, pady=1, sticky="nsew")

        total_ramen_eaten = sum(v for k, v in ramen_total.items() if k != "なし")
        big_label = tk.Label(
            self.ramen_frame,
            text=f"貴様がこれまでに食ったラーメンの回数　{total_ramen_eaten}回",
            font=("Helvetica", 13, "bold"),
            foreground="#b30000",
            background="#fff0f0",
            anchor="center",
            pady=8
        )
        big_label.grid(row=len(periods) + 2, column=0, columnspan=len(ramen_types) + 1,
                       pady=(10, 4), sticky="ew", padx=2)

    def update_image(self):
        if not self.original_image or not self.image_label.winfo_width():
            return
        try:
            label_w = max(100, self.image_label.winfo_width() - 20)
            label_h = max(100, self.image_label.winfo_height() - 20)
            img_w, img_h = self.original_image.size
            label_ratio = label_w / label_h
            img_ratio = img_w / img_h
            if img_ratio > label_ratio:
                new_h = label_h
                new_w = int(new_h * img_ratio)
            else:
                new_w = label_w
                new_h = int(new_w / img_ratio)
            resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - label_w) // 2
            top = (new_h - label_h) // 2
            cropped = resized.crop((left, top, left + label_w, top + label_h))
            self.current_photo = ImageTk.PhotoImage(cropped)
            self.image_label.config(image=self.current_photo)
        except Exception:
            pass

    def on_window_resize(self, event=None):
        if event and event.widget == self.root:
            self.root.after(80, self.update_image)


if __name__ == "__main__":
    root = tk.Tk()
    app = UmaApp(root)
    root.mainloop()
