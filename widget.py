"""
Personal OS Widget — compact desktop widget, always on the home screen.
Tabs: Tasks · Buy · Jobs · Assets
"""
import customtkinter as ctk
import json, os, ctypes, threading, urllib.request, urllib.error, subprocess
from datetime import datetime, date, timedelta

POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

def toast(title: str, message: str):
    """Show a Windows toast notification (no extra packages needed)."""
    safe_title   = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    ps = f"""
$app = 'Personal OS'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$tmpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$nodes = $tmpl.GetElementsByTagName('text')
$nodes.Item(0).AppendChild($tmpl.CreateTextNode("{safe_title}")) | Out-Null
$nodes.Item(1).AppendChild($tmpl.CreateTextNode("{safe_message}")) | Out-Null
$n = [Windows.UI.Notifications.ToastNotification]::new($tmpl)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show($n)
"""
    subprocess.Popen(
        [POWERSHELL, "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

# ── Theme — Meta / Facebook Design System (light) ─────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG      = "#F0F2F5"   # Meta app background
SURFACE = "#FFFFFF"   # card white
CARD    = "#F7F8FA"   # slightly off-white for inner cards
ACCENT  = "#1877F2"   # Meta blue
GREEN   = "#42B72A"   # Meta green
YELLOW  = "#F7B928"
RED     = "#FA3E3E"
MUTED   = "#65676B"   # Meta secondary text
TEXT    = "#050505"   # Meta primary text

# ── Data paths ─────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.abspath(__file__))
TASKS_F    = os.path.join(BASE, "tasks.json")
BUY_F      = os.path.join(BASE, "buylist.json")
JOBS_F     = os.path.join(BASE, "jobs.json")
ASSETS_F   = os.path.join(BASE, "assets.json")
SETTINGS_F = os.path.join(BASE, "settings.json")
POS_F      = os.path.join(BASE, "widget_pos.json")


# ── Tiny storage helpers ───────────────────────────────────────────────────────
def load(path, default=None):
    if default is None:
        default = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def uid():
    import random, string
    return datetime.now().strftime("%Y%m%d%H%M%S") + "".join(random.choices(string.ascii_lowercase, k=4))

def today_str():
    return date.today().isoformat()

def fmt_inr(n):
    if n >= 1e7:  return f"₹{n/1e7:.2f}Cr"
    if n >= 1e5:  return f"₹{n/1e5:.2f}L"
    return f"₹{int(n):,}"


# ══════════════════════════════════════════════════════════════════════════════
class PersonalOS(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._drag_x = self._drag_y = 0
        self._active_tab = "tasks"
        self._gold_price = None
        self.settings      = load(SETTINGS_F, {"name": "", "jobs_goal": 20, "gmail_accounts": []})
        self.gmail_accounts = self.settings.get("gmail_accounts", [])

        self._expanded_tasks = set()
        self._build_window()

        # First-run onboarding if name not set yet
        if not self.settings.get("name"):
            self.update()
            self._open_settings_dialog(first_run=True)

        self._build_ui()
        self._fix_taskbar()
        self._switch_tab("tasks")

        threading.Thread(target=self._fetch_gold, daemon=True).start()
        self._start_reminder_checker()

    # ── Window ─────────────────────────────────────────────────────────────────
    def _build_window(self):
        self.overrideredirect(True)
        self.attributes("-alpha", 0.96)
        self.configure(fg_color=BG)
        self.resizable(False, False)

        pos = load(POS_F, {})
        sw  = self.winfo_screenwidth()
        x   = pos.get("x", sw - 360)
        y   = pos.get("y", 50)
        self.geometry(f"340x640+{x}+{y}")

    def _fix_taskbar(self):
        GWL_EXSTYLE      = -20
        WS_EX_APPWINDOW  = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080
        hwnd  = self.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        ctypes.windll.user32.ShowWindow(hwnd, 5)

    def _save_pos(self):
        save(POS_F, {"x": self.winfo_x(), "y": self.winfo_y()})

    # ── Drag ───────────────────────────────────────────────────────────────────
    def _drag_start(self, e): self._drag_x = e.x; self._drag_y = e.y
    def _drag_move(self, e):
        self.geometry(f"+{self.winfo_x()+e.x-self._drag_x}+{self.winfo_y()+e.y-self._drag_y}")
    def _drag_end(self, _): self._save_pos()

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>",   self._drag_start)
        widget.bind("<B1-Motion>",       self._drag_move)
        widget.bind("<ButtonRelease-1>", self._drag_end)

    # ── UI skeleton ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        self._bind_drag(hdr)

        name = self.settings.get("name", "Pradeep")
        hour = datetime.now().hour
        greet = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"

        lbl = ctk.CTkLabel(hdr, text=f"  Good {greet}, {name}",
                           font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=TEXT)
        lbl.pack(side="left", pady=10); self._bind_drag(lbl)

        self.date_lbl = ctk.CTkLabel(hdr, text=date.today().strftime("%a, %d %b"),
                                     font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED)
        self.date_lbl.pack(side="left", padx=4); self._bind_drag(self.date_lbl)

        ctk.CTkButton(hdr, text="⚙", width=32, height=32,
                      fg_color="transparent", hover_color="#E4E6EB",
                      text_color=MUTED, font=ctk.CTkFont(size=14),
                      command=lambda: self._open_settings_dialog(first_run=False)
                      ).pack(side="right", padx=2)
        ctk.CTkButton(hdr, text="×", width=32, height=32,
                      fg_color="transparent", hover_color="#E4E6EB",
                      text_color=MUTED, font=ctk.CTkFont(size=18),
                      command=self._on_close).pack(side="right", padx=6)

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=38)
        tab_bar.pack(fill="x"); tab_bar.pack_propagate(False)

        self._tab_btns = {}
        for key, label in [("tasks","Tasks"), ("buy","Buy"), ("jobs","Jobs"), ("assets","Assets"), ("cal","Calendar")]:
            btn = ctk.CTkButton(tab_bar, text=label, width=60, height=28,
                                fg_color="transparent", hover_color=CARD,
                                text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                                corner_radius=6,
                                command=lambda k=key: self._switch_tab(k))
            btn.pack(side="left", padx=2, pady=5)
            self._tab_btns[key] = btn

        # ── Credits bar (bottom) ──────────────────────────────────────────────
        credits = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=22)
        credits.pack(fill="x", side="bottom")
        credits.pack_propagate(False)
        ctk.CTkLabel(credits, text="Built by ",
                     font=ctk.CTkFont("Segoe UI", 9), text_color=MUTED
                     ).pack(side="left", padx=(10, 0))
        link = ctk.CTkLabel(credits, text="Pradeep ↗",
                            font=ctk.CTkFont("Segoe UI", 9, "bold"),
                            text_color=ACCENT, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _: __import__("webbrowser").open(
            "https://www.pradeepyellapu.com/"))

        # ── Content area ──────────────────────────────────────────────────────
        self._frames = {}
        container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        container.pack(fill="both", expand=True)

        for key in ("tasks", "buy", "jobs", "assets", "cal"):
            f = ctk.CTkFrame(container, fg_color=BG, corner_radius=0)
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._frames[key] = f

        self._build_tasks_tab()
        self._build_buy_tab()
        self._build_jobs_tab()
        self._build_assets_tab()
        self._build_cal_tab()

    def _switch_tab(self, key):
        self._active_tab = key
        for k, f in self._frames.items():
            f.tkraise() if k == key else None
        self._frames[key].tkraise()

        for k, b in self._tab_btns.items():
            if k == key:
                b.configure(fg_color=ACCENT, text_color="white")
            else:
                b.configure(fg_color="transparent", text_color=MUTED)

        refresh = {"tasks": self._render_tasks, "buy": self._render_buy,
                   "jobs": self._render_jobs, "assets": self._render_assets,
                   "cal": self._render_cal}
        refresh[key]()

    # ══════════════════════════════════════════════════════════════════════════
    # TASKS TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_tasks_tab(self):
        f = self._frames["tasks"]

        # Suggestion banner
        self.task_suggest = ctk.CTkLabel(f, text="", wraplength=300,
                                         fg_color="#E7F3FF", corner_radius=8,
                                         font=ctk.CTkFont("Segoe UI", 12),
                                         text_color=ACCENT, pady=6)

        # Scrollable list
        self.task_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent",
                                                   scrollbar_button_color=SURFACE)
        self.task_scroll.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        # Input
        inp_row = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12)
        inp_row.pack(fill="x", padx=8, pady=8)

        self.task_entry = ctk.CTkEntry(inp_row, placeholder_text="Add task…",
                                       fg_color="transparent", border_width=0,
                                       font=ctk.CTkFont("Segoe UI", 13),
                                       text_color=TEXT, placeholder_text_color=MUTED, height=38)
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.task_entry.bind("<Return>", self._add_task)

        ctk.CTkButton(inp_row, text="+", width=36, height=36,
                      fg_color=ACCENT, hover_color="#4070cc",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      corner_radius=8, command=self._add_task).pack(side="right", padx=4, pady=3)

    def _add_task(self, _=None):
        text = self.task_entry.get().strip()
        if not text: return
        tasks = load(TASKS_F)
        tasks.append({"id": uid(), "text": text, "done": False,
                      "priority": "medium", "createdAt": datetime.now().isoformat()})
        save(TASKS_F, tasks)
        self.task_entry.delete(0, "end")
        self._render_tasks()

    def _toggle_task(self, tid):
        tasks = load(TASKS_F)
        for t in tasks:
            if t["id"] == tid: t["done"] = not t["done"]
        save(TASKS_F, tasks)
        self._render_tasks()

    def _delete_task(self, tid):
        save(TASKS_F, [t for t in load(TASKS_F) if t["id"] != tid])
        self._render_tasks()

    def _render_tasks(self):
        for w in self.task_scroll.winfo_children(): w.destroy()
        tasks  = load(TASKS_F)
        active = [t for t in tasks if not t.get("done")]
        done   = [t for t in tasks if t.get("done")]

        if not tasks:
            ctk.CTkLabel(self.task_scroll, text="No tasks yet — add one below!",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 12)).pack(pady=30)
            return

        # Show top suggestion
        if active:
            top = active[0]
            self.task_suggest.configure(text=f"⚡ Focus: {top['text']}")
            self.task_suggest.pack(fill="x", padx=8, pady=(6, 0))
        else:
            self.task_suggest.pack_forget()

        PDOT = {"high": RED, "medium": YELLOW, "low": GREEN}
        for t in active: self._task_row(t, PDOT)
        if done:
            ctk.CTkLabel(self.task_scroll, text=f"Completed ({len(done)})",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 10)).pack(anchor="w", padx=4, pady=(8,2))
            for t in done[:5]: self._task_row(t, PDOT)

    def _toggle_expand(self, tid):
        if tid in self._expanded_tasks:
            self._expanded_tasks.discard(tid)
        else:
            self._expanded_tasks.add(tid)
        self._render_tasks()

    def _task_row(self, t, pdot):
        is_done  = t.get("done", False)
        is_open  = t["id"] in self._expanded_tasks
        text     = t["text"]
        preview  = text if len(text) <= 38 else text[:36] + "…"

        # ── Outer card ────────────────────────────────────────────────────────
        outer = ctk.CTkFrame(self.task_scroll, fg_color=CARD, corner_radius=8)
        outer.pack(fill="x", pady=2)

        # ── Compact row (always visible, fixed height 40) ─────────────────────
        row = ctk.CTkFrame(outer, fg_color="transparent", height=40)
        row.pack(fill="x")
        row.pack_propagate(False)

        # Circle checkbox (left)
        circle = ctk.CTkButton(
            row,
            text="✓" if is_done else "",
            width=22, height=22,
            corner_radius=11,          # full circle
            fg_color=GREEN if is_done else "transparent",
            hover_color=GREEN + "55",
            border_width=2,
            border_color=GREEN if is_done else MUTED,
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda tid=t["id"]: self._toggle_task(tid),
        )
        circle.pack(side="left", padx=(10, 6), pady=9)

        # Priority bar (thin left strip)
        bar_color = pdot.get(t.get("priority","medium"), YELLOW)
        ctk.CTkFrame(row, fg_color=bar_color, width=3, corner_radius=2
                     ).pack(side="left", fill="y", pady=8)

        # Task text preview — click to expand
        lbl = ctk.CTkLabel(
            row, text=preview,
            font=ctk.CTkFont("Segoe UI", 12, overstrike=is_done),
            text_color=MUTED if is_done else TEXT,
            anchor="w", cursor="hand2",
        )
        lbl.pack(side="left", fill="x", expand=True, padx=(6, 2))
        lbl.bind("<Button-1>", lambda _, tid=t["id"]: self._toggle_expand(tid))

        # Step count badge
        steps = t.get("steps", [])
        if steps:
            done_steps = sum(1 for s in steps if s.get("done"))
            badge_color = GREEN if done_steps == len(steps) else ACCENT
            ctk.CTkLabel(row, text=f"{done_steps}/{len(steps)}",
                         font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=badge_color).pack(side="right", padx=(0,2))

        # Bell + delete (right)
        has_reminder = bool(t.get("remind_at"))
        ctk.CTkButton(row, text="🔔", width=24, height=24,
                      fg_color="transparent", hover_color=SURFACE,
                      text_color=ACCENT if has_reminder else MUTED,
                      font=ctk.CTkFont(size=12),
                      command=lambda tid=t["id"]: self._open_reminder(tid)
                      ).pack(side="right", padx=(0, 2))
        ctk.CTkButton(row, text="×", width=24, height=24,
                      fg_color="transparent", hover_color="#FFE0E0",
                      text_color=MUTED, font=ctk.CTkFont(size=14),
                      command=lambda tid=t["id"]: self._delete_task(tid)
                      ).pack(side="right", padx=(0, 2))

        # ── Expanded detail (only when clicked) ───────────────────────────────
        if is_open:
            detail = ctk.CTkFrame(outer, fg_color="#F0F2F5", corner_radius=0)
            detail.pack(fill="x")

            # Full text
            ctk.CTkLabel(detail, text=text, wraplength=270, justify="left",
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=TEXT, anchor="w"
                         ).pack(anchor="w", padx=14, pady=(8, 4))

            # Reminder line
            if t.get("remind_at"):
                try:
                    rt = datetime.fromisoformat(t["remind_at"])
                    ctk.CTkLabel(detail, text=f"⏰ {rt.strftime('%d %b %H:%M')}",
                                 font=ctk.CTkFont("Segoe UI", 10),
                                 text_color=ACCENT).pack(anchor="w", padx=14)
                except Exception:
                    pass

            # ── Steps ─────────────────────────────────────────────────────────
            steps = t.get("steps", [])
            if steps:
                ctk.CTkLabel(detail, text="Steps",
                             font=ctk.CTkFont("Segoe UI", 10, "bold"),
                             text_color=MUTED).pack(anchor="w", padx=14, pady=(6,2))
            for step in steps:
                self._step_row(detail, t["id"], step)

            # Add step input
            step_inp_row = ctk.CTkFrame(detail, fg_color="transparent")
            step_inp_row.pack(fill="x", padx=10, pady=(4, 8))

            step_e = ctk.CTkEntry(step_inp_row, placeholder_text="+ Add step…",
                                   fg_color=SURFACE, border_width=1,
                                   border_color="#E4E6EB",
                                   font=ctk.CTkFont("Segoe UI", 11),
                                   text_color=TEXT, height=30)
            step_e.pack(side="left", fill="x", expand=True, padx=(0,4))
            step_e.bind("<Return>", lambda _, tid=t["id"], e=step_e: self._add_step(tid, e))

            ctk.CTkButton(step_inp_row, text="Add", width=44, height=30,
                          fg_color=ACCENT, hover_color="#1565C0",
                          text_color="white", font=ctk.CTkFont("Segoe UI", 10, "bold"),
                          corner_radius=6,
                          command=lambda tid=t["id"], e=step_e: self._add_step(tid, e)
                          ).pack(side="right")

    # ── Step helpers ───────────────────────────────────────────────────────────
    def _step_row(self, parent, tid, step):
        is_done = step.get("done", False)
        row = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        row.pack(fill="x", padx=14, pady=1)
        row.pack_propagate(False)

        # Small circle checkbox
        circle = ctk.CTkButton(
            row, text="✓" if is_done else "", width=18, height=18,
            corner_radius=9,
            fg_color=GREEN if is_done else "transparent",
            hover_color=GREEN + "55", border_width=1,
            border_color=GREEN if is_done else "#9CA3AF",
            text_color="white", font=ctk.CTkFont(size=9, weight="bold"),
            command=lambda sid=step["id"]: self._toggle_step(tid, sid))
        circle.pack(side="left", padx=(0,6))

        ctk.CTkLabel(row, text=step["text"],
                     font=ctk.CTkFont("Segoe UI", 11, overstrike=is_done),
                     text_color=MUTED if is_done else TEXT,
                     anchor="w").pack(side="left", fill="x", expand=True)

        ctk.CTkButton(row, text="×", width=18, height=18,
                      fg_color="transparent", hover_color="#FFE0E0",
                      text_color=MUTED, font=ctk.CTkFont(size=11),
                      command=lambda sid=step["id"]: self._delete_step(tid, sid)
                      ).pack(side="right")

    def _add_step(self, tid, entry_widget):
        text = entry_widget.get().strip()
        if not text: return
        tasks = load(TASKS_F)
        for t in tasks:
            if t["id"] == tid:
                t.setdefault("steps", []).append(
                    {"id": uid(), "text": text, "done": False})
        save(TASKS_F, tasks)
        entry_widget.delete(0, "end")
        self._render_tasks()

    def _toggle_step(self, tid, sid):
        tasks = load(TASKS_F)
        for t in tasks:
            if t["id"] == tid:
                for s in t.get("steps", []):
                    if s["id"] == sid: s["done"] = not s["done"]
        save(TASKS_F, tasks)
        self._render_tasks()

    def _delete_step(self, tid, sid):
        tasks = load(TASKS_F)
        for t in tasks:
            if t["id"] == tid:
                t["steps"] = [s for s in t.get("steps", []) if s["id"] != sid]
        save(TASKS_F, tasks)
        self._render_tasks()

    # ── Reminder dialog ────────────────────────────────────────────────────────
    def _open_reminder(self, tid):
        tasks = load(TASKS_F)
        t     = next((x for x in tasks if x["id"] == tid), None)
        if not t: return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Set Reminder")
        dlg.geometry("280x220")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()
        dlg.configure(fg_color=BG)

        ctk.CTkLabel(dlg, text=t["text"], wraplength=240,
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=TEXT).pack(padx=16, pady=(16,4))

        ctk.CTkLabel(dlg, text='Remind me in… (e.g. "30m", "2h", "90m")',
                     font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED).pack(padx=16)

        inp = ctk.CTkEntry(dlg, placeholder_text="e.g. 30m or 2h",
                           font=ctk.CTkFont("Segoe UI", 13), height=36,
                           fg_color=SURFACE, border_color=ACCENT)
        inp.pack(padx=16, pady=8, fill="x")
        inp.focus()

        # If reminder already set, show current
        if t.get("remind_at"):
            try:
                rt = datetime.fromisoformat(t["remind_at"])
                inp.insert(0, rt.strftime("%d %b %H:%M"))
            except Exception:
                pass

        def _set(_=None):
            raw = inp.get().strip().lower()
            try:
                if raw.endswith("m"):
                    mins = int(raw[:-1])
                elif raw.endswith("h"):
                    mins = int(raw[:-1]) * 60
                else:
                    dlg.destroy(); return
                remind_at = (datetime.now() + timedelta(minutes=mins)).isoformat()
                for x in tasks:
                    if x["id"] == tid: x["remind_at"] = remind_at
                save(TASKS_F, tasks)
                dlg.destroy()
                self._render_tasks()
                toast("Reminder set ✅",
                      f"Will remind you about: {t['text'][:50]} in {raw}")
            except ValueError:
                pass

        def _clear():
            for x in tasks:
                if x["id"] == tid: x.pop("remind_at", None)
            save(TASKS_F, tasks)
            dlg.destroy()
            self._render_tasks()

        row_btns = ctk.CTkFrame(dlg, fg_color="transparent")
        row_btns.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(row_btns, text="Clear", width=80, height=32,
                      fg_color=CARD, hover_color=SURFACE,
                      text_color=MUTED, command=_clear).pack(side="left")
        ctk.CTkButton(row_btns, text="Set Reminder", height=32,
                      fg_color=ACCENT, hover_color="#4070cc",
                      command=_set).pack(side="right")
        inp.bind("<Return>", _set)

    # ── Background reminder checker ────────────────────────────────────────────
    def _start_reminder_checker(self):
        def _check():
            while True:
                try:
                    tasks   = load(TASKS_F)
                    changed = False
                    now     = datetime.now()
                    for t in tasks:
                        ra = t.get("remind_at")
                        if ra and not t.get("done") and not t.get("reminded"):
                            try:
                                if datetime.fromisoformat(ra) <= now:
                                    toast("⏰ Reminder — Personal OS", t["text"][:80])
                                    t["reminded"] = True
                                    changed = True
                            except Exception:
                                pass
                    if changed:
                        save(TASKS_F, tasks)
                        self.after(0, self._render_tasks)
                except Exception:
                    pass
                import time; time.sleep(30)

        threading.Thread(target=_check, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # BUY TAB
    # ══════════════════════════════════════════════════════════════════════════
    def _build_buy_tab(self):
        f = self._frames["buy"]
        self._buy_filter = "all"

        # Filter pills
        pill_row = ctk.CTkFrame(f, fg_color="transparent")
        pill_row.pack(fill="x", padx=8, pady=(8, 4))
        self._buy_pills = {}
        for label, key in [("All","all"),("🔴 Urgent","urgent"),("🛒 Grocery","groceries"),("💭 Someday","someday")]:
            b = ctk.CTkButton(pill_row, text=label, width=72, height=24,
                              fg_color=ACCENT if key=="all" else CARD,
                              hover_color="#E4E6EB", text_color="white",
                              font=ctk.CTkFont("Segoe UI", 10), corner_radius=12,
                              command=lambda k=key: self._buy_filter_switch(k))
            b.pack(side="left", padx=2)
            self._buy_pills[key] = b

        self.buy_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent",
                                                  scrollbar_button_color=SURFACE)
        self.buy_scroll.pack(fill="both", expand=True, padx=8)

        inp_row = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12)
        inp_row.pack(fill="x", padx=8, pady=8)

        self.buy_entry = ctk.CTkEntry(inp_row, placeholder_text="Add item…",
                                      fg_color="transparent", border_width=0,
                                      font=ctk.CTkFont("Segoe UI", 13),
                                      text_color=TEXT, placeholder_text_color=MUTED, height=38)
        self.buy_entry.pack(side="left", fill="x", expand=True, padx=(10,0))
        self.buy_entry.bind("<Return>", self._add_buy)

        ctk.CTkButton(inp_row, text="+", width=36, height=36,
                      fg_color=ACCENT, hover_color="#4070cc",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      corner_radius=8, command=self._add_buy).pack(side="right", padx=4, pady=3)

    def _buy_filter_switch(self, key):
        self._buy_filter = key
        for k, b in self._buy_pills.items():
            b.configure(fg_color=ACCENT if k == key else CARD)
        self._render_buy()

    def _add_buy(self, _=None):
        text = self.buy_entry.get().strip()
        if not text: return
        items = load(BUY_F)
        items.append({"id": uid(), "name": text, "cat": self._buy_filter if self._buy_filter != "all" else "someday",
                      "bought": False, "createdAt": datetime.now().isoformat()})
        save(BUY_F, items)
        self.buy_entry.delete(0, "end")
        self._render_buy()

    def _toggle_buy(self, iid):
        items = load(BUY_F)
        for i in items:
            if i["id"] == iid: i["bought"] = not i["bought"]
        save(BUY_F, items)
        self._render_buy()

    def _delete_buy(self, iid):
        save(BUY_F, [i for i in load(BUY_F) if i["id"] != iid])
        self._render_buy()

    def _render_buy(self):
        for w in self.buy_scroll.winfo_children(): w.destroy()
        items = load(BUY_F)
        if self._buy_filter != "all":
            items = [i for i in items if i.get("cat") == self._buy_filter]
        active = [i for i in items if not i.get("bought")]
        bought = [i for i in items if i.get("bought")]

        CAT_COLOR = {"urgent": RED, "groceries": GREEN, "someday": MUTED}
        CAT_ICON  = {"urgent":"🔴","groceries":"🛒","someday":"💭"}

        if not items:
            ctk.CTkLabel(self.buy_scroll, text="Nothing here — add something!",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 12)).pack(pady=30)
            return

        for i in active: self._buy_row(i, CAT_COLOR, CAT_ICON)
        if bought:
            ctk.CTkLabel(self.buy_scroll, text=f"Bought ({len(bought)})",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 10)).pack(anchor="w", padx=4, pady=(8,2))
            for i in bought: self._buy_row(i, CAT_COLOR, CAT_ICON)

    def _buy_row(self, i, cat_color, cat_icon):
        row = ctk.CTkFrame(self.buy_scroll, fg_color=CARD, corner_radius=8, height=40)
        row.pack(fill="x", pady=2); row.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(row, text=cat_icon.get(i.get("cat","someday"),"💭"),
                                 font=ctk.CTkFont(size=13), width=24)
        icon_lbl.pack(side="left", padx=(8,2))

        lbl = ctk.CTkLabel(row, text=i["name"],
                           font=ctk.CTkFont("Segoe UI", 12, overstrike=i.get("bought",False)),
                           text_color=MUTED if i.get("bought") else TEXT,
                           anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=4)
        lbl.bind("<Button-1>", lambda _, iid=i["id"]: self._toggle_buy(iid))

        ctk.CTkButton(row, text="×", width=24, height=24,
                      fg_color="transparent", hover_color="#FFE0E0",
                      text_color=MUTED, font=ctk.CTkFont(size=14),
                      command=lambda iid=i["id"]: self._delete_buy(iid)
                      ).pack(side="right", padx=4)

    # ══════════════════════════════════════════════════════════════════════════
    # JOBS TAB
    # ══════════════════════════════════════════════════════════════════════════

    # Keywords to detect application status from email subject/body
    STATUS_KW = {
        "offer":     ["offer letter","pleased to offer","congratulations","you have been selected",
                      "formal offer","job offer","we would like to offer"],
        "interview": ["interview","schedule a call","phone screen","video interview",
                      "meet with our team","next round","technical round","hiring manager"],
        "screening": ["recruiter","initial screening","preliminary","brief call",
                      "connect with you","next steps","shortlisted"],
        "rejected":  ["unfortunately","not moving forward","other candidates",
                      "regret to inform","not selected","not proceed",
                      "position has been filled","we won't be","will not be moving"],
        "applied":   ["received your application","thank you for applying",
                      "application submitted","we have received","application confirmation",
                      "successfully applied","your application for"],
    }

    # ── Settings / onboarding dialog ───────────────────────────────────────────
    def _open_settings_dialog(self, first_run=False):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Welcome to Personal OS" if first_run else "Settings")
        dlg.geometry("360x460")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()
        dlg.configure(fg_color=BG)

        # Header
        ctk.CTkLabel(dlg,
                     text="Welcome to Personal OS" if first_run else "Settings",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=TEXT).pack(padx=20, pady=(18, 4))
        ctk.CTkLabel(dlg,
                     text="Your data stays local. Each user needs their own\nGoogle credentials (see README for setup).",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED,
                     justify="center").pack(padx=20, pady=(0, 12))

        # Name
        ctk.CTkLabel(dlg, text="Your name", font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x", padx=20)
        name_e = ctk.CTkEntry(dlg, placeholder_text="e.g. Pradeep",
                              font=ctk.CTkFont("Segoe UI", 12), height=34,
                              fg_color=SURFACE, text_color=TEXT)
        name_e.pack(fill="x", padx=20, pady=(2, 10))
        if not first_run:
            name_e.insert(0, self.settings.get("name", ""))

        # Gmail accounts
        ctk.CTkLabel(dlg, text="Gmail accounts for job sync (one per line)",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x", padx=20)
        ctk.CTkLabel(dlg, text="Leave blank to skip Gmail sync",
                     font=ctk.CTkFont("Segoe UI", 10), text_color=MUTED,
                     anchor="w").pack(fill="x", padx=20)
        accounts_box = ctk.CTkTextbox(dlg, height=80,
                                      font=ctk.CTkFont("Segoe UI", 11),
                                      fg_color=SURFACE, text_color=TEXT,
                                      border_width=1, border_color="#E4E6EB")
        accounts_box.pack(fill="x", padx=20, pady=(2, 10))
        if not first_run and self.gmail_accounts:
            accounts_box.insert("1.0", "\n".join(self.gmail_accounts))

        # Daily job application goal
        ctk.CTkLabel(dlg, text="Daily job application goal",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x", padx=20)
        goal_e = ctk.CTkEntry(dlg, placeholder_text="20",
                              font=ctk.CTkFont("Segoe UI", 12), height=34,
                              fg_color=SURFACE, text_color=TEXT)
        goal_e.pack(fill="x", padx=20, pady=(2, 10))
        goal_e.insert(0, str(self.settings.get("jobs_goal", 20)))

        err_lbl = ctk.CTkLabel(dlg, text="", font=ctk.CTkFont("Segoe UI", 10),
                               text_color=RED)
        err_lbl.pack()

        def _save():
            name = name_e.get().strip()
            if not name:
                err_lbl.configure(text="Name is required."); return
            raw      = accounts_box.get("1.0", "end").strip()
            accounts = [e.strip() for e in raw.splitlines() if e.strip()]
            try:    goal = int(goal_e.get().strip())
            except: goal = 20

            self.settings["name"]          = name
            self.settings["gmail_accounts"] = accounts
            self.settings["jobs_goal"]      = goal
            save(SETTINGS_F, self.settings)
            self.gmail_accounts = accounts
            dlg.destroy()
            if not first_run:
                self._rebuild_jobs_tab()

        ctk.CTkButton(dlg, text="Save & Continue" if first_run else "Save",
                      height=36, fg_color=ACCENT, hover_color="#1565C0",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      corner_radius=8, command=_save).pack(fill="x", padx=20, pady=(4, 16))

        self.wait_window(dlg)

    def _rebuild_jobs_tab(self):
        """Tear down and rebuild the Jobs tab after settings change."""
        f = self._frames["jobs"]
        for w in f.winfo_children():
            w.destroy()
        # Reset all jobs-tab state
        self._gmail_status       = {}
        self._jobs_past_expanded = False
        self._gmail_acc_lbls     = {}
        self._gmail_acc_btns     = {}
        self._build_jobs_tab()
        self._render_jobs()

    def _build_jobs_tab(self):
        f = self._frames["jobs"]
        self._gmail_status       = {}
        self._jobs_past_expanded = False

        # ── Gmail sync panel ──────────────────────────────────────────────────
        gmail_panel = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12)
        gmail_panel.pack(fill="x", padx=8, pady=(8,4))

        hdr = ctk.CTkFrame(gmail_panel, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8,4))
        ctk.CTkLabel(hdr, text="Gmail Sync",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color=TEXT).pack(side="left")
        self.gmail_sync_btn = ctk.CTkButton(
            hdr, text="Sync All", width=72, height=26,
            fg_color=ACCENT, hover_color="#1565C0",
            font=ctk.CTkFont("Segoe UI", 10, "bold"), corner_radius=6,
            command=lambda: threading.Thread(target=self._gmail_sync_all, daemon=True).start())
        self.gmail_sync_btn.pack(side="right")
        self.gmail_last_sync_lbl = ctk.CTkLabel(hdr, text="",
                                                  font=ctk.CTkFont("Segoe UI", 10),
                                                  text_color=MUTED)
        self.gmail_last_sync_lbl.pack(side="right", padx=6)

        # One row per account
        self._gmail_acc_lbls = {}
        self._gmail_acc_btns = {}
        for i, email in enumerate(self.gmail_accounts):
            row = ctk.CTkFrame(gmail_panel, fg_color="transparent", height=28)
            row.pack(fill="x", padx=10, pady=2)
            row.pack_propagate(False)
            lbl = ctk.CTkLabel(row, text=f"○  {email}",
                               font=ctk.CTkFont("Segoe UI", 10), text_color=MUTED,
                               anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            btn = ctk.CTkButton(row, text="Connect", width=64, height=22,
                                fg_color=CARD, hover_color="#E4E6EB",
                                text_color=ACCENT, font=ctk.CTkFont("Segoe UI", 9, "bold"),
                                corner_radius=6,
                                command=lambda idx=i: threading.Thread(
                                    target=self._gmail_auth, args=(idx,), daemon=True).start())
            btn.pack(side="right")
            self._gmail_acc_lbls[i] = lbl
            self._gmail_acc_btns[i] = btn
        ctk.CTkFrame(gmail_panel, height=6, fg_color="transparent").pack()

        # ── Counter ───────────────────────────────────────────────────────────
        goal = self.settings.get("jobs_goal", 20)
        top  = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12)
        top.pack(fill="x", padx=8, pady=4)

        count_row = ctk.CTkFrame(top, fg_color="transparent")
        count_row.pack(fill="x", padx=14, pady=(10,4))
        self.jobs_count_lbl = ctk.CTkLabel(count_row, text="0",
                                            font=ctk.CTkFont("Segoe UI", 32, "bold"),
                                            text_color=ACCENT)
        self.jobs_count_lbl.pack(side="left")
        ctk.CTkLabel(count_row, text=f"/{goal} today",
                     font=ctk.CTkFont("Segoe UI", 13), text_color=MUTED
                     ).pack(side="left", padx=4, pady=6)
        self.jobs_streak_lbl = ctk.CTkLabel(count_row, text="",
                                             font=ctk.CTkFont("Segoe UI", 12), text_color=YELLOW)
        self.jobs_streak_lbl.pack(side="right", padx=4)

        self.jobs_bar = ctk.CTkProgressBar(top, height=6, corner_radius=3,
                                            fg_color=CARD, progress_color=ACCENT)
        self.jobs_bar.set(0)
        self.jobs_bar.pack(fill="x", padx=14, pady=(0,10))

        # Heatmap
        self.heat_frame = ctk.CTkFrame(f, fg_color="transparent")
        self.heat_frame.pack(fill="x", padx=8, pady=2)

        # Recent list
        self.jobs_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent",
                                                    scrollbar_button_color=SURFACE)
        self.jobs_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Manual input
        inp_row = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12)
        inp_row.pack(fill="x", padx=8, pady=8)
        self.jobs_entry = ctk.CTkEntry(inp_row, placeholder_text="Company — Role (Enter to log)",
                                       fg_color="transparent", border_width=0,
                                       font=ctk.CTkFont("Segoe UI", 12),
                                       text_color=TEXT, placeholder_text_color=MUTED, height=38)
        self.jobs_entry.pack(side="left", fill="x", expand=True, padx=(10,0))
        self.jobs_entry.bind("<Return>", self._add_job)
        ctk.CTkButton(inp_row, text="+", width=36, height=36,
                      fg_color=ACCENT, hover_color="#1565C0",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      corner_radius=8, command=self._add_job).pack(side="right", padx=4, pady=3)

        # Auto-reconnect previously authenticated accounts
        threading.Thread(target=self._gmail_auto_reconnect, daemon=True).start()

    # ── Gmail auth ─────────────────────────────────────────────────────────────
    def _gmail_auto_reconnect(self):
        for i, email in enumerate(self.gmail_accounts):
            token_path = os.path.join(BASE, f"gmail_token_{i}.json")
            creds_path = os.path.join(BASE, "credentials.json")
            if os.path.exists(token_path) and os.path.exists(creds_path):
                self._gmail_auth(i, silent=True)

    def _gmail_auth(self, idx, silent=False):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES     = ["https://www.googleapis.com/auth/gmail.readonly"]
        token_path = os.path.join(BASE, f"gmail_token_{idx}.json")
        creds_path = os.path.join(BASE, "credentials.json")
        email      = self.gmail_accounts[idx]

        if not os.path.exists(creds_path):
            self.after(0, lambda: self._gmail_set_status(idx, "No credentials.json", False))
            return

        creds = None
        if os.path.exists(token_path):
            try:   creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception: creds = None

        if not creds or not creds.valid:
            if silent: return   # Don't pop browser silently
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow  = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0, login_hint=email)
                with open(token_path, "w") as fh: fh.write(creds.to_json())
            except Exception as e:
                self.after(0, lambda: self._gmail_set_status(idx, f"Auth failed", False))
                return

        try:
            svc = build("gmail", "v1", credentials=creds)
            # Quick test call
            svc.users().getProfile(userId="me").execute()
            self._gmail_status[idx] = svc
            self.after(0, lambda: self._gmail_set_status(idx, "Connected", True))
        except Exception as e:
            self.after(0, lambda: self._gmail_set_status(idx, "Error", False))

    def _gmail_set_status(self, idx, text, ok):
        email = self.gmail_accounts[idx]
        dot   = "●" if ok else "○"
        color = GREEN if ok else MUTED
        self._gmail_acc_lbls[idx].configure(text=f"{dot}  {email}", text_color=color)
        self._gmail_acc_btns[idx].configure(text="Re-auth" if ok else "Connect")

    # ── Gmail sync ─────────────────────────────────────────────────────────────
    def _gmail_sync_all(self):
        self.after(0, lambda: self.gmail_sync_btn.configure(text="Syncing…", state="disabled"))
        total = 0
        for idx, svc in self._gmail_status.items():
            if svc and hasattr(svc, "_baseUrl"):
                total += self._gmail_sync_account(idx, svc)
        now_str = datetime.now().strftime("%H:%M")
        self.after(0, lambda: self.gmail_sync_btn.configure(text="Sync All", state="normal"))
        self.after(0, lambda: self.gmail_last_sync_lbl.configure(text=f"Last: {now_str} (+{total})"))
        self.after(0, self._render_jobs)

    def _gmail_sync_account(self, idx, svc):
        """Fetch job-related emails and add to jobs.json. Returns count of new entries."""
        processed_f = os.path.join(BASE, "gmail_processed.json")
        processed   = set(load(processed_f, []))

        # Tight query: only unambiguous application confirmation phrases
        query = (
            'subject:("application received" OR "thank you for applying" OR '
            '"thank you for your application" OR "your application has been" OR '
            '"application confirmation" OR "successfully applied" OR '
            '"we received your application" OR "we received your job application" OR '
            '"received your job application" OR "your job application" OR '
            '"application submitted" OR "application for" OR '
            '"invitation to interview" OR "interview request" OR '
            '"interview invitation" OR "offer letter" OR "job offer" OR '
            '"not moving forward" OR "we regret to inform") newer_than:180d'
        )
        try:
            res  = svc.users().messages().list(userId="me", q=query, maxResults=500).execute()
            msgs = res.get("messages", [])
        except Exception:
            return 0

        jobs    = load(JOBS_F)
        new_ids = set()
        added   = 0

        for m in msgs:
            mid = m["id"]
            if mid in processed: continue
            try:
                full = svc.users().messages().get(
                    userId="me", id=mid, format="metadata",
                    metadataHeaders=["Subject","From","Date"]).execute()
                hdrs      = {h["name"]: h["value"] for h in full["payload"]["headers"]}
                subject   = hdrs.get("Subject", "")
                sender    = hdrs.get("From", "")
                snippet   = full.get("snippet", "")
                date_raw  = hdrs.get("Date", "")
                thread_id = full.get("threadId", "")

                # ── Strict real-application gate ──────────────────────────────
                if not self._is_real_application(subject, snippet, sender):
                    new_ids.add(mid)   # mark as seen so we skip it next time
                    continue

                company, role = self._extract_company(sender, subject)
                if company in ("Unknown", ""):
                    new_ids.add(mid); continue

                status   = self._detect_status(subject + " " + snippet)
                date_str = self._parse_email_date(date_raw)

                # Deduplicate by Gmail message ID
                if any(j.get("gmail_id") == mid for j in jobs):
                    new_ids.add(mid); continue

                jobs.append({
                    "id":           uid(),
                    "company":      company,
                    "role":         role,
                    "status":       status,
                    "date":         date_str,
                    "source":       self.gmail_accounts[idx],
                    "gmail_id":     mid,
                    "gmail_thread": thread_id,
                    "gmail_acct":   idx,
                })
                added += 1
                new_ids.add(mid)
            except Exception:
                pass

        save(JOBS_F, jobs)
        save(processed_f, list(processed | new_ids))
        return added

    def _is_real_application(self, subject, snippet, sender):
        """Return True only for genuine job application emails."""
        text = (subject + " " + snippet).lower()

        # Hard exclusions — these are never real applications
        EXCLUDE = [
            "was sent to", "shared their profile", "new job alert", "jobs you might like",
            "job recommendation", "you may know", "connection request", "invitation to connect",
            "people viewed your", "profile view", "work anniversary", "birthday",
            "endorsement", "skill endorsement", "newsletter", "unsubscribe from",
            "weekly digest", "job matches for", "people are applying", "trending jobs",
            "salary insights", "open to work", "your network update", "congratulations on your new",
            "referral bonus", "staffing", "we found a candidate", "talent pipeline",
            "resume review", "career fair", "webinar", "free trial", "pricing",
        ]
        if any(p in text for p in EXCLUDE):
            return False

        # Must have at least one strong application signal in SUBJECT (not just snippet)
        subj = subject.lower()
        STRONG = [
            "application received", "thank you for applying", "thank you for your application",
            "your application has been", "application confirmation", "successfully applied",
            "we received your application", "we received your job application",
            "received your job application", "your job application", "application submitted",
            "application for", "applied for the position",
            "invitation to interview", "interview request", "interview scheduled",
            "phone screen", "video interview",
            "offer letter", "job offer", "pleased to offer",
            "not moving forward", "unfortunately", "regret to inform",
            "not selected", "position has been filled",
        ]
        return any(s in subj for s in STRONG)

    # ── Email parsing helpers ──────────────────────────────────────────────────
    def _detect_status(self, text):
        t = text.lower()
        for status, keywords in self.STATUS_KW.items():
            if any(kw in t for kw in keywords):
                return status
        return "applied"

    def _extract_company(self, sender, subject):
        import re
        role = ""

        # Known ATS / job platform senders → extract company from subject
        ats_domains = ["greenhouse.io","lever.co","workday.com","myworkdayjobs.com",
                       "taleo.net","icims.com","smartrecruiters.com","jobvite.com",
                       "linkedin.com","indeed.com","naukri.com","wellfound.com",
                       "oracle.com","cloud.oracle.com","successfactors.com",
                       "sap.com","recruitingbypaycor.com","paylocity.com",
                       "ultipro.com","kronos.com","bamboohr.com","ashbyhq.com"]

        # ── Try display name first (e.g. "JPMorgan Chase & Co. HR <no-reply@ats.com>")
        display_match = re.match(r'^([^<@\n]{3,60}?)\s*<', sender)
        display_name  = display_match.group(1).strip() if display_match else ""
        # Strip generic HR/recruiting suffixes from display name
        HR_SUFFIXES = r'\s*[\-–|,]?\s*(?:human resources?|talent acquisition|recruiting|hr|careers?|no.?reply|hiring|jobs?|notifications?|noreply|do not reply).*$'
        if display_name:
            cleaned = re.sub(HR_SUFFIXES, "", display_name, flags=re.IGNORECASE).strip(" .,&")
            # Accept if it looks like a real company name (not just a person's name or generic word)
            GENERIC_NAMES = {"careers", "recruiting", "hr", "jobs", "noreply", "hiring", "notifications"}
            if cleaned and cleaned.lower() not in GENERIC_NAMES and len(cleaned) >= 3:
                company = cleaned.title() if cleaned.isupper() else cleaned
                # Still try to extract role from subject before returning
                role_m = re.search(
                    r'(?:for(?: the)?|position[: ]+|role[: ]+)\s*([A-Za-z][^\-\|,@]{3,45}?)(?=\s+(?:at|with|to|@|in)\b|\s*[\-\|,]|$)',
                    subject, re.IGNORECASE)
                if role_m:
                    role = role_m.group(1).strip()
                    ROLE_JUNK = {"your application","you for applying","the position","our team","this opportunity"}
                    if any(j in role.lower() for j in ROLE_JUNK):
                        role = ""
                return company, role

        # Try to get domain from sender
        domain_match = re.search(r'@([\w.\-]+)', sender)
        domain = domain_match.group(1).lower() if domain_match else ""

        # Strip common prefixes from domain to get company name
        for ats in ats_domains:
            if ats in domain:
                # Fall through to subject parsing
                domain = ""
                break

        if domain:
            # Strip TLD suffixes, then split on dots — company name is the rightmost segment
            stripped = domain.replace(".com","").replace(".co","").replace(".io","").replace(".net","").replace(".org","")
            parts = [p for p in stripped.split(".") if p]
            # parts[-1] is the company (subdomains like "mail","careers","noreply" come before it)
            name = parts[-1] if parts else ""
            # If last part is still a generic prefix (rare), fall back one level
            GENERIC = {"mail","jobs","careers","hr","recruiting","noreply","no-reply","email","apply","applications","info","support"}
            if name.lower() in GENERIC and len(parts) > 1:
                name = parts[-2]
            # Skip 2-char country codes (e.g. ".in", ".uk" leftover)
            if len(name) <= 2 and len(parts) > 1:
                name = parts[-2]
            company = name.title()
        else:
            # Parse from subject: "Your application at/to/with COMPANY"
            m = re.search(
                r'(?:application (?:at|to|with|for)|applied (?:at|to)|position at|role at)\s+([A-Z][^\s,]+(?:\s[A-Z][^\s,]+)?)',
                subject, re.IGNORECASE)
            company = m.group(1).strip() if m else re.sub(
                r'(?i)(your application|application received|thank you|re:|fw:)', "", subject
            ).strip()[:40]

        # Try to extract role from subject — stop at company prepositions
        role_m = re.search(
            r'(?:for(?: the)?|position[: ]+|role[: ]+)\s*([A-Za-z][^\-\|,@]{3,45}?)(?=\s+(?:at|with|to|@|in)\b|\s*[\-\|,]|$)',
            subject, re.IGNORECASE)
        if role_m:
            role = role_m.group(1).strip()
            # Reject if role looks like generic text, not an actual job title
            ROLE_JUNK = {"your application", "you for applying", "the position", "our team", "this opportunity"}
            if any(j in role.lower() for j in ROLE_JUNK):
                role = ""

        return company or "Unknown", role

    def _parse_email_date(self, date_raw):
        import email.utils
        try:
            t = email.utils.parsedate_to_datetime(date_raw)
            return t.strftime("%Y-%m-%d")
        except Exception:
            return today_str()

    def _add_job(self, _=None):
        text = self.jobs_entry.get().strip()
        if not text: return
        parts = [p.strip() for p in text.split("—", 1)]
        company = parts[0]
        role    = parts[1] if len(parts) > 1 else ""
        jobs    = load(JOBS_F)
        jobs.append({"id": uid(), "company": company, "role": role,
                     "status": "applied", "date": today_str()})
        save(JOBS_F, jobs)
        self.jobs_entry.delete(0, "end")
        self._render_jobs()

    def _delete_job(self, jid):
        save(JOBS_F, [j for j in load(JOBS_F) if j["id"] != jid])
        self._render_jobs()

    def _fmt_job_time(self, jid):
        try:
            return datetime.strptime(jid[:14], "%Y%m%d%H%M%S").strftime("%H:%M")
        except Exception:
            return ""

    def _render_jobs(self):
        import webbrowser as _wb
        jobs  = load(JOBS_F)
        goal  = self.settings.get("jobs_goal", 20)
        today = today_str()

        today_jobs = sorted([j for j in jobs if j.get("date") == today],
                            key=lambda x: x["id"], reverse=True)
        past_jobs  = sorted([j for j in jobs if j.get("date") != today],
                            key=lambda x: (x.get("date",""), x["id"]), reverse=True)
        cnt_today  = len(today_jobs)

        self.jobs_count_lbl.configure(text=str(cnt_today))
        self.jobs_bar.set(min(cnt_today / goal, 1.0) if goal else 0)

        # ── Streak ────────────────────────────────────────────────────────────
        by_date = {}
        for j in jobs:
            by_date[j.get("date","")] = by_date.get(j.get("date",""), 0) + 1
        streak = 0
        d = date.today() - timedelta(days=1)
        while by_date.get(d.isoformat(), 0) >= goal:
            streak += 1; d -= timedelta(days=1)
        self.jobs_streak_lbl.configure(text=f"🔥 {streak}d" if streak else "")

        # ── Heatmap (last 28 days) ─────────────────────────────────────────────
        for w in self.heat_frame.winfo_children(): w.destroy()
        LEVELS = ["#E4E6EB","#c7d7fc","#93abf9","#6b88f7","#1877F2"]
        hrow = ctk.CTkFrame(self.heat_frame, fg_color="transparent")
        hrow.pack(anchor="w", padx=4)
        for i in range(27, -1, -1):
            d2  = date.today() - timedelta(days=i)
            cnt = by_date.get(d2.isoformat(), 0)
            lvl = 0 if cnt == 0 else 1 if cnt < 5 else 2 if cnt < 10 else 3 if cnt < 20 else 4
            ctk.CTkFrame(hrow, fg_color=LEVELS[lvl], width=10, height=10,
                         corner_radius=2).pack(side="left", padx=1, pady=1)

        # ── List area ─────────────────────────────────────────────────────────
        for w in self.jobs_scroll.winfo_children(): w.destroy()

        STATUS_COLOR = {
            "applied":   "#4338ca", "screening": "#a16207",
            "interview": "#15803d", "offer":     "#065f46",
            "rejected":  "#b91c1c",
        }

        def _make_row(parent, j, show_date=False):
            row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8, height=40)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            # Status color bar (left edge)
            sc = STATUS_COLOR.get(j.get("status","applied"), "#4338ca")
            ctk.CTkFrame(row, fg_color=sc, width=4, corner_radius=2
                         ).pack(side="left", fill="y", pady=6, padx=(6,0))

            # Company (bold)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=(8,4))

            company_lbl = ctk.CTkLabel(
                info, text=j["company"],
                font=ctk.CTkFont("Segoe UI", 12, "bold"),
                text_color=TEXT, anchor="w",
                cursor="hand2" if j.get("gmail_thread") else "arrow")
            company_lbl.pack(anchor="w")
            if j.get("gmail_thread"):
                acct = j.get("gmail_acct", 0)
                url  = f"https://mail.google.com/mail/u/{acct}/#all/{j['gmail_thread']}"
                company_lbl.bind("<Button-1>", lambda _, u=url: _wb.open(u))

            # Role (muted, small) — only if present
            if j.get("role"):
                ctk.CTkLabel(info, text=j["role"],
                             font=ctk.CTkFont("Segoe UI", 9),
                             text_color=MUTED, anchor="w").pack(anchor="w")

            # Right side: time (or date for past) + delete
            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=(0,6))

            time_str = j.get("date","") if show_date else self._fmt_job_time(j["id"])
            if time_str:
                ctk.CTkLabel(right, text=time_str,
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=MUTED).pack(anchor="e")

            ctk.CTkButton(right, text="×", width=20, height=20,
                          fg_color="transparent", hover_color="#FFE0E0",
                          text_color=MUTED, font=ctk.CTkFont(size=11),
                          command=lambda jid=j["id"]: self._delete_job(jid)
                          ).pack(anchor="e")

        # ── Today ─────────────────────────────────────────────────────────────
        if today_jobs:
            ctk.CTkLabel(self.jobs_scroll,
                         text=f"Today — {cnt_today} applied",
                         font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=ACCENT, anchor="w"
                         ).pack(anchor="w", padx=6, pady=(4,2))
            for j in today_jobs:
                _make_row(self.jobs_scroll, j, show_date=False)
        else:
            ctk.CTkLabel(self.jobs_scroll, text="No applications logged today",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11)
                         ).pack(pady=12)

        # ── Past dropdown ──────────────────────────────────────────────────────
        if past_jobs:
            arrow = "▼" if self._jobs_past_expanded else "▶"

            def _toggle_past():
                self._jobs_past_expanded = not self._jobs_past_expanded
                self._render_jobs()

            ctk.CTkButton(
                self.jobs_scroll,
                text=f"{arrow}  Past applications ({len(past_jobs)})",
                height=30, fg_color="transparent", hover_color=CARD,
                text_color=MUTED, font=ctk.CTkFont("Segoe UI", 10, "bold"),
                anchor="w", corner_radius=8,
                command=_toggle_past
            ).pack(fill="x", padx=2, pady=(10, 2))

            if self._jobs_past_expanded:
                for j in past_jobs:
                    _make_row(self.jobs_scroll, j, show_date=True)

    # ══════════════════════════════════════════════════════════════════════════
    # ASSETS TAB
    # ══════════════════════════════════════════════════════════════════════════

    # Category definitions: key -> (label, dot colour)
    ASSET_CATS = {
        "gold":    ("Gold",          "#F59E0B"),
        "silver":  ("Silver",        "#9CA3AF"),
        "cash":    ("Cash / Bank",   "#22C55E"),
        "stocks":  ("Stocks",        "#3B82F6"),
        "mf":      ("Mutual Funds",  "#8B5CF6"),
        "crypto":  ("Crypto",        "#F97316"),
        "fd":      ("FD / RD",       "#06B6D4"),
        "other":   ("Other",         "#6B7280"),
    }

    def _build_assets_tab(self):
        f = self._frames["assets"]

        # Net worth banner
        nw = ctk.CTkFrame(f, fg_color="#1877F2", corner_radius=12)
        nw.pack(fill="x", padx=8, pady=(8,4))
        ctk.CTkLabel(nw, text="Total Net Worth",
                     font=ctk.CTkFont("Segoe UI", 11), text_color="#E7F3FF"
                     ).pack(anchor="w", padx=14, pady=(8,0))
        nw_row = ctk.CTkFrame(nw, fg_color="transparent")
        nw_row.pack(fill="x", padx=14, pady=(0,8))
        self.nw_val = ctk.CTkLabel(nw_row, text="₹0",
                                    font=ctk.CTkFont("Segoe UI", 24, "bold"), text_color="white")
        self.nw_val.pack(side="left")
        ctk.CTkButton(nw_row, text="🔄", width=28, height=24,
                      fg_color="transparent", hover_color="#1565C0",
                      text_color="white", font=ctk.CTkFont(size=13),
                      corner_radius=6,
                      command=lambda: threading.Thread(target=self._fetch_gold, daemon=True).start()
                      ).pack(side="right")

        self.assets_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent",
                                                     scrollbar_button_color=SURFACE)
        self.assets_scroll.pack(fill="both", expand=True, padx=8, pady=(4,0))

        # Add button
        ctk.CTkButton(f, text="+ Add Asset", height=34,
                      fg_color=ACCENT, hover_color="#1565C0",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      corner_radius=8,
                      command=self._open_add_asset).pack(fill="x", padx=8, pady=8)

    def _open_add_asset(self, prefill=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add Asset")
        dlg.geometry("300x320")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()
        dlg.configure(fg_color=BG)

        ctk.CTkLabel(dlg, text="Add Asset",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=TEXT
                     ).pack(padx=16, pady=(14,8))

        # Name
        name_e = ctk.CTkEntry(dlg, placeholder_text="Name (e.g. HDFC Nifty 50)",
                               font=ctk.CTkFont("Segoe UI", 12), height=34,
                               fg_color=SURFACE, text_color=TEXT)
        name_e.pack(fill="x", padx=16, pady=(0,6))

        # Category grid
        ctk.CTkLabel(dlg, text="Category", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=MUTED).pack(anchor="w", padx=16)
        cat_var   = ctk.StringVar(value="other")
        cat_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        cat_frame.pack(fill="x", padx=16, pady=(2,6))
        cat_btns  = {}
        for i, (key, (label, color)) in enumerate(self.ASSET_CATS.items()):
            btn = ctk.CTkButton(cat_frame, text=f"● {label}", height=26,
                                fg_color=CARD, hover_color=SURFACE,
                                text_color=MUTED,
                                font=ctk.CTkFont("Segoe UI", 10),
                                corner_radius=6,
                                command=lambda k=key: self._cat_select(k, cat_var, cat_btns))
            btn.grid(row=i//2, column=i%2, padx=2, pady=2, sticky="ew")
            cat_frame.columnconfigure(i%2, weight=1)
            cat_btns[key] = (btn, color)
        # Highlight default
        self._cat_select("other", cat_var, cat_btns)

        # Value
        val_e = ctk.CTkEntry(dlg, placeholder_text="Current value (₹)",
                              font=ctk.CTkFont("Segoe UI", 12), height=34,
                              fg_color=SURFACE, text_color=TEXT)
        val_e.pack(fill="x", padx=16, pady=(0,8))
        val_e.bind("<Return>", lambda _: _save())

        def _save():
            name = name_e.get().strip()
            if not name: return
            try:   v = float(val_e.get().strip().replace("₹","").replace(",",""))
            except: v = 0.0
            assets = load(ASSETS_F)
            assets.append({"id": uid(), "name": name, "type": cat_var.get(),
                           "manualValue": v, "updatedAt": datetime.now().isoformat()})
            save(ASSETS_F, assets)
            dlg.destroy()
            self._render_assets()

        ctk.CTkButton(dlg, text="Save", height=34,
                      fg_color=ACCENT, hover_color="#1565C0",
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      corner_radius=8, command=_save).pack(fill="x", padx=16, pady=(0,12))
        name_e.focus()

    def _cat_select(self, key, var, btns):
        var.set(key)
        for k, (btn, color) in btns.items():
            if k == key:
                btn.configure(fg_color=color, text_color="white")
            else:
                btn.configure(fg_color=CARD, text_color=MUTED)

    def _delete_asset(self, aid):
        save(ASSETS_F, [a for a in load(ASSETS_F) if a["id"] != aid])
        self._render_assets()

    def _fetch_gold(self):
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
            usd_oz  = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            usd_inr = 84.0
            try:
                req2 = urllib.request.Request("https://open.er-api.com/v6/latest/USD",
                                               headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=5) as r2:
                    usd_inr = json.loads(r2.read())["rates"]["INR"]
            except Exception: pass
            self._gold_price = (usd_oz / 31.1035) * usd_inr
            assets = load(ASSETS_F)
            for a in assets:
                if a.get("type") == "gold": a["goldPrice"] = self._gold_price
            save(ASSETS_F, assets)
            self.after(0, self._render_assets)
        except Exception: pass

    def _render_assets(self):
        for w in self.assets_scroll.winfo_children(): w.destroy()
        assets = load(ASSETS_F)

        # Compute total
        total = 0
        for a in assets:
            if a.get("type") == "gold":
                total += a.get("qty", 0) * a.get("goldPrice", a.get("buyPrice", 0))
            else:
                total += a.get("manualValue", 0)
        self.nw_val.configure(text=fmt_inr(total))

        if not assets:
            ctk.CTkLabel(self.assets_scroll, text="Add your first asset below",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 12)).pack(pady=30)
            return

        for a in assets:
            cat    = a.get("type", "other")
            _, dot_color = self.ASSET_CATS.get(cat, ("Other", "#6B7280"))

            # ── single compact row ────────────────────────────────────────────
            row = ctk.CTkFrame(self.assets_scroll, fg_color=CARD,
                               corner_radius=8, height=40)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            # Coloured category dot
            ctk.CTkFrame(row, fg_color=dot_color, width=8, height=8,
                         corner_radius=4).pack(side="left", padx=(10,6), pady=16)

            ctk.CTkLabel(row, text=a["name"],
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=TEXT, anchor="w"
                         ).pack(side="left", fill="x", expand=True)

            # Value (and gain for gold)
            if a.get("type") == "gold":
                val  = a.get("qty", 0) * a.get("goldPrice", a.get("buyPrice", 0))
                cost = a.get("qty", 0) * a.get("buyPrice", 0)
                gain = val - cost
                gain_str = f" (+{gain/cost*100:.1f}%)" if cost and gain > 0 else ""
                val_text  = fmt_inr(val) + gain_str
                val_color = GREEN if gain > 0 else ACCENT
            else:
                val       = a.get("manualValue", 0)
                val_text  = fmt_inr(val)
                val_color = ACCENT

            ctk.CTkLabel(row, text=val_text,
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=val_color
                         ).pack(side="right", padx=(0,6))

            ctk.CTkButton(row, text="×", width=22, height=22,
                          fg_color="transparent", hover_color="#FFE0E0",
                          text_color=MUTED, font=ctk.CTkFont(size=12),
                          command=lambda aid=a["id"]: self._delete_asset(aid)
                          ).pack(side="right", padx=2)

    # ══════════════════════════════════════════════════════════════════════════
    # CALENDAR TAB  — full month grid + day event panel
    # ══════════════════════════════════════════════════════════════════════════
    def _build_cal_tab(self):
        import calendar as cal_mod
        f = self._frames["cal"]
        self._cal_service      = None
        self._cal_events_cache = {}          # "YYYY-MM-DD" -> [events]
        self._cal_selected     = date.today()
        self._cal_month        = date.today().replace(day=1)

        # ── Status bar ────────────────────────────────────────────────────────
        bar = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=0, height=38)
        bar.pack(fill="x"); bar.pack_propagate(False)

        self.cal_status_lbl = ctk.CTkLabel(bar, text="Not connected",
                                            font=ctk.CTkFont("Segoe UI", 11),
                                            text_color=MUTED)
        self.cal_status_lbl.pack(side="left", padx=10)

        self.cal_connect_btn = ctk.CTkButton(
            bar, text="Connect", height=26, width=80,
            fg_color=ACCENT, hover_color="#4070cc",
            font=ctk.CTkFont("Segoe UI", 10, "bold"), corner_radius=6,
            command=lambda: threading.Thread(target=self._cal_auth, daemon=True).start())
        self.cal_connect_btn.pack(side="right", padx=6, pady=6)

        # ── Month navigator ───────────────────────────────────────────────────
        nav = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=0, height=34)
        nav.pack(fill="x"); nav.pack_propagate(False)

        ctk.CTkButton(nav, text="◀", width=28, height=26,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT, font=ctk.CTkFont(size=13),
                      command=self._cal_prev_month).pack(side="left", padx=6)
        ctk.CTkButton(nav, text="▶", width=28, height=26,
                      fg_color="transparent", hover_color=CARD,
                      text_color=TEXT, font=ctk.CTkFont(size=13),
                      command=self._cal_next_month).pack(side="right", padx=6)
        ctk.CTkButton(nav, text="Today", width=50, height=22,
                      fg_color=CARD, hover_color=SURFACE,
                      text_color=ACCENT, font=ctk.CTkFont("Segoe UI", 10),
                      corner_radius=6,
                      command=self._cal_goto_today).pack(side="right", padx=2)

        self.cal_month_lbl = ctk.CTkLabel(nav, text="",
                                           font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                           text_color=TEXT)
        self.cal_month_lbl.pack(expand=True)

        # ── Day-of-week header ────────────────────────────────────────────────
        dow_frame = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=0, height=24)
        dow_frame.pack(fill="x"); dow_frame.pack_propagate(False)
        for d in ("Su","Mo","Tu","We","Th","Fr","Sa"):
            ctk.CTkLabel(dow_frame, text=d, width=44,
                         font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=MUTED).pack(side="left", expand=True)

        # ── Calendar grid ─────────────────────────────────────────────────────
        self.cal_grid = ctk.CTkFrame(f, fg_color=BG, corner_radius=0)
        self.cal_grid.pack(fill="x", padx=4)

        # ── Day events panel ──────────────────────────────────────────────────
        self.cal_day_lbl = ctk.CTkLabel(f, text="",
                                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                                         text_color=TEXT, anchor="w")
        self.cal_day_lbl.pack(fill="x", padx=12, pady=(6,2))

        self.cal_events_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent",
                                                         scrollbar_button_color=SURFACE)
        self.cal_events_scroll.pack(fill="both", expand=True, padx=8, pady=(0,6))

        # Auto-connect if already authenticated
        if os.path.exists(os.path.join(BASE, "cal_token.json")) and \
           os.path.exists(os.path.join(BASE, "credentials.json")):
            threading.Thread(target=self._cal_auth, daemon=True).start()
        else:
            self._render_cal_grid()

    # ── Auth ───────────────────────────────────────────────────────────────────
    def _cal_auth(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES     = ["https://www.googleapis.com/auth/calendar.readonly"]
        token_path = os.path.join(BASE, "cal_token.json")
        creds_path = os.path.join(BASE, "credentials.json")

        if not os.path.exists(creds_path):
            self.after(0, lambda: self._cal_set_status("Put credentials.json in personal_os folder", False))
            return

        creds = None
        if os.path.exists(token_path):
            try:   creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception: creds = None

        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow  = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_path, "w") as fh:
                    fh.write(creds.to_json())
            except Exception as e:
                self.after(0, lambda: self._cal_set_status(f"Auth failed: {e}", False))
                return

        try:
            self._cal_service = build("calendar", "v3", credentials=creds)
            self.after(0, lambda: self._cal_set_status("● Connected", True))
            self._cal_fetch_month()
        except Exception as e:
            self.after(0, lambda: self._cal_set_status(f"Error: {e}", False))

    def _cal_set_status(self, text, connected):
        self.cal_status_lbl.configure(text=text,
                                       text_color=GREEN if connected else MUTED)
        if connected:
            self.cal_connect_btn.configure(text="Re-auth")

    # ── Fetch month ────────────────────────────────────────────────────────────
    def _cal_fetch_month(self):
        if not self._cal_service: return
        import calendar as cal_mod
        from datetime import timezone
        y, m  = self._cal_month.year, self._cal_month.month
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        last  = cal_mod.monthrange(y, m)[1]
        end   = datetime(y, m, last, 23, 59, 59, tzinfo=timezone.utc)
        try:
            res    = self._cal_service.events().list(
                calendarId="primary", timeMin=start.isoformat(),
                timeMax=end.isoformat(), singleEvents=True,
                orderBy="startTime", maxResults=200).execute()
            events = res.get("items", [])
            by_date = {}
            for ev in events:
                d_raw = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
                d_key = d_raw[:10]
                by_date.setdefault(d_key, []).append(ev)
            self._cal_events_cache = by_date
            self.after(0, self._render_cal_grid)
            self.after(0, self._render_cal_day)
        except Exception as e:
            self.after(0, lambda: self._cal_set_status(f"Fetch error: {e}", True))

    # ── Navigation ─────────────────────────────────────────────────────────────
    def _cal_prev_month(self):
        m = self._cal_month
        self._cal_month = (m.replace(day=1) - timedelta(days=1)).replace(day=1)
        threading.Thread(target=self._cal_fetch_month, daemon=True).start()
        self._render_cal_grid()

    def _cal_next_month(self):
        import calendar as cal_mod
        m    = self._cal_month
        last = cal_mod.monthrange(m.year, m.month)[1]
        self._cal_month = (m.replace(day=last) + timedelta(days=1)).replace(day=1)
        threading.Thread(target=self._cal_fetch_month, daemon=True).start()
        self._render_cal_grid()

    def _cal_goto_today(self):
        self._cal_selected = date.today()
        self._cal_month    = date.today().replace(day=1)
        threading.Thread(target=self._cal_fetch_month, daemon=True).start()
        self._render_cal_grid()
        self._render_cal_day()

    # ── Grid render ────────────────────────────────────────────────────────────
    def _render_cal_grid(self):
        import calendar as cal_mod
        for w in self.cal_grid.winfo_children(): w.destroy()

        m    = self._cal_month
        self.cal_month_lbl.configure(text=m.strftime("%B %Y"))
        cal  = cal_mod.monthcalendar(m.year, m.month)  # weeks, Mon-start
        today = date.today()

        # Re-order to Sun-start
        cal_sun = []
        for week in cal:
            cal_sun.append([week[6]] + week[:6])  # Sun first

        for week in cal_sun:
            row_f = ctk.CTkFrame(self.cal_grid, fg_color="transparent")
            row_f.pack(fill="x")
            for day_num in week:
                cell_f = ctk.CTkFrame(row_f, fg_color="transparent", width=44, height=36)
                cell_f.pack(side="left", expand=True)
                cell_f.pack_propagate(False)

                if day_num == 0:
                    continue

                d      = date(m.year, m.month, day_num)
                d_key  = d.isoformat()
                is_today    = d == today
                is_selected = d == self._cal_selected
                has_events  = bool(self._cal_events_cache.get(d_key))

                if is_selected:
                    bg, fg = ACCENT, "white"
                elif is_today:
                    bg, fg = "#E7F3FF", ACCENT
                else:
                    bg, fg = "transparent", TEXT

                btn = ctk.CTkButton(
                    cell_f, text=str(day_num),
                    width=32, height=28,
                    fg_color=bg, hover_color="#3a4a6e",
                    text_color=fg,
                    font=ctk.CTkFont("Segoe UI", 11,
                                     "bold" if is_today or is_selected else "normal"),
                    corner_radius=6,
                    command=lambda dd=d: self._cal_select_day(dd))
                btn.place(relx=0.5, rely=0.35, anchor="center")

                # Event dot
                if has_events and not is_selected:
                    dot = ctk.CTkFrame(cell_f, fg_color=ACCENT, width=4, height=4,
                                       corner_radius=2)
                    dot.place(relx=0.5, rely=0.85, anchor="center")

    def _cal_select_day(self, d):
        self._cal_selected = d
        self._render_cal_grid()
        self._render_cal_day()

    # ── Day events render ──────────────────────────────────────────────────────
    def _render_cal_day(self):
        import webbrowser, re
        for w in self.cal_events_scroll.winfo_children(): w.destroy()

        d_key  = self._cal_selected.isoformat()
        today  = date.today()
        label  = "Today" if self._cal_selected == today else \
                 self._cal_selected.strftime("%A, %d %B")
        self.cal_day_lbl.configure(text=label)

        if not self._cal_service:
            ctk.CTkLabel(self.cal_events_scroll,
                         text="Connect Google Calendar above",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11)).pack(pady=20)
            return

        events = self._cal_events_cache.get(d_key, [])
        if not events:
            ctk.CTkLabel(self.cal_events_scroll, text="No events",
                         text_color=MUTED, font=ctk.CTkFont("Segoe UI", 11)).pack(pady=20)
            return

        for ev in events:
            start_raw = ev.get("start",{}).get("dateTime") or ev.get("start",{}).get("date","")
            if "T" in start_raw:
                try:
                    dt       = datetime.fromisoformat(start_raw)
                    time_str = dt.strftime("%I:%M %p")
                    diff     = int((dt.replace(tzinfo=None) - datetime.now()).total_seconds()/60)
                    if 0 < diff < 120: time_str += f" · in {diff}m"
                except Exception: time_str = start_raw[11:16]
            else:
                time_str = "All day"

            # Meet link
            link = None
            if ev.get("hangoutLink"): link = ev["hangoutLink"]
            else:
                desc = (ev.get("description") or "") + (ev.get("location") or "")
                mx   = re.search(r"https://(meet\.google\.com|zoom\.us|teams\.microsoft\.com)/\S+", desc)
                if mx: link = mx.group(0)

            card = ctk.CTkFrame(self.cal_events_scroll, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", pady=3)

            ctk.CTkFrame(card, fg_color=ACCENT, width=4, corner_radius=2
                         ).pack(side="left", fill="y", pady=6, padx=(6,0))

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            ctk.CTkLabel(info, text=ev.get("summary","(No title)"),
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=TEXT, anchor="w", wraplength=180).pack(anchor="w")
            ctk.CTkLabel(info, text=time_str,
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=MUTED, anchor="w").pack(anchor="w")

            if link:
                ctk.CTkButton(card, text="Join", width=48, height=26,
                              fg_color=GREEN, hover_color="#16a34a",
                              text_color="white", font=ctk.CTkFont("Segoe UI", 10, "bold"),
                              corner_radius=6,
                              command=lambda l=link: webbrowser.open(l)
                              ).pack(side="right", padx=8, pady=8)

    def _render_cal(self, *_):
        self._render_cal_grid()
        self._render_cal_day()

    # ── Close ──────────────────────────────────────────────────────────────────
    def _on_close(self):
        self._save_pos()
        self.destroy()


if __name__ == "__main__":
    app = PersonalOS()
    app.mainloop()
