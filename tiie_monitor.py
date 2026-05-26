import os
import sys
import json
import time
import datetime
import threading
import ssl
import urllib.request
import urllib.error
import logging
from tkinter import Tk, Frame, Label, Menu, StringVar, Canvas, Text, BOTH, LEFT, RIGHT, Y, X

# Configuration and Constants
BANXICO_TOKEN = "f790ae51a34ab0af596fca1024f508d5810f4f52ff74ebac1244c4c741a60fa0"
TIIE_SERIES_ID = "SF43783"       # TIIE a 28 dias diaria
TASA_OBJ_SERIES_ID = "SF61745"   # Tasa Objetivo Banxico
LOG_FILENAME = "tiie_monitor.log"
UPDATE_HOURS = [12, 13, 14, 15, 18, 19]

# Expectations Series IDs (Cetes 28d Survey CR170)
EXP_T_MEDIA = "SR14748"
EXP_T_MIN = "SR14752"
EXP_T_MAX = "SR14753"
EXP_T1_MEDIA = "SR14755"
EXP_T1_MIN = "SR14759"
EXP_T1_MAX = "SR14760"

EXPECTATION_IDS = [EXP_T_MEDIA, EXP_T_MIN, EXP_T_MAX, EXP_T1_MEDIA, EXP_T1_MIN, EXP_T1_MAX]

# Color Palette (Premium Dark Theme)
COLOR_BG = "#121214"         # Main window background (Nvidia overlay style dark)
COLOR_HEADER = "#1a1a1e"     # Header bar background
COLOR_CARD = "#1a1a1e"       # Card backgrounds
COLOR_BORDER = "#2a2a30"     # Borders and dividers
COLOR_TEXT_PRIMARY = "#ffffff" # Primary text (values)
COLOR_TEXT_MUTED = "#8e8e93"   # Labels and description
COLOR_ACCENT_GREEN = "#30d158" # Upward trend (Green)
COLOR_ACCENT_RED = "#ff453a"   # Downward trend (Red)
COLOR_ACCENT_GOLD = "#ffd60a"  # Stable trend (Yellow)

# Setup logging to both file and console
script_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_dir, LOG_FILENAME)

