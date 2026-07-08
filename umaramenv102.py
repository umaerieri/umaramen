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
        return "デビュー前", f"{turn}ターン" if turn < 12 else "12ターン（デビュー戦）"
    elif turn <= 24:
        return f"1年目 {turn-12}", get_month_str(turn)
    elif turn <= 48:
        return f"2年目 {turn-24}", get_month_str(turn)
    elif turn <= 72:
        return f"3年目 {turn-48}", get_month_str(turn)
    else:
        return f"URA {turn-72}", "URA"


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
    c.execute('''CREATE TABLE IF NOT EXISTS records (turn INTEGER PRIMARY KEY, training TEXT, ramen TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)''')
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
        self.last_screenshot_path = None

        self.train_labels = {}
        self.ramen_labels = {}
        self.total_ramen_label = None
        self.summary_created = False

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
        ttk.Label(input_frame, text="獲得スキポ").pack(side="left", padx=(0, 4))
        self.skill_entry = ttk.Entry(input_frame, textvariable=self.skill_pt_var, width=12, justify="right")
        self.skill_entry.pack(side="left", padx=(0, 15))
        self.skill_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("skill_pt", self.skill_pt_var))

        ttk.Label(input_frame, text="総盛り上がりpt").pack(side="left", padx=(0, 4))
        self.excite_entry = ttk.Entry(input_frame, textvariable=self.excitement_pt_var, width=12, justify="right")
        self.excite_entry.pack(side="left", padx=(0, 15))
        self.excite_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("excitement_pt", self.excitement_pt_var))

        ttk.Label(input_frame, text="評価点").pack(side="left", padx=(0, 4))
        self.eval_entry = ttk.Entry(input_frame, textvariable=self.evaluation_var, width=12, justify="right")
        self.eval_entry.pack(side="left")
        self.eval_entry.bind("<FocusOut>", lambda e: self.format_and_save_meta("evaluation_score", self.evaluation_var))

        ttk.Label(bottom_frame, text="【トレーニング】（カッコ内はラーメン同時）", 
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(0, 6))
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
        ttk.Button(right_frame, text="スクリーンショットを読み込む", command=self.load_screenshot).pack(pady=5)

        self.root.bind("<Configure>", self.on_window_resize)

    # 集計表作成（省略せず全文）
    def _create_train_summary_table(self):
        headers = ["期間"] + [train_abbr[t] for t in training_types]
        for col, header in enumerate(headers):
            ttk.Label(self.train_frame, text=header, font=("Helvetica", 9, "bold"),
                      background="#fff9db", anchor="center", width=9).grid(row=0, column=col, padx=1, pady=1, sticky="nsew")

        periods = ["デビュー前", "1年目", "2年目", "3年目", "URA", "合計"]
        for row_idx, pname in enumerate(periods, start=1):
            ttk.Label(self.train_frame, text=pname, font=("Helvetica", 9), anchor="center", width=10).grid(
                row=row_idx, column=0, padx=1, pady=1, sticky="nsew")
            for col_idx, t in enumerate(training_types, start=1):
                color = TRAIN_COLORS[t]
                frame = ttk.Frame(self.train_frame)
                frame.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")
                num = tk.Label(frame, text="0", font=("Helvetica", 9), bg=color, anchor="center", width=5)
                num.pack(side="left")
                pair = tk.Label(frame, text="", font=("Helvetica", 9, "bold"), fg="#cc0000", bg=color, anchor="center", width=4)
                pair.pack(side="left")
                self.train_labels[(pname, t)] = (num, pair)

    def _create_ramen_summary_table(self):
        headers = ["期間"] + [r[:3] for r in ramen_types]
        for col, header in enumerate(headers):
            ttk.Label(self.ramen_frame, text=header, font=("Helvetica", 9, "bold"),
                      background="#e8e8e8", anchor="center", width=7).grid(row=0, column=col, padx=1, pady=1, sticky="nsew")

        periods = ["デビュー前", "1年目", "2年目", "3年目", "URA", "合計"]
        for row_idx, pname in enumerate(periods, start=1):
            ttk.Label(self.ramen_frame, text=pname, font=("Helvetica", 9), anchor="center", width=10).grid(
                row=row_idx, column=0, padx=1, pady=1, sticky="nsew")
            for col_idx, r in enumerate(ramen_types, start=1):
                lbl = ttk.Label(self.ramen_frame, text="0", font=("Helvetica", 9),
                                background=RAMEN_COLORS[r], anchor="center", width=5)
                lbl.grid(row=row_idx, column=col_idx, padx=1, pady=1, sticky="nsew")
                self.ramen_labels[(pname, r)] = lbl

        self.total_ramen_label = tk.Label(
            self.ramen_frame, text="貴様がこれまでに食ったラーメンの回数　0回",
            font=("Helvetica", 13, "bold"), foreground="#b30000", background="#fff0f0", anchor="center", pady=8)
        self.total_ramen_label.grid(row=len(periods)+1, column=0, columnspan=len(ramen_types)+1, pady=(10,4), sticky="ew", padx=2)

    def create_pre_debut_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="デビュー前")
        self._create_grid(tab, range(1, 13))

    def create_year_tab(self, notebook, year, after_debut=False):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=f"{year}年目")
        if year == 1 and after_debut:
            self._create_grid(tab, range(13, 25))
        elif year == 2:
            self._create_grid(tab, range(25, 49))
        elif year == 3:
            self._create_grid(tab, range(49, 73))

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
        for i in range(6): grid.columnconfigure(i, weight=1)

    def _create_grid(self, tab, turn_range):
        frame = ttk.Frame(tab)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        grid = ttk.Frame(frame)
        grid.pack(expand=True, fill="both")
        for i, turn in enumerate(turn_range):
            cell = self.create_cell(grid, turn)
            cell.grid(row=i//6, column=i%6, padx=6, pady=6, sticky="nsew")
            self.cells[turn] = cell
        for i in range(6): grid.columnconfigure(i, weight=1)
        for i in range((len(turn_range)+5)//6): grid.rowconfigure(i, weight=1)

    def create_cell(self, parent, turn):
        frame = ttk.Frame(parent, relief="ridge", borderwidth=2)
        turn_str, month_str = get_turn_info(turn)
        l1 = tk.Label(frame, text=turn_str, bg="#E0F0FF", font=("Helvetica", 10, "bold"))
        l1.pack(fill="x")
        l2 = tk.Label(frame, text=month_str, bg="#FFF0F5" if turn > 12 else "#E0F0FF", font=("Helvetica", 9))
        l2.pack(fill="x")
        train_label = tk.Label(frame, text="", bg="white", font=("Helvetica", 10), anchor="w")
        train_label.pack(fill="x", padx=5)
        ramen_label = tk.Label(frame, text="", bg="white", font=("Helvetica", 10), anchor="w")
        ramen_label.pack(fill="x", padx=5)

        for w in (frame, l1, l2, train_label, ramen_label):
            w.bind("<Button-1>", lambda e, t=turn: self.show_record_dialog(t))
        return frame

    # ==================== ここが修正ポイント ====================
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

        special_trainings = {"お出かけ", "お休み", "レース"}

        def try_save(*args):
            training = training_combo.get().strip()
            ramen = ramen_combo.get().strip() or "なし"
            if not training:
                return

            # 特殊トレーニング → 選択した時点で保存
            if training in special_trainings:
                self.save_record(turn, training, ramen, dialog)
                return

            # 通常トレーニング → ラーメン（なし含む）を選択したら保存
            if ramen_combo.get():   # 何か選択されたら（"なし"でもOK）
                self.save_record(turn, training, ramen, dialog)

        training_combo.bind("<<ComboboxSelected>>", try_save)
        ramen_combo.bind("<<ComboboxSelected>>", try_save)

    def save_record(self, turn, training, ramen, dialog):
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO records (turn, training, ramen) VALUES (?,?,?)",
                  (turn, training, ramen))
        conn.commit()
        conn.close()

        self.update_cell_display(turn, training, ramen)
        self.update_period_summary()
        dialog.destroy()

    def update_cell_display(self, turn, training, ramen):
        cell = self.cells.get(turn)
        if cell and len(cell.winfo_children()) >= 4:
            cell.winfo_children()[-2].config(text=training or "")
            cell.winfo_children()[-1].config(text=ramen if ramen != "なし" else "")

    def update_period_summary(self):
        conn = sqlite3.connect('umamusume.db')
        c = conn.cursor()
        c.execute("SELECT turn, training, ramen FROM records")
        data = c.fetchall()
        conn.close()

        periods = {"デビュー前": (1,12), "1年目":(13,24), "2年目":(25,48),
                   "3年目":(49,72), "URA":(73,78)}

        if not self.summary_created:
            self._create_train_summary_table()
            self._create_ramen_summary_table()
            self.summary_created = True

        train_total = {t: 0 for t in training_types}
        paired_total = {t: 0 for t in training_types}
        ramen_total = {r: 0 for r in ramen_types}

        p_train = {p: {t:0 for t in training_types} for p in periods}
        p_paired = {p: {t:0 for t in training_types} for p in periods}
        p_ramen = {p: {r:0 for r in ramen_types} for p in periods}

        for turn, tr, rm in data:
            for pname, (s,e) in periods.items():
                if s <= turn <= e:
                    if tr in p_train[pname]:
                        p_train[pname][tr] += 1
                        train_total[tr] += 1
                        if rm != "なし":
                            p_paired[pname][tr] += 1
                            paired_total[tr] += 1
                    if rm in p_ramen[pname]:
                        p_ramen[pname][rm] += 1
                        ramen_total[rm] += 1
                    break

        for pname in periods:
            for t in training_types:
                if (pname, t) in self.train_labels:
                    num, pair = self.train_labels[(pname, t)]
                    num.config(text=str(p_train[pname][t]))
                    if t not in ("お出かけ","お休み","レース"):
                        pair.config(text=f"({p_paired[pname][t]})")
            for r in ramen_types:
                if (pname, r) in self.ramen_labels:
                    self.ramen_labels[(pname, r)].config(text=str(p_ramen[pname][r]))

        for t in training_types:
            if ("合計", t) in self.train_labels:
                num, pair = self.train_labels[("合計", t)]
                num.config(text=str(train_total[t]))
                if t not in ("お出かけ","お休み","レース"):
                    pair.config(text=f"({paired_total[t]})")

        for r in ramen_types:
            if ("合計", r) in self.ramen_labels:
                self.ramen_labels[("合計", r)].config(text=str(ramen_total[r]))

        total_eaten = sum(v for k,v in ramen_total.items() if k != "なし")
        if self.total_ramen_label:
            self.total_ramen_label.config(text=f"貴様がこれまでに食ったラーメンの回数　{total_eaten}回")

    # 以下は変更なし（load_all_data, clear, export, import, meta, image関連）
    def load_all_data(self):
        for cell in self.cells.values():
            labels = cell.winfo_children()
            if len(labels) >= 4:
                labels[-2].config(text="")
                labels[-1].config(text="")
        self.update_period_summary()

    def clear_all_data(self):
        if messagebox.askyesno("全消去", "すべての記録を消去しますか？"):
            conn = sqlite3.connect('umamusume.db')
            conn.cursor().execute("DELETE FROM records")
            conn.commit()
            conn.close()
            self.load_all_data()
            messagebox.showinfo("完了", "全記録を消去しました")

    def export_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path: return
        conn = sqlite3.connect('umamusume.db')
        records = [{"turn": t, "training": tr, "ramen": r} for t, tr, r in 
                   conn.cursor().execute("SELECT turn, training, ramen FROM records ORDER BY turn")]
        conn.close()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("完了", f"{len(records)}件保存しました")

    def import_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path: return
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        if messagebox.askyesno("確認", f"{len(records)}件読み込みますか？"):
            conn = sqlite3.connect('umamusume.db')
            c = conn.cursor()
            for rec in records:
                if "turn" in rec:
                    c.execute("INSERT OR REPLACE INTO records VALUES (?,?,?)",
                              (rec["turn"], rec.get("training"), rec.get("ramen")))
            conn.commit()
            conn.close()
            self.load_all_data()
            messagebox.showinfo("完了", "読み込み完了")

    def load_meta_values(self):
        self.skill_pt_var.set(self._format_display(self.load_meta("skill_pt")))
        self.excitement_pt_var.set(self._format_display(self.load_meta("excitement_pt")))
        self.evaluation_var.set(self._format_display(self.load_meta("evaluation_score")))

        saved = self.load_meta("last_screenshot_path", "")
        if saved:
            try:
                self.original_image = Image.open(saved)
                self.last_screenshot_path = saved
                self.update_image()
            except:
                pass

    def _format_display(self, val):
        try: return f"{int(val):,}"
        except: return "0"

    def format_and_save_meta(self, key, var):
        try:
            raw = int(var.get().replace(",", "") or 0)
            var.set(f"{raw:,}")
            self.save_meta(key, raw)
        except:
            var.set("0")
            self.save_meta(key, 0)

    def save_meta(self, key, value):
        conn = sqlite3.connect('umamusume.db')
        conn.cursor().execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))
        conn.commit()
        conn.close()

    def load_meta(self, key, default="0"):
        row = sqlite3.connect('umamusume.db').cursor().execute(
            "SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def load_screenshot(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")])
        if path:
            try:
                self.original_image = Image.open(path)
                self.last_screenshot_path = path
                self.save_meta("last_screenshot_path", path)
                self.update_image()
                messagebox.showinfo("成功", "スクリーンショットを読み込みました")
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def update_image(self):
        if not self.original_image: return
        try:
            w = max(100, self.image_label.winfo_width() - 20)
            h = max(100, self.image_label.winfo_height() - 20)
            img = self.original_image.copy()
            img.thumbnail((w, h), Image.Resampling.LANCZOS)
            self.current_photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_photo)
        except:
            pass

    def on_window_resize(self, event=None):
        if event and event.widget == self.root:
            self.root.after(100, self.update_image)


if __name__ == "__main__":
    root = tk.Tk()
    app = UmaApp(root)
    root.mainloop()
