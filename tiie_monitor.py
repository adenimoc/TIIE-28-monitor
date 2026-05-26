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
from tkinter import Tk, Frame, Label, Menu, StringVar, Canvas, BOTH, LEFT, RIGHT, Y, X

# Configuration and Constants
BANXICO_TOKEN = "f790ae51a34ab0af596fca1024f508d5810f4f52ff74ebac1244c4c741a60fa0"
TIIE_SERIES_ID = "SF43783"       # TIIE a 28 dias diaria
TASA_OBJ_SERIES_ID = "SF61745"   # Tasa Objetivo Banxico
LOG_FILENAME = "tiie_monitor.log"
UPDATE_HOURS = [12, 13, 14, 15, 18, 19]

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
        
        # Default geometry: 310px width by 250px height, positioned near top-right
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"310x250+{screen_width - 340}+50")
        
        # Default Opacity
        self.opacity = 0.85
        self.root.attributes("-alpha", self.opacity)
        
        # Window dragging variables
        self.drag_x = 0
        self.drag_y = 0
        
        # App State variables
        self.last_update_str = StringVar(value="Iniciando...")
        self.status_dot_color = COLOR_ACCENT_GOLD
        
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
                       self.footer_frame, self.last_update_lbl]:
            widget.bind("<Button-1>", self.start_window_drag)
            widget.bind("<B1-Motion>", self.execute_window_drag)
            
        # Context menu (Right click)
        self.context_menu = Menu(self.root, tearoff=0, bg=COLOR_HEADER, fg=COLOR_TEXT_PRIMARY, activebackground=COLOR_BG, activeforeground=COLOR_TEXT_PRIMARY, bd=1, relief="flat")
        self.context_menu.add_command(label="Refrescar Ahora ↻", command=self.trigger_refresh)
        self.context_menu.add_command(label="Minimizar ─", command=self.minimize_window)
        
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
        self.min_btn.bind("<Button-1>", lambda e: self.minimize_window())
        
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
        logger.info("Minimizing window...")
        # Save position before minimizing to prevent window manager drift
        self.last_x = self.root.winfo_x()
        self.last_y = self.root.winfo_y()
        self.root.overrideredirect(False)
        self.root.iconify()

    def on_window_map(self, event):
        # When restored from minimized state, re-apply borderless setting
        self.root.overrideredirect(True)
        # Restore coordinates if saved to bypass title bar shift offsets
        if hasattr(self, "last_x") and hasattr(self, "last_y"):
            self.root.geometry(f"+{self.last_x}+{self.last_y}")
        self.root.attributes("-topmost", self.is_always_on_top)

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
            
            url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{TIIE_SERIES_ID},{TASA_OBJ_SERIES_ID}/datos/{start_str}/{end_str}"
            logger.info(f"Querying Banxico API range: {start_str} to {end_str} for series {TIIE_SERIES_ID},{TASA_OBJ_SERIES_ID}")
            
            req = urllib.request.Request(url)
            req.add_header("Bmx-Token", BANXICO_TOKEN)
            
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
                    res_body = response.read().decode('utf-8')
                    parsed_res = json.loads(res_body)
                    
                    series_list = parsed_res.get("bmx", {}).get("series", [])
                    if not series_list or len(series_list) < 2:
                        raise ValueError("Expected 2 series from Banxico API, got fewer or none")
                    
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
            
            logger.info("GUI successfully refreshed with new metrics.")
        else:
            # On error, maintain older readings but show error status in footer
            self.last_update_str.set(f"Error ({now.strftime('%H:%M')}): {error_msg}")
            self.status_dot_color = COLOR_ACCENT_RED
            self.draw_status_dot(COLOR_ACCENT_RED)
            logger.warning(f"GUI refresh completed with failures: {error_msg}")

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
