"""
iRacing Telemetry Tool - GUI
Tkinter-based interface for capturing and exporting telemetry data.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import queue

# Import existing functionality
from src.capture import TelemetryCapture
from src.storage import list_all_sessions, load_session
from src.exporter import DataExporter

# Try to import irsdk for connection checking
try:
    import irsdk
    IRSDK_AVAILABLE = True
except ImportError:
    IRSDK_AVAILABLE = False

COLORS = {
    'bg_dark': '#0a0a0a',
    'bg_panel': '#111111',
    'bg_card': '#1a1a1a',
    'bg_hover': '#222222',
    'border': '#2a2a2a',
    'text': '#e0e0e0',
    'text_dim': '#666666',
    'accent_red': '#e63946',
    'accent_green': '#4ade80',
    'accent_purple': '#a855f7',
    'accent_yellow': '#f59e0b',
}


class TelemetryGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("iRacing Telemetry Tool")
        self.root.geometry("750x550")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(650, 450)

        # State
        self.is_capturing = False
        self.is_connected = False
        self.selected_session = None
        self.sessions = []
        self.capture_thread = None
        self.telemetry_queue = queue.Queue()

        # Constants
        self.POLL_RATE = 60
        self.CHANNEL_COUNT = 14

        # Build UI
        self._create_ui()
        self._load_sessions()
        self._start_polling()

    def _create_ui(self):
        """Build the complete UI."""
        # Main container
        main_container = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main_container.pack(fill='both', expand=True)

        # Sidebar
        self._create_sidebar(main_container)

        # Main panel
        self._create_main_panel(main_container)

    def _create_sidebar(self, parent):
        """Create the sessions list sidebar."""
        sidebar = tk.Frame(parent, bg=COLORS['bg_panel'], width=220)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        # Header
        header = tk.Label(
            sidebar,
            text="SESSIONS",
            font=('Consolas', 9, 'bold'),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_panel'],
            anchor='w'
        )
        header.pack(fill='x', padx=16, pady=(16, 8))

        # Session list container with scrollbar
        list_container = tk.Frame(sidebar, bg=COLORS['bg_panel'])
        list_container.pack(fill='both', expand=True, padx=8)

        scrollbar = tk.Scrollbar(list_container, bg=COLORS['bg_panel'])
        scrollbar.pack(side='right', fill='y')

        self.session_canvas = tk.Canvas(
            list_container,
            bg=COLORS['bg_panel'],
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.session_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.session_canvas.yview)

        self.session_list_frame = tk.Frame(self.session_canvas, bg=COLORS['bg_panel'])
        self.session_canvas.create_window((0, 0), window=self.session_list_frame, anchor='nw')

        self.session_list_frame.bind('<Configure>',
            lambda e: self.session_canvas.configure(scrollregion=self.session_canvas.bbox('all')))

    def _create_main_panel(self, parent):
        """Create the main panel with stats and controls."""
        main_panel = tk.Frame(parent, bg=COLORS['bg_dark'])
        main_panel.pack(side='right', fill='both', expand=True)

        # Status bar
        self._create_status_bar(main_panel)

        # Stats cards
        self._create_stats_cards(main_panel)

        # Lap table
        self._create_lap_table(main_panel)

        # Action buttons
        self._create_action_buttons(main_panel)

    def _create_status_bar(self, parent):
        """Create the status bar at the top."""
        status_bar = tk.Frame(parent, bg=COLORS['bg_card'], height=40)
        status_bar.pack(fill='x', padx=16, pady=(16, 0))
        status_bar.pack_propagate(False)

        # Connection status (left)
        status_left = tk.Frame(status_bar, bg=COLORS['bg_card'])
        status_left.pack(side='left', pady=8, padx=12)

        self.connection_dot = tk.Label(
            status_left,
            text="●",
            font=('Consolas', 12),
            fg=COLORS['accent_red'],
            bg=COLORS['bg_card']
        )
        self.connection_dot.pack(side='left')

        self.connection_label = tk.Label(
            status_left,
            text="Disconnected",
            font=('Consolas', 9),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card']
        )
        self.connection_label.pack(side='left', padx=(6, 0))

        # Capture info (right)
        self.capture_info_label = tk.Label(
            status_bar,
            text="",
            font=('Consolas', 9),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card']
        )
        self.capture_info_label.pack(side='right', pady=8, padx=12)

    def _create_stats_cards(self, parent):
        """Create the three stats cards."""
        cards_container = tk.Frame(parent, bg=COLORS['bg_dark'])
        cards_container.pack(fill='x', padx=16, pady=(12, 0))

        # Current Lap
        self.current_lap_card = self._create_stat_card(
            cards_container, "Current", "—", "—"
        )
        self.current_lap_card.pack(side='left', fill='x', expand=True, padx=(0, 6))

        # Best Lap
        self.best_lap_card = self._create_stat_card(
            cards_container, "Best", "—", "—", accent=True
        )
        self.best_lap_card.pack(side='left', fill='x', expand=True, padx=6)

        # Delta
        self.delta_card = self._create_stat_card(
            cards_container, "Delta", "—", "to best"
        )
        self.delta_card.pack(side='left', fill='x', expand=True, padx=(6, 0))

    def _create_stat_card(self, parent, title, value, subtitle, accent=False):
        """Create a single stat card."""
        card = tk.Frame(parent, bg=COLORS['bg_card'], height=80)
        card.pack_propagate(False)

        # Title
        title_label = tk.Label(
            card,
            text=title,
            font=('Consolas', 8),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card']
        )
        title_label.pack(pady=(12, 4))

        # Value
        value_color = COLORS['accent_purple'] if accent else COLORS['text']
        value_label = tk.Label(
            card,
            text=value,
            font=('Consolas', 16, 'bold'),
            fg=value_color,
            bg=COLORS['bg_card']
        )
        value_label.pack()

        # Subtitle
        subtitle_label = tk.Label(
            card,
            text=subtitle,
            font=('Consolas', 8),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card']
        )
        subtitle_label.pack(pady=(2, 12))

        # Store references
        card.title_label = title_label
        card.value_label = value_label
        card.subtitle_label = subtitle_label

        return card

    def _create_lap_table(self, parent):
        """Create the laps table."""
        table_container = tk.Frame(parent, bg=COLORS['bg_dark'])
        table_container.pack(fill='both', expand=True, padx=16, pady=(12, 0))

        # Header
        header_frame = tk.Frame(table_container, bg=COLORS['bg_card'])
        header_frame.pack(fill='x')

        tk.Label(
            header_frame,
            text="LAP",
            font=('Consolas', 8, 'bold'),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card'],
            width=8,
            anchor='w'
        ).pack(side='left', padx=(12, 0), pady=8)

        tk.Label(
            header_frame,
            text="TIME",
            font=('Consolas', 8, 'bold'),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card'],
            width=12,
            anchor='w'
        ).pack(side='left', pady=8)

        tk.Label(
            header_frame,
            text="DELTA",
            font=('Consolas', 8, 'bold'),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_card'],
            width=12,
            anchor='w'
        ).pack(side='left', pady=8)

        # Scrollable lap list
        list_frame = tk.Frame(table_container, bg=COLORS['bg_dark'])
        list_frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')

        self.lap_canvas = tk.Canvas(
            list_frame,
            bg=COLORS['bg_dark'],
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.lap_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.lap_canvas.yview)

        self.lap_list_frame = tk.Frame(self.lap_canvas, bg=COLORS['bg_dark'])
        self.lap_canvas_window = self.lap_canvas.create_window((0, 0), window=self.lap_list_frame, anchor='nw')

        # Update scroll region when frame contents change
        self.lap_list_frame.bind('<Configure>',
            lambda e: self.lap_canvas.configure(scrollregion=self.lap_canvas.bbox('all')))

        # Make frame width match canvas width
        def _on_lap_canvas_configure(event):
            self.lap_canvas.itemconfig(self.lap_canvas_window, width=event.width)

        self.lap_canvas.bind('<Configure>', _on_lap_canvas_configure)

    def _create_action_buttons(self, parent):
        """Create the bottom action buttons."""
        button_frame = tk.Frame(parent, bg=COLORS['bg_dark'])
        button_frame.pack(fill='x', padx=16, pady=(12, 16))

        # Start/Stop capture button
        self.capture_button = tk.Button(
            button_frame,
            text="▶ START CAPTURE",
            font=('Consolas', 10, 'bold'),
            fg='#000000',
            bg='#22c55e',
            activebackground='#22c55e',
            relief='flat',
            cursor='hand2',
            command=self._toggle_capture
        )
        self.capture_button.pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 8))

        # Export session button
        self.export_all_button = tk.Button(
            button_frame,
            text="Export Session",
            font=('Consolas', 10),
            fg=COLORS['text'],
            bg=COLORS['bg_card'],
            activebackground=COLORS['bg_hover'],
            relief='flat',
            cursor='hand2',
            command=self._export_all_laps,
            state='disabled'
        )
        self.export_all_button.pack(side='left', fill='x', expand=True, ipady=8)

    def _load_sessions(self):
        """Load and display all sessions."""
        self.sessions = list_all_sessions()
        self._refresh_session_list()

    def _refresh_session_list(self):
        """Refresh the session list display."""
        # Clear existing
        for widget in self.session_list_frame.winfo_children():
            widget.destroy()

        # Add sessions
        for session in self.sessions:
            self._create_session_item(session)

    def _create_session_item(self, session):
        """Create a single session list item."""
        is_selected = self.selected_session == session['session_id']

        item_frame = tk.Frame(
            self.session_list_frame,
            bg=COLORS['bg_card'] if is_selected else COLORS['bg_panel'],
            cursor='hand2'
        )
        item_frame.pack(fill='x', pady=2)

        if is_selected:
            # Left accent border
            border = tk.Frame(item_frame, bg=COLORS['accent_red'], width=3)
            border.pack(side='left', fill='y')

        content = tk.Frame(item_frame, bg=item_frame['bg'])
        content.pack(side='left', fill='both', expand=True, padx=12, pady=8)

        # Track name
        track_label = tk.Label(
            content,
            text=session['track_name'],
            font=('Consolas', 9, 'bold' if is_selected else 'normal'),
            fg=COLORS['text'] if is_selected else COLORS['text_dim'],
            bg=content['bg'],
            anchor='w'
        )
        track_label.pack(fill='x')

        # Car + laps
        info_text = f"{session['car_name']} • {session['total_laps']} laps"
        info_label = tk.Label(
            content,
            text=info_text,
            font=('Consolas', 8),
            fg=COLORS['text_dim'],
            bg=content['bg'],
            anchor='w'
        )
        info_label.pack(fill='x')

        # Click handler
        item_frame.bind('<Button-1>', lambda e, sid=session['session_id']: self._select_session(sid))
        for child in item_frame.winfo_children():
            child.bind('<Button-1>', lambda e, sid=session['session_id']: self._select_session(sid))
            for subchild in child.winfo_children():
                subchild.bind('<Button-1>', lambda e, sid=session['session_id']: self._select_session(sid))

    def _select_session(self, session_id):
        """Select a session and display its details."""
        self.selected_session = session_id
        self._refresh_session_list()
        self._load_session_details(session_id)

    def _load_session_details(self, session_id):
        """Load and display session lap details."""
        session_data, filepath = load_session(session_id)
        if not session_data:
            return

        # Clear existing laps
        for widget in self.lap_list_frame.winfo_children():
            widget.destroy()

        laps = session_data.get('laps', [])
        if not laps:
            return

        # Find best lap
        best_time = min((lap['lap_time'] for lap in laps if lap.get('lap_time')), default=None)

        # Create lap rows
        for lap in laps:
            lap_number = lap.get('lap_number', 0) + 1  # Convert to 1-based
            lap_time = lap.get('lap_time')

            if not lap_time:
                continue

            is_best = (lap_time == best_time)
            delta = lap_time - best_time if best_time else 0

            self._create_lap_row(lap_number, lap_time, delta, is_best, session_id)

        # Force geometry update and refresh scroll region
        self.lap_list_frame.update_idletasks()
        self.lap_canvas.configure(scrollregion=self.lap_canvas.bbox('all'))

        # Update stats cards
        if best_time:
            best_lap_num = next(lap.get('lap_number', 0) + 1 for lap in laps if lap.get('lap_time') == best_time)
            self.best_lap_card.value_label.config(text=f"{best_time:.3f}s")
            self.best_lap_card.subtitle_label.config(text=f"Lap {best_lap_num}")

        # Enable export all button
        self.export_all_button.config(state='normal')

    def _create_lap_row(self, lap_number, lap_time, delta, is_best, session_id):
        """Create a single lap row."""
        row_frame = tk.Frame(
            self.lap_list_frame,
            bg=COLORS['bg_card'],
            height=40
        )
        row_frame.pack(fill='x', pady=1)
        row_frame.pack_propagate(False)

        # Star for best lap
        star_text = "★ " if is_best else "   "
        star_label = tk.Label(
            row_frame,
            text=star_text,
            font=('Consolas', 10),
            fg=COLORS['accent_purple'],
            bg=COLORS['bg_card'],
            width=3,
            anchor='w'
        )
        star_label.pack(side='left', padx=(12, 0))

        # Lap number
        lap_color = COLORS['accent_purple'] if is_best else COLORS['text']
        lap_label = tk.Label(
            row_frame,
            text=str(lap_number),
            font=('Consolas', 9, 'bold' if is_best else 'normal'),
            fg=lap_color,
            bg=COLORS['bg_card'],
            width=5,
            anchor='w'
        )
        lap_label.pack(side='left')

        # Lap time
        time_label = tk.Label(
            row_frame,
            text=f"{lap_time:.3f}s",
            font=('Consolas', 9, 'bold' if is_best else 'normal'),
            fg=lap_color,
            bg=COLORS['bg_card'],
            width=12,
            anchor='w'
        )
        time_label.pack(side='left')

        # Delta
        delta_text = "—" if is_best else f"+{delta:.3f}"
        delta_color = COLORS['accent_purple'] if is_best else COLORS['accent_yellow']
        delta_label = tk.Label(
            row_frame,
            text=delta_text,
            font=('Consolas', 9),
            fg=delta_color,
            bg=COLORS['bg_card'],
            width=12,
            anchor='w'
        )
        delta_label.pack(side='left')

        # Export button
        export_btn = tk.Button(
            row_frame,
            text="Export",
            font=('Consolas', 8),
            fg=COLORS['text_dim'],
            bg=COLORS['bg_hover'],
            activebackground=COLORS['border'],
            relief='flat',
            cursor='hand2',
            command=lambda: self._export_lap(session_id, lap_number)
        )
        export_btn.pack(side='right', padx=12)

    def _toggle_capture(self):
        """Toggle capture on/off."""
        if self.is_capturing:
            self._stop_capture()
        else:
            self._start_capture()

    def _start_capture(self):
        """Start telemetry capture in background thread."""
        # Check if capture is already running
        if self.capture_thread and self.capture_thread.is_alive():
            return

        if not self.is_connected and IRSDK_AVAILABLE:
            messagebox.showwarning(
                "iRacing Not Connected",
                "iRacing is not running or not in a session.\n\nPlease load into a session and try again."
            )
            return

        self.is_capturing = True
        self.capture_button.config(
            text="■ STOP CAPTURE",
            fg=COLORS['text'],
            bg=COLORS['accent_red']
        )
        self.capture_info_label.config(text=f"{self.POLL_RATE} Hz • {self.CHANNEL_COUNT} channels")

        # Start capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def _stop_capture(self):
        """Stop telemetry capture."""
        self.is_capturing = False
        self.capture_button.config(
            text="▶ START CAPTURE",
            fg='#000000',
            bg='#22c55e'
        )
        self.capture_info_label.config(text="")

        # Reset stats
        self.current_lap_card.value_label.config(text="—")
        self.current_lap_card.subtitle_label.config(text="—")
        self.delta_card.value_label.config(text="—")

        # Refresh session list after a delay
        self.root.after(2000, self._load_sessions)

    def _capture_loop(self):
        """Run capture loop in background thread."""
        try:
            capture = TelemetryCapture(poll_rate=self.POLL_RATE)

            # Override the run method to integrate with GUI
            capture.wait_for_iracing()

            while self.is_capturing:
                if not capture.ir.is_connected:
                    break

                telemetry = capture.get_telemetry()
                if telemetry:
                    capture.process_telemetry(telemetry)

                    # Update GUI via queue
                    self.telemetry_queue.put({
                        'current_lap': telemetry.get('lap'),
                        'speed': telemetry.get('speed'),
                        'best_lap_time': capture.best_lap_time,
                    })

                import time
                time.sleep(capture.poll_interval)

            # Save session when stopped
            capture.save_current_session(include_incomplete_lap=True)
            capture.disconnect()

        except Exception as e:
            print(f"Capture error: {e}")
            self.is_capturing = False

    def _export_lap(self, session_id, lap_number):
        """Export a specific lap."""
        try:
            session_data, _ = load_session(session_id)
            if not session_data:
                messagebox.showerror("Error", "Failed to load session data")
                return

            exporter = DataExporter()
            filepath = exporter.export_lap_to_csv(session_data, lap_number)

            if filepath:
                messagebox.showinfo(
                    "Export Complete",
                    f"Lap {lap_number} exported to:\n{filepath}"
                )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export lap:\n{str(e)}")

    def _export_all_laps(self):
        """Export all laps from selected session."""
        if not self.selected_session:
            return

        try:
            session_data, _ = load_session(self.selected_session)
            if not session_data:
                messagebox.showerror("Error", "Failed to load session data")
                return

            exporter = DataExporter()
            filepath = exporter.export_complete_session_to_csv(session_data)

            if filepath:
                messagebox.showinfo(
                    "Export Complete",
                    f"All laps exported to:\n{filepath}"
                )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{str(e)}")

    def _start_polling(self):
        """Start background polling for iRacing connection and telemetry updates."""
        self._check_iracing_connection()
        self._process_telemetry_queue()
        self.root.after(2000, self._start_polling)

    def _check_iracing_connection(self):
        """Check if iRacing is connected."""
        if not IRSDK_AVAILABLE:
            return

        try:
            ir = irsdk.IRSDK()
            connected = ir.startup() and ir.is_connected
            ir.shutdown()

            if connected != self.is_connected:
                self.is_connected = connected
                self._update_connection_status(connected)
        except:
            self.is_connected = False
            self._update_connection_status(False)

    def _update_connection_status(self, connected):
        """Update the connection status display."""
        if connected:
            self.connection_dot.config(fg=COLORS['accent_green'])
            self.connection_label.config(text="Connected", fg=COLORS['text'])
        else:
            self.connection_dot.config(fg=COLORS['accent_red'])
            self.connection_label.config(text="Disconnected", fg=COLORS['text_dim'])

    def _process_telemetry_queue(self):
        """Process telemetry updates from capture thread."""
        try:
            while True:
                data = self.telemetry_queue.get_nowait()

                # Update current lap display
                if data.get('current_lap'):
                    self.current_lap_card.subtitle_label.config(text=f"Lap {data['current_lap']}")

                # Update delta if we have best lap
                if data.get('best_lap_time'):
                    self.best_lap_card.value_label.config(text=f"{data['best_lap_time']:.3f}s")

        except queue.Empty:
            pass

    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = TelemetryGUI()
    app.run()