logger = logging.getLogger("TIIEMonitor")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler
fh = logging.FileHandler(log_path, encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("Initializing TIIE Monitor Script...")

# Linear Regression Math (Pure Python)
def calculate_linear_regression_next(values):
    """
    Fits a linear regression y = mx + c to the values list (representing index 0 to n-1)
    and predicts the value at index n (the next business day).
    """
    n = len(values)
    if n < 2:
        return values[-1] if n == 1 else 0.0
    
    x = list(range(n))
    y = values
    
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(i**2 for i in x)
    sum_xy = sum(i * j for i, j in zip(x, y))
    
    denominator = (n * sum_xx - sum_x**2)
    if denominator == 0:
        return y[-1]
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    
    # Predict for x = n
    return slope * n + intercept

class TIIEMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TIIE 28 Dias  BANXICO- SIIE")
        
        # Borderless, always-on-top window setup
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Default geometry: 350px width by 580px height, positioned near top-right
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"350x580+{screen_width - 380}+50")
        
        # Default Opacity
        self.opacity = 0.85
        self.root.attributes("-alpha", self.opacity)
        
        # Window dragging variables
        self.drag_x = 0
        self.drag_y = 0
        
        # App State variables
        self.last_update_str = StringVar(value="Iniciando...")
        self.status_dot_color = COLOR_ACCENT_GOLD
        self.current_table_content = ""
        self.current_clipboard_text = ""
        self.history_rates_to_plot = []
        self.is_collapsed = False
        self.is_minimized_to_taskbar = False
        self.forecast_media = []
        self.forecast_min = []
        self.forecast_max = []
        
        # Daily Variables
        self.daily_val = StringVar(value="--.- %")
        self.daily_trend_sym = StringVar(value="")
        self.daily_trend_text = StringVar(value="")
        self.daily_trend_color = COLOR_TEXT_MUTED
        self.daily_prev = StringVar(value="Ant: --.- %")
        self.daily_next = StringVar(value="Mañana est: --.- %")
        
        # Monthly Variables
        self.monthly_val = StringVar(value="--.- %")
        self.monthly_trend_sym = StringVar(value="")
        self.monthly_trend_text = StringVar(value="")
        self.monthly_trend_color = COLOR_TEXT_MUTED
        self.monthly_prev = StringVar(value="Ant: --.- %")
        self.monthly_next = StringVar(value="Sig. est: --.- %")
        
        # Mutex lock for updates to prevent thread conflicts
        self.update_lock = threading.Lock()
        self.updating_now = False
        
        # Cache for scheduled hour executions: {hour_int: today_date_str}
        self.last_scheduled_updates = {}
        
        self.create_widgets()
        self.setup_bindings()
        
        # Start background thread scheduler
        self.scheduler_active = True
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Trigger first load immediately
        self.trigger_refresh()

    def create_widgets(self):
        # Outer container frame (handles background and thin border)
        self.container = Frame(self.root, bg=COLOR_BG, bd=1, highlightbackground=COLOR_BORDER, highlightcolor=COLOR_BORDER, highlightthickness=1)
        self.container.pack(fill=BOTH, expand=True)
        
        # --- HEADER BAR ---
        self.header_frame = Frame(self.container, bg=COLOR_HEADER, height=28)
        self.header_frame.pack(fill=X)
        self.header_frame.pack_propagate(False)
        
        # Draggable header label
        self.title_lbl = Label(self.header_frame, text="TIIE 28 Dias  BANXICO- SIIE", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER)
        self.title_lbl.pack(side=LEFT, padx=10, pady=5)
        
        # Header controls container
        self.controls_frame = Frame(self.header_frame, bg=COLOR_HEADER)
        self.controls_frame.pack(side=RIGHT)
        
        # Refresh icon button in header
        self.refresh_btn = Label(self.controls_frame, text=" ↻ ", font=("Segoe UI", 11, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER, cursor="hand2")
        self.refresh_btn.pack(side=LEFT, padx=2)
        
        # Minimize icon button in header
        self.min_btn = Label(self.controls_frame, text=" ─ ", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER, cursor="hand2")
        self.min_btn.pack(side=LEFT, padx=2)
        
        # Close icon button in header
        self.close_btn = Label(self.controls_frame, text=" × ", font=("Segoe UI", 12, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER, cursor="hand2")
        self.close_btn.pack(side=LEFT, padx=6)
        
        # --- CARD 1: DAILY TIIE ---
        self.daily_frame = Frame(self.container, bg=COLOR_BG)
        self.daily_frame.pack(fill=X, padx=10, pady=(6, 2))
        
        # Title of Daily Card
        self.daily_title_lbl = Label(self.daily_frame, text="TIIE DIARIA (28 DÍAS)", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.daily_title_lbl.pack(anchor="w")
        
        # Daily main row (value & trend)
        self.daily_val_frame = Frame(self.daily_frame, bg=COLOR_BG)
        self.daily_val_frame.pack(fill=X, pady=1)
        
        self.daily_val_lbl = Label(self.daily_val_frame, textvariable=self.daily_val, font=("Segoe UI", 18, "bold"), fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG)
        self.daily_val_lbl.pack(side=LEFT)
        
        self.daily_trend_sym_lbl = Label(self.daily_val_frame, textvariable=self.daily_trend_sym, font=("Segoe UI", 12, "bold"), bg=COLOR_BG)
        self.daily_trend_sym_lbl.pack(side=LEFT, padx=(6, 2))
        
        self.daily_trend_lbl = Label(self.daily_val_frame, textvariable=self.daily_trend_text, font=("Segoe UI", 9, "bold"), bg=COLOR_BG)
        self.daily_trend_lbl.pack(side=LEFT)
        
        # Daily metadata row (yesterday rate & tomorrow prediction)
        self.daily_meta_frame = Frame(self.daily_frame, bg=COLOR_BG)
        self.daily_meta_frame.pack(fill=X)
        
        self.daily_prev_lbl = Label(self.daily_meta_frame, textvariable=self.daily_prev, font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.daily_prev_lbl.pack(side=LEFT)
        
        self.daily_separator_lbl = Label(self.daily_meta_frame, text="  |  ", font=("Segoe UI", 8), fg=COLOR_BORDER, bg=COLOR_BG)
        self.daily_separator_lbl.pack(side=LEFT)
        
        self.daily_next_lbl = Label(self.daily_meta_frame, textvariable=self.daily_next, font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.daily_next_lbl.pack(side=LEFT)

        # Thin divider line
        self.divider = Canvas(self.container, height=1, bg=COLOR_BORDER, bd=0, highlightthickness=0)
        self.divider.pack(fill=X, padx=10, pady=8)
        
        # --- CARD 2: MONTHLY TIIE ---
        self.monthly_frame = Frame(self.container, bg=COLOR_BG)
        self.monthly_frame.pack(fill=X, padx=10, pady=2)
        
        # Title of Monthly Card (Now Tasa Objetivo)
        self.monthly_title_lbl = Label(self.monthly_frame, text="TASA OBJETIVO BANXICO", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.monthly_title_lbl.pack(anchor="w")
        
        # Monthly main row (value & trend)
        self.monthly_val_frame = Frame(self.monthly_frame, bg=COLOR_BG)
        self.monthly_val_frame.pack(fill=X, pady=1)
        
        self.monthly_val_lbl = Label(self.monthly_val_frame, textvariable=self.monthly_val, font=("Segoe UI", 18, "bold"), fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG)
        self.monthly_val_lbl.pack(side=LEFT)
        
        self.monthly_trend_sym_lbl = Label(self.monthly_val_frame, textvariable=self.monthly_trend_sym, font=("Segoe UI", 12, "bold"), bg=COLOR_BG)
        self.monthly_trend_sym_lbl.pack(side=LEFT, padx=(6, 2))
        
        self.monthly_trend_lbl = Label(self.monthly_val_frame, textvariable=self.monthly_trend_text, font=("Segoe UI", 9, "bold"), bg=COLOR_BG)
        self.monthly_trend_lbl.pack(side=LEFT)
        
        # Monthly metadata row (prior month rate & expected rate)
        self.monthly_meta_frame = Frame(self.monthly_frame, bg=COLOR_BG)
        self.monthly_meta_frame.pack(fill=X)
        
        self.monthly_prev_lbl = Label(self.monthly_meta_frame, textvariable=self.monthly_prev, font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.monthly_prev_lbl.pack(side=LEFT)
        
        self.monthly_separator_lbl = Label(self.monthly_meta_frame, text="  |  ", font=("Segoe UI", 8), fg=COLOR_BORDER, bg=COLOR_BG)
        self.monthly_separator_lbl.pack(side=LEFT)
        
        self.monthly_next_lbl = Label(self.monthly_meta_frame, textvariable=self.monthly_next, font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.monthly_next_lbl.pack(side=LEFT)
        
        # --- CHART SECTION (CANVAS) ---
        self.chart_divider = Canvas(self.container, height=1, bg=COLOR_BORDER, bd=0, highlightthickness=0)
        self.chart_divider.pack(fill=X, padx=10, pady=(6, 4))
        
        self.canvas = Canvas(self.container, bg=COLOR_BG, highlightthickness=1, highlightbackground=COLOR_BORDER, highlightcolor=COLOR_BORDER, width=330, height=110)
        self.canvas.pack(fill=X, padx=10, pady=2)
        
        # --- TABLE SECTION (FORECAST) ---
        self.table_divider = Canvas(self.container, height=1, bg=COLOR_BORDER, bd=0, highlightthickness=0)
        self.table_divider.pack(fill=X, padx=10, pady=(6, 4))
        
        self.table_header_frame = Frame(self.container, bg=COLOR_BG)
        self.table_header_frame.pack(fill=X, padx=10, pady=2)
        
        self.table_title_lbl = Label(self.table_header_frame, text="PRONÓSTICO TIIE 28 (ANCLA: CETES 28)", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.table_title_lbl.pack(side=LEFT)
        
        self.copy_btn = Label(self.table_header_frame, text="Copiar Tabla 📋", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_PRIMARY, bg="#2a2a30", padx=6, pady=2, cursor="hand2")
        self.copy_btn.pack(side=RIGHT)
        
        self.table_text = Text(self.container, font=("Consolas", 8), bg=COLOR_CARD, fg=COLOR_TEXT_PRIMARY, bd=1, highlightbackground=COLOR_BORDER, highlightcolor=COLOR_BORDER, highlightthickness=1, height=10, padx=5, pady=5, selectbackground="#30d158", selectforeground="#000000")
        self.table_text.pack(fill=X, padx=10, pady=(2, 4))
        
        # --- FOOTER BAR ---
        self.footer_frame = Frame(self.container, bg=COLOR_BG)
        self.footer_frame.pack(fill=X, side="bottom", padx=10, pady=(2, 6))
        
        # Indicator dot
        self.status_dot = Canvas(self.footer_frame, width=8, height=8, bg=COLOR_BG, bd=0, highlightthickness=0)
        self.status_dot.pack(side=LEFT, pady=3)
        self.draw_status_dot(self.status_dot_color)
        
        # Last update label
        self.last_update_lbl = Label(self.footer_frame, textvariable=self.last_update_str, font=("Segoe UI", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.last_update_lbl.pack(side=LEFT, padx=4)
        
        # API Source tag
        self.source_lbl = Label(self.footer_frame, text="SIE Banxico", font=("Segoe UI", 8, "italic"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG)
        self.source_lbl.pack(side=RIGHT)

    def draw_status_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(1, 1, 7, 7, fill=color, outline="")

    def setup_bindings(self):
        # Enable dragging of the window from the header, the container, and titles
        for widget in [self.header_frame, self.title_lbl, self.container, 
                       self.daily_frame, self.daily_title_lbl,
                       self.monthly_frame, self.monthly_title_lbl,
                       self.table_header_frame, self.table_title_lbl,
                       self.footer_frame, self.last_update_lbl]:
            widget.bind("<Button-1>", self.start_window_drag)
            widget.bind("<B1-Motion>", self.execute_window_drag)
            
        # Context menu (Right click)
        self.context_menu = Menu(self.root, tearoff=0, bg=COLOR_HEADER, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_BG, activeforeground=COLOR_TEXT_PRIMARY, bd=1, relief="flat")
        self.context_menu.add_command(label="Refrescar Ahora ↻", command=self.trigger_refresh)
        self.context_menu.add_command(label="Colapsar / Expandir ⤢", command=self.toggle_collapse)
        self.context_menu.add_command(label="Minimizar a Barra ─", command=self.minimize_window)
        
        # Opacity submenu
        self.opacity_submenu = Menu(self.context_menu, tearoff=0, bg=COLOR_HEADER, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_BG, bd=1)
        for pct in [25, 50, 70, 85, 95, 100]:
            self.opacity_submenu.add_command(label=f"{pct}%", command=lambda p=pct: self.set_window_opacity(p / 100))
        self.context_menu.add_cascade(label="Opacidad", menu=self.opacity_submenu)
        
        # Always on top toggle
        self.is_always_on_top = True
        self.context_menu.add_command(label="Fijar al Frente (Sí)", command=self.toggle_always_on_top)
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cerrar", command=self.close_application)
        
        # Bind right click to show menu
        self.root.bind("<Button-3>", self.show_context_menu)
        
        # Interactive hover effects for buttons
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg=COLOR_ACCENT_RED, bg="#2a1010"))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER))
        self.close_btn.bind("<Button-1>", lambda e: self.close_application())
        
        self.refresh_btn.bind("<Enter>", lambda e: self.refresh_btn.config(fg=COLOR_TEXT_PRIMARY))
        self.refresh_btn.bind("<Leave>", lambda e: self.refresh_btn.config(fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER))
        self.refresh_btn.bind("<Button-1>", lambda e: self.trigger_refresh())
        
        self.min_btn.bind("<Enter>", lambda e: self.min_btn.config(fg=COLOR_TEXT_PRIMARY, bg="#27272a"))
        self.min_btn.bind("<Leave>", lambda e: self.min_btn.config(fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER))
        self.min_btn.bind("<Button-1>", lambda e: self.toggle_collapse())
        
        # Copy button hover and click
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.config(bg="#3a3a40"))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.config(bg="#2a2a30"))
        self.copy_btn.bind("<Button-1>", lambda e: self.copy_table_to_clipboard())
        
        # Bind the Map event to restore frameless styling when de-minimized
        self.root.bind("<Map>", self.on_window_map)

    # --- DRAG AND DROP LOGIC ---
    def start_window_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def execute_window_drag(self, event):
        delta_x = event.x - self.drag_x
        delta_y = event.y - self.drag_y
        new_x = self.root.winfo_x() + delta_x
        new_y = self.root.winfo_y() + delta_y
        self.root.geometry(f"+{new_x}+{new_y}")

    # --- WINDOW DECORATIONS & CONTROLS ---
    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def set_window_opacity(self, value):
        self.opacity = value
        self.root.attributes("-alpha", self.opacity)
        logger.info(f"Window opacity changed to {int(value * 100)}%")

    def toggle_always_on_top(self):
        self.is_always_on_top = not self.is_always_on_top
        self.root.attributes("-topmost", self.is_always_on_top)
        status_txt = "Sí" if self.is_always_on_top else "No"
        self.context_menu.entryconfigure(2, label=f"Fijar al Frente ({status_txt})")
        logger.info(f"Always-on-top status toggled to: {self.is_always_on_top}")

    def close_application(self):
        logger.info("Closing application. Goodbye!")
        self.scheduler_active = False
        self.root.destroy()
        sys.exit(0)

    def minimize_window(self):
        logger.info("Minimizing window to taskbar...")
        # Save position before minimizing to prevent window manager drift
        self.last_x = self.root.winfo_x()
        self.last_y = self.root.winfo_y()
        self.is_minimized_to_taskbar = True
        self.root.overrideredirect(False)
        self.root.iconify()

    def on_window_map(self, event):
        if hasattr(self, "is_minimized_to_taskbar") and self.is_minimized_to_taskbar:
            self.is_minimized_to_taskbar = False
            self.root.after(150, self.restore_borderless_state)

    def restore_borderless_state(self):
        self.root.overrideredirect(True)
        # If collapsed, restore collapsed geometry, otherwise restore full geometry
        if hasattr(self, "last_x") and hasattr(self, "last_y"):
            h = 30 if self.is_collapsed else 580
            self.root.geometry(f"350x{h}+{self.last_x}+{self.last_y}")
        self.root.attributes("-topmost", self.is_always_on_top)
        if not self.is_collapsed and self.history_rates_to_plot:
            self.update_chart(self.history_rates_to_plot, self.forecast_media, self.forecast_min, self.forecast_max)

    def toggle_collapse(self):
        if not self.is_collapsed:
            # Collapse window
            self.is_collapsed = True
            
            # Hide all widgets below header
            self.daily_frame.pack_forget()
            self.divider.pack_forget()
            self.monthly_frame.pack_forget()
            self.chart_divider.pack_forget()
            self.canvas.pack_forget()
            self.table_divider.pack_forget()
            self.table_header_frame.pack_forget()
            self.table_text.pack_forget()
            self.footer_frame.pack_forget()
            
            # Shrink window height to header height + borders
            curr_x = self.root.winfo_x()
            curr_y = self.root.winfo_y()
            self.root.geometry(f"350x30+{curr_x}+{curr_y}")
            
            # Change minimize button text to indicate expand
            self.min_btn.config(text=" ＋ ")
            logger.info("Widget collapsed to header bar.")
        else:
            # Expand window
            self.is_collapsed = False
            
            # Repack all widgets in their correct order
            self.daily_frame.pack(fill=X, padx=10, pady=(6, 2))
            self.divider.pack(fill=X, padx=10, pady=8)
            self.monthly_frame.pack(fill=X, padx=10, pady=2)
            self.chart_divider.pack(fill=X, padx=10, pady=(6, 4))
            self.canvas.pack(fill=X, padx=10, pady=2)
            self.table_divider.pack(fill=X, padx=10, pady=(6, 4))
            self.table_header_frame.pack(fill=X, padx=10, pady=2)
            self.table_text.pack(fill=X, padx=10, pady=(2, 4))
            self.footer_frame.pack(fill=X, side="bottom", padx=10, pady=(2, 6))
            
            # Restore window height to 580px
            curr_x = self.root.winfo_x()
            curr_y = self.root.winfo_y()
            self.root.geometry(f"350x580+{curr_x}+{curr_y}")
            
            # Change minimize button text back to collapse indicator
            self.min_btn.config(text=" ─ ")
            
            # Redraw chart if data is present
            if self.history_rates_to_plot:
                self.update_chart(self.history_rates_to_plot, self.forecast_media, self.forecast_min, self.forecast_max)
                
            logger.info("Widget expanded back to full size.")

    # --- REFRESH UTILITIES ---
    def trigger_refresh(self):
        if self.updating_now:
            logger.info("Refresh already in progress. Ignoring request.")
            return
        
        self.updating_now = True
        self.last_update_str.set("Actualizando...")
        self.draw_status_dot(COLOR_ACCENT_GOLD)
        
        # Rotate spinner in UI (micro-animation)
        self.refresh_btn.config(fg=COLOR_ACCENT_GOLD)
        
        # Fetch and calculate in a background thread to prevent GUI freezing
        threading.Thread(target=self.fetch_data_thread, daemon=True).start()

    def fetch_data_thread(self):
        with self.update_lock:
            success = False
            error_msg = ""
            
            # Disable certificate validation failures dynamically if needed (standard fallback for Banxico API TLS 1.3)
            ctx = ssl.create_default_context()
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
            
            # Fetch last 90 calendar days to have ~60 business days of observations
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=90)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            all_series_ids = [TIIE_SERIES_ID, TASA_OBJ_SERIES_ID] + EXPECTATION_IDS
            url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{','.join(all_series_ids)}/datos/{start_str}/{end_str}"
            logger.info(f"Querying Banxico API range: {start_str} to {end_str} for series {','.join(all_series_ids)}")
            
            req = urllib.request.Request(url)
            req.add_header("Bmx-Token", BANXICO_TOKEN)
            
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
                    res_body = response.read().decode('utf-8')
                    parsed_res = json.loads(res_body)
                    
                    series_list = parsed_res.get("bmx", {}).get("series", [])
                    if not series_list or len(series_list) < 2:
                        raise ValueError("Expected at least core series from Banxico API, got fewer or none")
                    
                    logger.info(f"Retrieved {len(series_list)} series successfully.")
                    
                    # Process and calculate indicators
                    self.process_observations_multi(series_list)
                    success = True
                    
            except urllib.error.HTTPError as he:
                error_msg = f"HTTP Error {he.code}"
                logger.error(f"Banxico API HTTP Error: {he.code} - {he.reason}")
            except urllib.error.URLError as ue:
                error_msg = "Error de Conexión"
                logger.error(f"Banxico API Connection Error: {ue.reason}")
            except Exception as ex:
                error_msg = "Error de Datos"
                logger.error(f"Error parsing Banxico data: {str(ex)}")
            
            # Update GUI elements on main thread
            self.root.after(0, lambda: self.finalize_update_ui(success, error_msg))

    def process_observations_multi(self, series_list):
        # Banxico API reports ascending date order (oldest first).
        # Build dictionary of series data
        series_dict = {}
        for s in series_list:
            sid = s.get("idSerie")
            obs_list = s.get("datos", [])
            
            dates = []
            rates = []
            for obs in obs_list:
                try:
                    val = float(obs["dato"])
                    rates.append(val)
                    dates.append(obs["fecha"])
                except (ValueError, TypeError):
                    continue
            series_dict[sid] = rates
            
        tiie_rates = series_dict.get(TIIE_SERIES_ID, [])
        tasa_obj_rates = series_dict.get(TASA_OBJ_SERIES_ID, [])
        
        # 1. DAILY TIIE DETAILS
        n_tiie = len(tiie_rates)
        if n_tiie >= 2:
            latest_val = tiie_rates[-1]
            prev_val = tiie_rates[-2]
            daily_diff = latest_val - prev_val
            
            # Format display
            self.daily_val.set(f"{latest_val:.4f}%")
            self.daily_prev.set(f"Ant: {prev_val:.4f}%")
            
            # Predict next business day daily rate based on last 5 days
            recent_rates_5 = tiie_rates[-5:] if n_tiie >= 5 else tiie_rates
            predicted_tomorrow = calculate_linear_regression_next(recent_rates_5)
            self.daily_next.set(f"Est. Mañana: {predicted_tomorrow:.4f}%")
            
            # Trend calculation
            if daily_diff > 0.00001:
                self.daily_trend_sym.set("▲")
                self.daily_trend_text.set(f"+{daily_diff:.4f}%")
                self.daily_trend_color = COLOR_ACCENT_GREEN
            elif daily_diff < -0.00001:
                self.daily_trend_sym.set("▼")
                self.daily_trend_text.set(f"{daily_diff:.4f}%")
                self.daily_trend_color = COLOR_ACCENT_RED
            else:
                self.daily_trend_sym.set("=")
                self.daily_trend_text.set("Estable")
                self.daily_trend_color = COLOR_ACCENT_GOLD
        else:
            logger.error("Insufficient observations for TIIE")
            raise ValueError("Insufficient observations for TIIE")
            
        # 2. TASA OBJETIVO DETAILS
        n_tasa = len(tasa_obj_rates)
        if n_tasa >= 2:
            latest_val = tasa_obj_rates[-1]
            prev_val = tasa_obj_rates[-2]
            tasa_diff = latest_val - prev_val
            
            self.monthly_val.set(f"{latest_val:.4f}%")
            self.monthly_prev.set(f"Ant: {prev_val:.4f}%")
            
            # Predict tomorrow's target rate (constant extrapolation via regression)
            recent_rates_5 = tasa_obj_rates[-5:] if n_tasa >= 5 else tasa_obj_rates
            predicted_tomorrow = calculate_linear_regression_next(recent_rates_5)
            self.monthly_next.set(f"Est. Siguiente: {predicted_tomorrow:.4f}%")
            
            # Trend calculation
            if tasa_diff > 0.00001:
                self.monthly_trend_sym.set("▲")
                self.monthly_trend_text.set(f"+{tasa_diff:.4f}%")
                self.monthly_trend_color = COLOR_ACCENT_GREEN
            elif tasa_diff < -0.00001:
                self.monthly_trend_sym.set("▼")
                self.monthly_trend_text.set(f"{tasa_diff:.4f}%")
                self.monthly_trend_color = COLOR_ACCENT_RED
            else:
                self.monthly_trend_sym.set("=")
                self.monthly_trend_text.set("Estable")
                self.monthly_trend_color = COLOR_ACCENT_GOLD
        else:
            logger.error("Insufficient observations for Tasa Objetivo")
            raise ValueError("Insufficient observations for Tasa Objetivo")

        # 3. INTERPOLATION FORECAST AND EXPECTATIONS
        current_tiie = tiie_rates[-1]
        
        def get_last_val(s_dict, sid, default):
            vals = s_dict.get(sid, [])
            return vals[-1] if vals else default
            
        val_t_media = get_last_val(series_dict, EXP_T_MEDIA, current_tiie)
        val_t_min = get_last_val(series_dict, EXP_T_MIN, current_tiie)
        val_t_max = get_last_val(series_dict, EXP_T_MAX, current_tiie)
        
        val_t1_media = get_last_val(series_dict, EXP_T1_MEDIA, current_tiie)
        val_t1_min = get_last_val(series_dict, EXP_T1_MIN, current_tiie)
        val_t1_max = get_last_val(series_dict, EXP_T1_MAX, current_tiie)
        
        logger.info(f"Expectations CR170 Cetes 28d Year t (Media/Min/Max): {val_t_media}/{val_t_min}/{val_t_max}")
        logger.info(f"Expectations CR170 Cetes 28d Year t+1 (Media/Min/Max): {val_t1_media}/{val_t1_min}/{val_t1_max}")
        
        today = datetime.date.today()
        current_month = today.month
        
        d1 = 12 - current_month
        d2 = d1 + 12
        
        # Build interpolation control points
        points_media = [(0, current_tiie)]
        points_min = [(0, current_tiie)]
        points_max = [(0, current_tiie)]
        
        if d1 > 0:
            points_media.append((d1, val_t_media))
            points_min.append((d1, val_t_min))
            points_max.append((d1, val_t_max))
            
            points_media.append((d2, val_t1_media))
            points_min.append((d2, val_t1_min))
            points_max.append((d2, val_t1_max))
        else:
            points_media.append((12, val_t1_media))
            points_min.append((12, val_t1_min))
            points_max.append((12, val_t1_max))
            
        def get_interpolated_val(m, points):
            for i in range(len(points) - 1):
                x0, y0 = points[i]
                x1, y1 = points[i+1]
                if x0 <= m <= x1:
                    if x1 == x0:
                        return y0
                    return y0 + (m - x0) * (y1 - y0) / (x1 - x0)
            return points[-1][1]
            
        # Compute forecasts
        self.forecast_media = [get_interpolated_val(m, points_media) for m in range(13)]
        self.forecast_min = [get_interpolated_val(m, points_min) for m in range(13)]
        self.forecast_max = [get_interpolated_val(m, points_max) for m in range(13)]
        self.history_rates_to_plot = tiie_rates[-30:]
        
        # Construct table text
        def get_future_month_name(months_ahead):
            year = today.year + (today.month + months_ahead - 1) // 12
            month = (today.month + months_ahead - 1) % 12 + 1
            months_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            return f"{months_es[month-1]} {str(year)[2:]}"
            
        table_lines = []
        table_lines.append(" Mes      Mín (%)  Media (%)  Máx (%)")
        table_lines.append("─" * 38)
        
        clipboard_lines = []
        clipboard_lines.append("Mes\tMín (%)\tMedia (%)\tMáx (%)")
        
        for m in range(1, 13):
            mes_name = get_future_month_name(m)
            val_min = self.forecast_min[m]
            val_med = self.forecast_media[m]
            val_max = self.forecast_max[m]
            
            table_lines.append(f" {mes_name:<8} {val_min:>7.4f}%   {val_med:>7.4f}%  {val_max:>7.4f}%")
            clipboard_lines.append(f"{mes_name}\t{val_min:.4f}%\t{val_med:.4f}%\t{val_max:.4f}%")
            
        self.current_table_content = "\n".join(table_lines)
        self.current_clipboard_text = "\n".join(clipboard_lines)

    def finalize_update_ui(self, success, error_msg):
        self.updating_now = False
        
        # Reset refresh button color
        self.refresh_btn.config(fg=COLOR_TEXT_MUTED)
        
        now = datetime.datetime.now()
        now_time_str = now.strftime("%H:%M:%S")
        
        if success:
            self.last_update_str.set(f"Act: {now_time_str}")
            self.status_dot_color = COLOR_ACCENT_GREEN
            self.draw_status_dot(COLOR_ACCENT_GREEN)
            
            # Set the font colors for trend labels
            self.daily_trend_sym_lbl.config(fg=self.daily_trend_color)
            self.daily_trend_lbl.config(fg=self.daily_trend_color)
            self.monthly_trend_sym_lbl.config(fg=self.monthly_trend_color)
            self.monthly_trend_lbl.config(fg=self.monthly_trend_color)
            
            # Update table text widget
            self.table_text.config(state="normal")
            self.table_text.delete("1.0", "end")
            self.table_text.insert("1.0", self.current_table_content)
            self.table_text.config(state="disabled")
            
            # Update chart canvas
            self.update_chart(self.history_rates_to_plot, self.forecast_media, self.forecast_min, self.forecast_max)
            
            logger.info("GUI successfully refreshed with new metrics.")
        else:
            # On error, maintain older readings but show error status in footer
            self.last_update_str.set(f"Error ({now.strftime('%H:%M')}): {error_msg}")
            self.status_dot_color = COLOR_ACCENT_RED
            self.draw_status_dot(COLOR_ACCENT_RED)
            logger.warning(f"GUI refresh completed with failures: {error_msg}")

    def update_chart(self, history_rates, forecast_media, forecast_min, forecast_max):
        self.canvas.delete("all")
        
        canvas_width = 330
        canvas_height = 110
        
        margin_left = 40
        margin_right = 15
        margin_top = 15
        margin_bottom = 20
        
        plot_width = canvas_width - margin_left - margin_right
        plot_height = canvas_height - margin_top - margin_bottom
        
        all_vals = list(history_rates) + list(forecast_media) + list(forecast_min) + list(forecast_max)
        if not all_vals:
            return
            
        min_v = min(all_vals)
        max_v = max(all_vals)
        v_range = max_v - min_v
        if v_range < 0.001:
            v_range = 1.0
            
        y_min = min_v - 0.08 * v_range
        y_max = max_v + 0.08 * v_range
        
        def get_y(val):
            return margin_top + plot_height - ((val - y_min) / (y_max - y_min)) * plot_height
            
        # Draw grid lines
        y_grid_vals = [y_min + 0.1 * (y_max - y_min), (y_min + y_max) / 2.0, y_max - 0.1 * (y_max - y_min)]
        for g_val in y_grid_vals:
            y_coord = get_y(g_val)
            self.canvas.create_line(margin_left, y_coord, margin_left + plot_width, y_coord, fill="#2a2a30", dash=(2, 2))
            self.canvas.create_text(margin_left - 5, y_coord, text=f"{g_val:.2f}%", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7), anchor="e")
            
        # Today vertical line (midpoint of plot)
        x_mid = margin_left + plot_width / 2
        self.canvas.create_line(x_mid, margin_top, x_mid, margin_top + plot_height, fill="#3a3a40", dash=(2, 2))
        self.canvas.create_text(x_mid, margin_top - 5, text="Hoy", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7), anchor="s")
        
        # Bottom labels
        self.canvas.create_text(margin_left + 5, margin_top + plot_height + 5, text="Historial (30d)", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7, "bold"), anchor="nw")
        self.canvas.create_text(margin_left + plot_width - 5, margin_top + plot_height + 5, text="Pronóstico (12m)", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 7, "bold"), anchor="ne")
        
        # Plot history
        H = len(history_rates)
        if H >= 2:
            hist_coords = []
            for i, val in enumerate(history_rates):
                x = margin_left + (i / (H - 1)) * (plot_width / 2)
                y = get_y(val)
                hist_coords.extend([x, y])
            self.canvas.create_line(hist_coords, fill="#ffffff", width=2)
            
        # Plot forecast media
        F = len(forecast_media)
        if F >= 2:
            media_coords = []
            for j, val in enumerate(forecast_media):
                x = x_mid + (j / (F - 1)) * (plot_width / 2)
                y = get_y(val)
                media_coords.extend([x, y])
            self.canvas.create_line(media_coords, fill="#54afec", width=2)
            
            # Plot max
            max_coords = []
            for j, val in enumerate(forecast_max):
                x = x_mid + (j / (F - 1)) * (plot_width / 2)
                y = get_y(val)
                max_coords.extend([x, y])
            self.canvas.create_line(max_coords, fill="#ff453a", width=1.5, dash=(4, 4))
            
            # Plot min
            min_coords = []
            for j, val in enumerate(forecast_min):
                x = x_mid + (j / (F - 1)) * (plot_width / 2)
                y = get_y(val)
                min_coords.extend([x, y])
            self.canvas.create_line(min_coords, fill="#30d158", width=1.5, dash=(4, 4))

    def copy_table_to_clipboard(self):
        if not hasattr(self, "current_clipboard_text") or not self.current_clipboard_text:
            return
        
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_clipboard_text)
            self.root.update()
            
            # Micro-animation feedback
            self.copy_btn.config(text="Copiado! ✓", fg=COLOR_ACCENT_GREEN)
            logger.info("Table copied to clipboard successfully.")
            self.root.after(1500, lambda: self.copy_btn.config(text="Copiar Tabla 📋", fg=COLOR_TEXT_PRIMARY))
        except Exception as e:
            logger.error(f"Error copying table to clipboard: {e}")

    # --- SCHEDULER IMPLEMENTATION ---
    def run_scheduler(self):
        """
        Background thread checking local time every 15 seconds.
        Triggers updates at startup and exactly at 12:00, 13:00, 14:00, 15:00, 18:00, 19:00 hrs daily.
        """
        logger.info("Background scheduler thread started successfully.")
        
        # Short cooldown on start to let UI draw
        time.sleep(2)
        
        while self.scheduler_active:
            now = datetime.datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            today_str = now.strftime("%Y-%m-%d")
            
            # Check if current hour is a target hour
            if current_hour in UPDATE_HOURS:
                # Check if we have already updated in this target hour today
                last_update_day = self.last_scheduled_updates.get(current_hour)
                if last_update_day != today_str:
                    logger.info(f"Scheduler triggered update for target hour {current_hour}:00 (Local Time: {now.strftime('%Y-%m-%d %H:%M:%S')})")
                    
                    # Update local state before refreshing to prevent duplicate triggers
                    self.last_scheduled_updates[current_hour] = today_str
                    self.root.after(0, self.trigger_refresh)
            
            # Clean up old days from cache to prevent infinite growth
            keys_to_delete = []
            for h, day in self.last_scheduled_updates.items():
                if day != today_str:
                    keys_to_delete.append(h)
            for h in keys_to_delete:
                del self.last_scheduled_updates[h]
                
            # Sleep for 15 seconds
            time.sleep(15)

if __name__ == "__main__":
    # Ensure DPI scaling doesn't blur window on high resolution displays
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    root = Tk()
    app = TIIEMonitorApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by CLI signal.")
        sys.exit(0)
