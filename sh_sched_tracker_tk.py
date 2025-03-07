import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import json
import time
from datetime import datetime, timedelta
import sys
import os
from PIL import Image, ImageTk
import pystray
import threading
import platform

class ScheduleTrackerTk:
    def __init__(self, enable_test_mode=False):
        self.root = tk.Tk()
        self.root.title("SH Schedule Tracker")
        self.root.attributes('-topmost', True)
        self.root.resizable(False, False)

        # Set application icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set application icon: {e}")

        # Initialize variables
        self.test_mode = False  # Always start with test mode disabled
        self.test_time = datetime.strptime("07:00", "%H:%M").time()
        self.test_timer = None
        self.test_delay = 1000  # milliseconds between time updates in test mode
        self.settings = {}
        self.load_settings()
        
        # Set initial window size
        self.root.geometry("325x225")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create menu bar
        self.create_menu()

        # Create schedule display
        self.create_schedule_display()

        # Create test panel
        self.create_test_panel()

        # Create system tray icon only on Windows
        self.tray_icon = None
        if platform.system() == 'Windows':
            self.create_tray_icon()
            # Start tray icon in a separate thread
            threading.Thread(target=lambda: self.tray_icon.run(), daemon=True).start()

        # Start timer for updates
        self.update_timer()

        # Apply initial colors
        self.apply_colors()
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure('Period.TLabel', font=('Arial', 12, 'bold'))

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set window position after all widgets are created
        self.root.update_idletasks()
        self.restore_window_position()
        
        self.current_period = "Not in session"
        self.is_visible = True
        self.password = self.settings.get('password', '')

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Color Settings...", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)

        # Tools menu - always visible
        self.tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Edit Schedule...", command=self.edit_schedule)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Enable Test Mode", command=self.enable_test_mode)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="About", command=self.show_about)

    def create_schedule_display(self):
        # Regular schedule frame
        regular_frame = ttk.LabelFrame(self.main_frame, text="Regular Schedule", style='Period.TLabelframe')
        regular_frame.grid(row=0, column=0, padx=5, pady=5)
        
        self.regular_label = ttk.Label(regular_frame, text="Not in session", style='Period.TLabel', width=30)
        self.regular_label.grid(row=0, column=0, padx=5, pady=5)

        # Two Hour Delay schedule frame
        delay_frame = ttk.LabelFrame(self.main_frame, text="Two Hour Delay", style='Period.TLabelframe')
        delay_frame.grid(row=1, column=0, padx=5, pady=5)
        
        self.delay_label = ttk.Label(delay_frame, text="Not in session", style='Period.TLabel', width=30)
        self.delay_label.grid(row=0, column=0, padx=5, pady=5)

        # Homeroom schedule frame
        homeroom_frame = ttk.LabelFrame(self.main_frame, text="Homeroom Schedule", style='Period.TLabelframe')
        homeroom_frame.grid(row=2, column=0, padx=5, pady=5)
        
        self.homeroom_label = ttk.Label(homeroom_frame, text="Not in session", style='Period.TLabel', width=30)
        self.homeroom_label.grid(row=0, column=0, padx=5, pady=5)

        # Configure grid weights for better resizing
        self.main_frame.grid_columnconfigure(0, weight=1)
        for i in range(3):  # Three rows for three schedules
            self.main_frame.grid_rowconfigure(i, weight=1)

        # Set minimum window size
        self.root.minsize(325, 225)

    def create_tray_icon(self):
        """Create system tray icon (Windows only)"""
        try:
            # Load icon image
            icon_path = self.get_resource_path("clock.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                
                self.tray_icon = pystray.Icon(
                    "schedule_tracker",
                    image,
                    "Schedule Tracker"  # Initial tooltip
                )
        except Exception as e:
            print(f"Failed to create system tray icon: {e}")
            self.tray_icon = None

    def minimize_window(self):
        """Minimize window based on platform"""
        if platform.system() == 'Windows':
            # On Windows, just minimize to taskbar
            self.root.iconify()
        else:
            # On macOS/Linux, use standard window minimize
            self.root.iconify()

    def on_close(self):
        """Handle window close button"""
        if platform.system() == 'Windows':
            self.save_window_position()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.quit()
        else:
            # For non-Windows systems, just quit
            self.save_window_position()
            self.root.quit()

    def update_timer(self):
        """Update the display with current time"""
        if self.test_mode:
            if self.test_timer is not None:
                # In test mode with active timer, use test time
                current_time = self.test_time
            else:
                # In test mode without active timer, keep using the last set test time
                current_time = self.test_time
        else:
            # Use real time in normal mode
            current_time = datetime.now().time()
        
        self.update_schedule_display(current_time)
        
        # Only schedule next update if not in test mode or if test timer is not active
        if not self.test_mode or self.test_timer is None:
            self.root.after(1000, self.update_timer)

    def update_schedule_display(self, current_time):
        # Update window title with current time
        time_str = current_time.strftime("%H:%M")
        self.root.title(f"SH Schedule Tracker - {time_str}")
        
        # Get schedule messages
        regular_period = self.get_current_period(current_time, "regular")
        delay_period = self.get_current_period(current_time, "two_hour_delay")
        homeroom_period = self.get_current_period(current_time, "homeroom_schedule")
        
        # Update labels
        self.regular_label.configure(text=regular_period, style='Period.TLabel')
        self.delay_label.configure(text=delay_period, style='Period.TLabel')
        self.homeroom_label.configure(text=homeroom_period, style='Period.TLabel')
        
        # Update tray tooltip (Windows only)
        if platform.system() == 'Windows' and self.tray_icon:
            tooltip = (f"Current Time: {time_str}\n"
                      f"Regular: {regular_period}\n"
                      f"2-Hour Delay: {delay_period}\n"
                      f"Homeroom: {homeroom_period}")
            self.tray_icon.title = tooltip

    def get_current_period(self, current_time, schedule_type):
        # Remove '_schedule' suffix if present for regular schedule
        if schedule_type == 'regular_schedule':
            schedule_type = 'regular'
        
        schedule = self.settings.get(f'{schedule_type}', [])
        
        if not schedule:
            return "No schedule defined"
        
        # Sort periods by start time and filter out periods with None start or end times
        valid_periods = [p for p in schedule if p.get('start') is not None and p.get('end') is not None]
        
        if not valid_periods:
            return "No valid periods defined"
        
        try:
            sorted_periods = sorted(valid_periods, key=lambda x: datetime.strptime(x['start'], "%H:%M"))
            
            # Check if after last period (after 14:30)
            last_end_time = datetime.strptime("14:30", "%H:%M").time()
            if current_time > last_end_time:
                return "After School"
            
            # Find Period 1 start time for the "waiting for period 1" message
            period_1 = next((p for p in sorted_periods if str(p['name']) == '1'), None)
            if period_1:
                period_1_start = datetime.strptime(period_1['start'], "%H:%M").time()
                if current_time < period_1_start:
                    return f"Period 1 starts at {period_1['start']}"
            
            # Check if before first period
            first_period = sorted_periods[0]
            first_start = datetime.strptime(first_period['start'], "%H:%M").time()
            
            if current_time < first_start:
                return "Before School"
            
            # Check current period and transitions
            for i, period in enumerate(sorted_periods):
                start_time = datetime.strptime(period['start'], "%H:%M").time()
                end_time = datetime.strptime(period['end'], "%H:%M").time()
                
                if start_time <= current_time <= end_time:
                    # Convert period name to string and check if it's a number
                    period_name = str(period['name'])
                    if period_name.isdigit():
                        return f"Period {period_name}"
                    else:
                        return period_name
                
                # Check for transition between periods
                if i < len(sorted_periods) - 1:  # If not the last period
                    next_period = sorted_periods[i + 1]
                    next_start = datetime.strptime(next_period['start'], "%H:%M").time()
                    
                    if end_time < current_time < next_start:
                        # Format period names
                        current_name = str(period['name'])
                        next_name = str(next_period['name'])
                        current_display = f"Period {current_name}" if current_name.isdigit() else current_name
                        next_display = f"Period {next_name}" if next_name.isdigit() else next_name
                        return f"{current_display} → {next_display}"
                
            return "Not in session"
            
        except (ValueError, TypeError) as e:
            print(f"Error processing schedule: {e}")
            return "Error in schedule format"

    def edit_schedule(self):
        if self.check_password():
            self.show_schedule_editor()

    def show_schedule_editor(self):
        editor = ScheduleEditorDialog(self.root, self.settings)
        if editor.result:
            self.settings = editor.result
            self.save_settings()

    def show_settings(self):
        settings_dialog = SettingsDialog(self.root, self.settings)
        if settings_dialog.result:
            self.settings = settings_dialog.result
            self.save_settings()
            self.apply_colors()  # Apply new colors immediately

    def check_password(self):
        if not self.password:
            return True
        
        dialog = PasswordDialog(self.root)
        return dialog.result == self.password

    def load_settings(self):
        try:
            # Load settings
            try:
                with open('schedule_settings.json', 'r') as f:
                    self.settings = json.load(f)
            except FileNotFoundError:
                self.settings = self.get_default_settings()
                self.save_settings()
            
            # Load schedules
            try:
                with open('schedules.json', 'r') as f:
                    schedules_data = json.load(f)
                    if 'southampton_high_school' in schedules_data:
                        school_data = schedules_data['southampton_high_school']
                        # Debug print
                        print("Loaded schedule data:", school_data)
                        # Update settings with schedule data
                        self.settings.update({
                            'regular': school_data.get('regular_schedule', {}).get('periods', []),
                            'two_hour_delay': school_data.get('two_hour_delay', {}).get('periods', []),
                            'homeroom_schedule': school_data.get('homeroom_schedule', {}).get('periods', [])
                        })
                        # Debug print
                        print("Updated settings:", self.settings)
            except FileNotFoundError:
                print("Warning: schedules.json not found")
            except json.JSONDecodeError:
                print("Warning: Invalid JSON in schedules.json")
            
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            self.settings = self.get_default_settings()

    def save_settings(self):
        # Save settings
        with open('schedule_settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        
        # Save schedules
        try:
            with open('schedules.json', 'r') as f:
                schedules_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            schedules_data = {'southampton_high_school': {}}
        
        # Update schedules data
        if 'southampton_high_school' not in schedules_data:
            schedules_data['southampton_high_school'] = {}
        
        school_data = schedules_data['southampton_high_school']
        school_data.update({
            'regular_schedule': {'periods': self.settings.get('regular', [])},
            'two_hour_delay': {'periods': self.settings.get('two_hour_delay', [])},
            'homeroom_schedule': {'periods': self.settings.get('homeroom_schedule', [])}
        })
        
        # Save updated schedules
        with open('schedules.json', 'w') as f:
            json.dump(schedules_data, f, indent=4)

    def get_default_settings(self):
        return {
            'regular': [],
            'two_hour_delay': [],
            'homeroom_schedule': [],
            'password': '',
            'window_color': '#FFFFFF',
            'text_color': '#000000',
            'label_bg_color': '#E0E0E0',    # Message background
            'label_text_color': '#000000',   # Message text
            'frame_bg_color': '#D0D0D0',    # Schedule frame label background
            'frame_text_color': '#000000'    # Schedule frame label text
        }

    def get_resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def show_user_guide(self):
        try:
            # Get the path to user_guide_tk.md
            guide_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_guide_tk.md")
            
            # Read the contents of the file
            with open(guide_path, 'r', encoding='utf-8') as f:
                guide_text = f.read()
            
            # Create custom dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("User Guide")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Set dark blue background
            dialog.configure(bg='#000080')  # Dark blue background
            
            # Center dialog on parent window
            dialog.update_idletasks()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Create text widget with scrollbar
            text_frame = ttk.Frame(dialog)
            text_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side='right', fill='y')
            
            # Create text widget with custom colors and bold font
            text_widget = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set, 
                                font=('Arial', 10, 'bold'),
                                bg='#000080',  # Dark blue background
                                fg='white',    # White text
                                insertbackground='white')  # White cursor
            text_widget.pack(side='left', fill='both', expand=True)
            
            scrollbar.config(command=text_widget.yview)
            
            # Insert the guide text
            text_widget.insert('1.0', guide_text)
            text_widget.config(state='disabled')  # Make text read-only
            
            # Style the OK button
            style = ttk.Style()
            style.configure('Guide.TButton', font=('Arial', 10, 'bold'))
            
            # OK button with custom style
            ttk.Button(dialog, text="OK", command=dialog.destroy, style='Guide.TButton').pack(pady=10)
            
            # Set dialog icon
            try:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
                if os.path.exists(icon_path):
                    dialog.iconbitmap(icon_path)
            except Exception as e:
                print(f"Failed to set dialog icon: {e}")
            
            dialog.wait_window()
            
        except FileNotFoundError:
            messagebox.showerror("Error", "User guide file not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load user guide: {str(e)}")

    def show_about(self):
        app_name = "SH Schedule Tracker"
        app_gui = "Tkinter"
        app_version = "1.01"
        app_author = "Fragillidae Software"
        app_web = "www.fragillidae.com"
        app_email = "info@fragillidae.com"
        
        # Create custom dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("About")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog on parent window
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Create and pack widgets
        ttk.Label(dialog, text=app_name, font=('Arial', 12, 'bold')).pack(pady=(10,5))
        ttk.Label(dialog, text=f"GUI Type: {app_gui}", font=('Arial', 10, 'bold')).pack()
        ttk.Label(dialog, text=f"Version: {app_version}", font=('Arial', 10, 'bold')).pack()
        ttk.Label(dialog, text="", font=('Arial', 10)).pack(pady=5)
        ttk.Label(dialog, text=app_author, font=('Arial', 10, 'bold')).pack()
        
        # Create frame for links
        links_frame = ttk.Frame(dialog)
        links_frame.pack(pady=5)
        
        # Create web link
        web_link = ttk.Label(links_frame, text=app_web, font=('Arial', 10, 'bold'), foreground='blue', cursor='hand2')
        web_link.pack()
        web_link.bind('<Button-1>', lambda e: self.open_url(f"https://{app_web}"))
        web_link.bind('<Enter>', lambda e: web_link.configure(underline=True))
        web_link.bind('<Leave>', lambda e: web_link.configure(underline=False))
        
        # Create email link
        email_link = ttk.Label(links_frame, text=app_email, font=('Arial', 10, 'bold'), foreground='blue', cursor='hand2')
        email_link.pack()
        email_link.bind('<Button-1>', lambda e: self.open_url(f"mailto:{app_email}"))
        email_link.bind('<Enter>', lambda e: email_link.configure(underline=True))
        email_link.bind('<Leave>', lambda e: email_link.configure(underline=False))
        
        # OK button
        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=10)
        
        # Set dialog icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set dialog icon: {e}")
        
        dialog.wait_window()

    def open_url(self, url):
        """Open a URL in the default web browser"""
        import webbrowser
        webbrowser.open(url)

    def quit_app(self):
        """Handle exit from menu"""
        if platform.system() == 'Windows':
            self.save_window_position()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.quit()
        else:
            self.save_window_position()
            self.root.quit()

    def run(self):
        self.root.mainloop()

    def apply_colors(self):
        # Get colors from settings
        bg_color = self.settings.get('window_color', '#FFFFFF')
        fg_color = self.settings.get('text_color', '#000000')
        label_bg = self.settings.get('label_bg_color', '#E0E0E0')
        label_fg = self.settings.get('label_text_color', '#000000')
        frame_bg = self.settings.get('frame_bg_color', '#D0D0D0')
        frame_fg = self.settings.get('frame_text_color', '#000000')
        
        self.root.configure(bg=bg_color)
        self.main_frame.configure(style='Main.TFrame')
        
        # Create custom styles for widgets with bold font
        self.style = ttk.Style()
        self.style.configure('Main.TFrame', background=bg_color)
        self.style.configure('Period.TLabel', 
                            background=label_bg, 
                            foreground=label_fg, 
                            font=('Arial', 12, 'bold'))
        self.style.configure('Period.TLabelframe', 
                            background=frame_bg, 
                            foreground=frame_fg)
        self.style.configure('Period.TLabelframe.Label', 
                            background=frame_bg, 
                            foreground=frame_fg, 
                            font=('Arial', 12, 'bold'))
        
        # Apply to existing widgets
        label_names = ['regular_label', 'delay_label', 'homeroom_label']
        for label_name in label_names:
            if hasattr(self, label_name):
                getattr(self, label_name).configure(style='Period.TLabel')

    def enable_test_mode(self):
        """Toggle test mode on/off with password protection"""
        if not self.test_mode:
            # Check password
            dialog = PasswordDialog(self.root, default_password='shs')
            if not dialog.result == 'shs':
                messagebox.showerror("Error", "Incorrect password")
                return

        # Toggle test mode
        self.test_mode = not self.test_mode
        
        if self.test_mode:
            # Show test panel and resize window
            self.test_panel.grid()
            self.root.geometry("325x400")
            self.tools_menu.entryconfigure(2, label="Disable Test Mode")
            # Initialize test time to current time
            self.test_time = datetime.now().time()
            self.hour_spinner.set(f"{self.test_time.hour:02d}")
            self.minute_spinner.set(f"{self.test_time.minute:02d}")
            # Start real-time updates
            self.update_timer()
        else:
            # Hide test panel and restore window size
            self.stop_auto_test()
            self.test_panel.grid_remove()
            self.root.geometry("325x225")
            self.tools_menu.entryconfigure(2, label="Enable Test Mode")
            # Restart real-time updates
            self.update_timer()

    def set_test_time(self):
        """Set the test time from the spinners"""
        try:
            hours = int(self.hour_spinner.get())
            minutes = int(self.minute_spinner.get())
            self.test_time = datetime.strptime(f"{hours:02d}:{minutes:02d}", "%H:%M").time()
            # Cancel any existing test timer
            if self.test_timer:
                self.root.after_cancel(self.test_timer)
                self.test_timer = None
            self.update_schedule_display(self.test_time)
            self.test_status.configure(text=f"Manual test time set to {self.test_time.strftime('%H:%M')}")
        except ValueError:
            messagebox.showerror("Error", "Invalid time format")

    def start_auto_test(self):
        """Start automated testing"""
        try:
            delay = int(self.delay_spinner.get())
            if delay < 1 or delay > 60:
                raise ValueError("Delay must be between 1 and 60 seconds")
            
            self.start_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            self.test_delay = delay * 1000  # Convert to milliseconds
            self.test_timer = self.root.after(0, self.update_test_time)  # Start immediately
            self.test_status.configure(text=f"Testing started with {delay} second delay")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.stop_auto_test()

    def stop_auto_test(self):
        """Stop automated testing"""
        if self.test_timer:
            self.root.after_cancel(self.test_timer)
            self.test_timer = None
        self.stop_button.configure(state='disabled')
        self.test_status.configure(text="Test stopped")
        # Restart real-time updates if in test mode
        if self.test_mode:
            self.update_timer()

    def update_test_time(self):
        """Update the test time and schedule next update"""
        if self.test_mode and self.test_timer is not None:
            # Move to next time in the list
            self.current_time_index += 1
            
            # If we've reached the end of the times, stop testing
            if self.current_time_index >= len(self.test_times):
                self.stop_auto_test()
                self.test_status.configure(text="Test completed - reached end of file")
                return
            
            # Parse the next time
            time_str = self.test_times[self.current_time_index]
            time_formats = ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"]
            
            for fmt in time_formats:
                try:
                    self.test_time = datetime.strptime(time_str, fmt).time()
                    break
                except ValueError:
                    continue
            
            # Update spinners and display
            self.hour_spinner.set(f"{self.test_time.hour:02d}")
            self.minute_spinner.set(f"{self.test_time.minute:02d}")
            self.update_schedule_display(self.test_time)
            self.test_status.configure(text=f"Testing time: {self.test_time.strftime('%H:%M')}")
            
            # Schedule next update
            self.test_timer = self.root.after(self.test_delay, self.update_test_time)

    def load_test_file(self):
        """Load a test time file and start automated testing"""
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = filedialog.askopenfilename(
            title="Select Test File",
            initialdir=initial_dir,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    # Read all lines and filter out empty lines
                    self.test_times = [line.strip() for line in f.readlines() if line.strip()]
                    
                    if not self.test_times:
                        raise ValueError("File is empty")
                    
                    # Try different time formats
                    time_formats = ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"]
                    test_time = None
                    
                    # Parse the first time
                    for fmt in time_formats:
                        try:
                            test_time = datetime.strptime(self.test_times[0], fmt).time()
                            break
                        except ValueError:
                            continue
                    
                    if test_time is None:
                        raise ValueError(f"Invalid time format in file. Please use one of these formats:\n" +
                                       "HH:MM (24-hour)\n" +
                                       "HH:MM:SS (24-hour with seconds)\n" +
                                       "HH:MM AM/PM (12-hour)\n" +
                                       "HH:MM:SS AM/PM (12-hour with seconds)")
                    
                    # Set initial time and update display
                    self.test_time = test_time
                    self.hour_spinner.set(f"{test_time.hour:02d}")
                    self.minute_spinner.set(f"{test_time.minute:02d}")
                    self.update_schedule_display(self.test_time)
                    self.test_status.configure(text=f"Initial time set to {test_time.strftime('%H:%M')}")
                    
                    # Get delay and start automated testing
                    try:
                        delay = int(self.delay_spinner.get())
                        if delay < 1 or delay > 60:
                            raise ValueError("Delay must be between 1 and 60 seconds")
                        
                        self.test_delay = delay * 1000  # Convert to milliseconds
                        self.current_time_index = 0  # Start with first time
                        # Enable stop button before starting test
                        self.stop_button.configure(state='normal')
                        # Wait for the specified delay before starting the automated test
                        self.test_timer = self.root.after(self.test_delay, self.update_test_time)
                        self.test_status.configure(text=f"Testing started with {delay} second delay")
                    except ValueError as e:
                        messagebox.showerror("Error", str(e))
                        self.stop_auto_test()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load test file: {str(e)}")

    def create_test_panel(self):
        """Create the test mode panel"""
        self.test_panel = ttk.LabelFrame(self.main_frame, text="Test Mode Controls", style='Period.TLabelframe')
        self.test_panel.grid(row=3, column=0, padx=5, pady=5, sticky='nsew')
        self.test_panel.grid_remove()  # Hidden by default

        # Time setting controls
        time_frame = ttk.Frame(self.test_panel)
        time_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(time_frame, text="Test Time:").pack(side='left', padx=5)
        self.hour_spinner = ttk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f")
        self.hour_spinner.pack(side='left')
        ttk.Label(time_frame, text=":").pack(side='left')
        self.minute_spinner = ttk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
        self.minute_spinner.pack(side='left')
        
        ttk.Button(time_frame, text="Set Time", command=self.set_test_time).pack(side='left', padx=5)

        # Delay controls
        delay_frame = ttk.Frame(self.test_panel)
        delay_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(delay_frame, text="Delay (seconds):").pack(side='left', padx=5)
        self.delay_spinner = ttk.Spinbox(delay_frame, from_=1, to=60, width=3)
        self.delay_spinner.pack(side='left')
        self.delay_spinner.set("5")  # Set default delay to 5 seconds
        # Bind delay spinner changes
        self.delay_spinner.bind('<KeyRelease>', self.on_delay_change)
        self.delay_spinner.bind('<ButtonRelease-1>', self.on_delay_change)

        # File and control buttons
        button_frame = ttk.Frame(self.test_panel)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Load Test File", command=self.load_test_file).pack(side='left', padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_auto_test, state='disabled')
        self.stop_button.pack(side='left', padx=5)

        # Test status label
        self.test_status = ttk.Label(self.test_panel, text="No test running", style='Period.TLabel')
        self.test_status.pack(fill='x', padx=5, pady=5)

    def on_delay_change(self, event=None):
        """Handle delay spinner changes"""
        try:
            delay = int(self.delay_spinner.get())
            if delay < 1 or delay > 60:
                raise ValueError("Delay must be between 1 and 60 seconds")
            
            self.test_delay = delay * 1000  # Convert to milliseconds
            if self.test_timer is not None:
                # Restart timer with new delay
                self.root.after_cancel(self.test_timer)
                self.test_timer = self.root.after(0, self.update_test_time)
                self.test_status.configure(text=f"Testing with {delay} second delay")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.stop_auto_test()

    def save_window_position(self):
        """Save current window position"""
        try:
            # Get the window geometry string (format: "widthxheight+x+y")
            geometry = self.root.geometry()
            # Parse the geometry string to get x and y coordinates
            # Split the geometry string and get the position part
            position = geometry.split('+')[1:]
            if len(position) == 2:
                x = int(position[0])
                y = int(position[1])
                # Only save if position is valid
                if x >= 0 and y >= 0:
                    self.settings['window_x'] = x
                    self.settings['window_y'] = y
                    self.save_settings()
        except Exception as e:
            print(f"Error saving window position: {e}")

    def restore_window_position(self):
        """Restore window position or center on screen"""
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            window_width = 325
            window_height = 225

            # Get saved position
            x = self.settings.get('window_x')
            y = self.settings.get('window_y')
            
            # If we have valid saved coordinates
            if x is not None and y is not None:
                # Ensure window is fully visible on screen
                if x < 0:
                    x = 0
                if y < 0:
                    y = 0
                if x + window_width > screen_width:
                    x = screen_width - window_width
                if y + window_height > screen_height:
                    y = screen_height - window_height
                    
                # Set window position
                self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            else:
                # Center on screen
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        except Exception as e:
            print(f"Error restoring window position: {e}")
            # Fallback to center position
            x = (self.root.winfo_screenwidth() - 325) // 2
            y = (self.root.winfo_screenheight() - 225) // 2
            self.root.geometry(f"325x225+{x}+{y}")

    def toggle_window(self, *args):  # Accept any arguments
        """Toggle window visibility"""
        if self.is_visible:
            self.root.withdraw()  # Hide window
            self.is_visible = False
        else:
            self.root.deiconify()  # Show window
            self.root.lift()       # Bring to front
            self.is_visible = True

class ScheduleEditorDialog:
    def __init__(self, parent, settings):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Schedule Editor")
        self.dialog.transient(parent)
        self.settings = settings.copy()
        self.result = None
        
        # Load schedules from JSON file
        self.load_schedules_from_json()
        
        self.create_editor()
        
        # Center dialog on parent window
        self.dialog.update_idletasks()  # Update dialog size
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Set dialog icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set dialog icon: {e}")
        
        self.dialog.wait_window()

    def load_schedules_from_json(self):
        """Load schedules from schedules.json file"""
        try:
            with open('schedules.json', 'r') as f:
                schedules_data = json.load(f)
                if 'southampton_high_school' in schedules_data:
                    school_data = schedules_data['southampton_high_school']
                    # Update settings with schedule data
                    self.settings.update({
                        'regular': school_data.get('regular_schedule', {}).get('periods', []),
                        'two_hour_delay': school_data.get('two_hour_delay', {}).get('periods', []),
                        'homeroom_schedule': school_data.get('homeroom_schedule', {}).get('periods', [])
                    })
        except FileNotFoundError:
            messagebox.showwarning("Warning", "schedules.json not found. Creating new file.")
            self.save_schedules_to_json()
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON in schedules.json")
            self.settings.update({
                'regular': [],
                'two_hour_delay': [],
                'homeroom_schedule': []
            })
            self.save_schedules_to_json()

    def save_schedules_to_json(self):
        """Save schedules to schedules.json file"""
        try:
            # Load existing schedules data or create new structure
            try:
                with open('schedules.json', 'r') as f:
                    schedules_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                schedules_data = {'southampton_high_school': {}}

            # Update schedules data
            if 'southampton_high_school' not in schedules_data:
                schedules_data['southampton_high_school'] = {}

            school_data = schedules_data['southampton_high_school']
            
            # Only update the schedules that were modified
            if hasattr(self, 'modified_schedules'):
                for schedule_type in self.modified_schedules:
                    if schedule_type == 'regular':
                        school_data['regular_schedule'] = {'periods': self.settings.get('regular', [])}
                    elif schedule_type == 'two_hour_delay':
                        school_data['two_hour_delay'] = {'periods': self.settings.get('two_hour_delay', [])}
                    elif schedule_type == 'homeroom_schedule':
                        school_data['homeroom_schedule'] = {'periods': self.settings.get('homeroom_schedule', [])}

            # Save updated schedules
            with open('schedules.json', 'w') as f:
                json.dump(schedules_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save schedules: {str(e)}")

    def create_editor(self):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # Regular Schedule Tab
        regular_frame = ttk.Frame(notebook)
        notebook.add(regular_frame, text='Regular Schedule')
        self.create_schedule_table(regular_frame, 'regular')

        # Two Hour Delay Tab
        delay_frame = ttk.Frame(notebook)
        notebook.add(delay_frame, text='Two Hour Delay')
        self.create_schedule_table(delay_frame, 'two_hour_delay')

        # Homeroom Schedule Tab
        homeroom_frame = ttk.Frame(notebook)
        notebook.add(homeroom_frame, text='Homeroom Schedule')
        self.create_schedule_table(homeroom_frame, 'homeroom_schedule')

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Save", command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right')

    def create_schedule_table(self, parent, schedule_type):
        # Create table
        columns = ('Period', 'Start Time', 'End Time')
        tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        tree.pack(expand=True, fill='both')

        # Add buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Add", 
                  command=lambda: self.add_period(tree, schedule_type)).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Edit", 
                  command=lambda: self.edit_period(tree, schedule_type)).pack(side='left')
        ttk.Button(button_frame, text="Delete", 
                  command=lambda: self.delete_period(tree, schedule_type)).pack(side='left', padx=5)

        # Load existing schedule
        self.load_schedule(tree, schedule_type)

    def load_schedule(self, tree, schedule_type):
        for period in self.settings.get(schedule_type, []):
            tree.insert('', 'end', values=(period['name'], period['start'], period['end']))

    def add_period(self, tree, schedule_type):
        dialog = PeriodDialog(self.dialog)
        if dialog.result:
            tree.insert('', 'end', values=dialog.result)
            self.update_settings_from_tree(tree, schedule_type)
            if not hasattr(self, 'modified_schedules'):
                self.modified_schedules = set()
            self.modified_schedules.add(schedule_type)

    def edit_period(self, tree, schedule_type):
        selected = tree.selection()
        if not selected:
            return
        
        item = tree.item(selected[0])
        dialog = PeriodDialog(self.dialog, item['values'])
        if dialog.result:
            tree.item(selected[0], values=dialog.result)
            self.update_settings_from_tree(tree, schedule_type)
            if not hasattr(self, 'modified_schedules'):
                self.modified_schedules = set()
            self.modified_schedules.add(schedule_type)

    def delete_period(self, tree, schedule_type):
        selected = tree.selection()
        if selected and messagebox.askyesno("Confirm Delete", "Delete selected period?"):
            tree.delete(selected[0])
            self.update_settings_from_tree(tree, schedule_type)
            if not hasattr(self, 'modified_schedules'):
                self.modified_schedules = set()
            self.modified_schedules.add(schedule_type)

    def update_settings_from_tree(self, tree, schedule_type):
        schedule = []
        for item_id in tree.get_children():
            values = tree.item(item_id)['values']
            schedule.append({
                'name': values[0],
                'start': values[1],
                'end': values[2]
            })
        self.settings[schedule_type] = schedule

    def save(self):
        """Save changes to both settings and JSON file"""
        self.result = self.settings
        self.save_schedules_to_json()
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()

class PeriodDialog:
    def __init__(self, parent, values=None):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Period Details")
        self.dialog.transient(parent)
        self.result = None
        
        self.create_widgets(values)
        
        # Center dialog on parent window
        self.dialog.update_idletasks()  # Update dialog size
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Set dialog icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set dialog icon: {e}")
        
        self.dialog.wait_window()

    def create_widgets(self, values):
        # Period Name
        ttk.Label(self.dialog, text="Period Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.dialog)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Start Time
        ttk.Label(self.dialog, text="Start Time (HH:MM):").grid(row=1, column=0, padx=5, pady=5)
        self.start_entry = ttk.Entry(self.dialog)
        self.start_entry.grid(row=1, column=1, padx=5, pady=5)

        # End Time
        ttk.Label(self.dialog, text="End Time (HH:MM):").grid(row=2, column=0, padx=5, pady=5)
        self.end_entry = ttk.Entry(self.dialog)
        self.end_entry.grid(row=2, column=1, padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right')

        # Set values if editing
        if values:
            self.name_entry.insert(0, values[0])
            self.start_entry.insert(0, values[1])
            self.end_entry.insert(0, values[2])

    def validate_time(self, time_str):
        """Validate time format HH:MM"""
        if not time_str:
            return False
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def save(self):
        name = self.name_entry.get().strip()
        start = self.start_entry.get().strip()
        end = self.end_entry.get().strip()

        # Validate inputs
        if not name:
            messagebox.showerror("Error", "Period name cannot be empty")
            return
        
        if not self.validate_time(start):
            messagebox.showerror("Error", "Invalid start time format. Use HH:MM")
            return
        
        if not self.validate_time(end):
            messagebox.showerror("Error", "Invalid end time format. Use HH:MM")
            return

        # Convert times to datetime for comparison
        start_time = datetime.strptime(start, "%H:%M")
        end_time = datetime.strptime(end, "%H:%M")

        if end_time <= start_time:
            messagebox.showerror("Error", "End time must be after start time")
            return

        self.result = (name, start, end)
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()

class SettingsDialog:
    def __init__(self, parent, settings):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.settings = settings.copy()
        self.result = None
        
        # Make dialog modal
        self.dialog.grab_set()
        
        # Handle window close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Set dialog icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                self.dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"Failed to set dialog icon: {e}")
        
        self.create_widgets()
        
        # Center dialog on parent window
        self.dialog.update_idletasks()  # Update dialog size
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.dialog.wait_window()

    def create_widgets(self):
        # Add icon at the top
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fragillidae.ico")
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
                # Resize icon to 32x32 pixels
                icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(icon_image)
                icon_label = ttk.Label(self.dialog, image=icon_photo)
                icon_label.image = icon_photo  # Keep a reference
                icon_label.grid(row=0, column=0, columnspan=3, pady=10)
        except Exception as e:
            print(f"Failed to load icon: {e}")

        # Window Colors
        ttk.Label(self.dialog, text="Window Colors:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(self.dialog, text="Background", 
                  command=lambda: self.choose_color('window_color')).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.dialog, text="Text", 
                  command=lambda: self.choose_color('text_color')).grid(row=1, column=2, padx=5, pady=5)

        # Message Frame Colors
        ttk.Label(self.dialog, text="Message Colors:").grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self.dialog, text="Background", 
                  command=lambda: self.choose_color('label_bg_color')).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(self.dialog, text="Text", 
                  command=lambda: self.choose_color('label_text_color')).grid(row=2, column=2, padx=5, pady=5)

        # Schedule Label Colors
        ttk.Label(self.dialog, text="Schedule Labels:").grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(self.dialog, text="Background", 
                  command=lambda: self.choose_color('frame_bg_color')).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(self.dialog, text="Text", 
                  command=lambda: self.choose_color('frame_text_color')).grid(row=3, column=2, padx=5, pady=5)

        # Color Preview Frame
        self.preview_frame = ttk.Frame(self.dialog)
        self.preview_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=10, sticky='ew')
        self.update_preview()

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        # Add Return to Defaults button
        ttk.Button(button_frame, text="Return to Defaults", 
                  command=self.set_default_colors).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="Save", 
                  command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.cancel).pack(side='right')

    def update_preview(self):
        # Clear existing preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        # Create preview labels
        preview_label = ttk.Label(self.preview_frame, text="Preview")
        preview_label.pack(pady=5)

        # Window preview
        window_preview = tk.Label(self.preview_frame, text="Window Colors",
                                bg=self.settings.get('window_color', '#FFFFFF'),
                                fg=self.settings.get('text_color', '#000000'))
        window_preview.pack(fill='x', padx=5, pady=2)

        # Message preview
        message_preview = tk.Label(self.preview_frame, text="Message Colors",
                                 bg=self.settings.get('label_bg_color', '#E0E0E0'),
                                 fg=self.settings.get('label_text_color', '#000000'))
        message_preview.pack(fill='x', padx=5, pady=2)

        # Schedule label preview
        frame_preview = tk.Label(self.preview_frame, text="Schedule Label Colors",
                               bg=self.settings.get('frame_bg_color', '#D0D0D0'),
                               fg=self.settings.get('frame_text_color', '#000000'))
        frame_preview.pack(fill='x', padx=5, pady=2)

    def choose_color(self, color_type):
        color = colorchooser.askcolor(color=self.settings.get(color_type))[1]
        if color:
            self.settings[color_type] = color
            self.update_preview()

    def set_default_colors(self):
        """Set all colors to default black and white"""
        self.settings.update({
            'window_color': '#000000',      # Black background
            'text_color': '#FFFFFF',        # White text
            'label_bg_color': '#000000',    # Black background
            'label_text_color': '#FFFFFF',  # White text
            'frame_bg_color': '#000000',    # Black background
            'frame_text_color': '#FFFFFF'   # White text
        })
        self.update_preview()

    def save(self):
        self.result = self.settings
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()

class PasswordDialog:
    def __init__(self, parent, default_password=''):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Enter Password")
        self.dialog.transient(parent)
        self.result = None
        
        # Make dialog modal
        self.dialog.grab_set()
        
        # Handle window close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Bind keyboard events
        self.dialog.bind('<Return>', lambda e: self.save())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        self.create_widgets()
        
        # Center dialog on parent
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50))
        
        # Set focus to password entry
        self.password_entry.focus_set()
        
        self.dialog.wait_window()

    def create_widgets(self):
        ttk.Label(self.dialog, text="Password:").pack(padx=5, pady=5)
        
        self.password_entry = ttk.Entry(self.dialog, show="*")
        self.password_entry.pack(padx=5, pady=5)
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="OK", command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right', padx=5)

    def save(self):
        self.result = self.password_entry.get()
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

class TimeInputDialog:
    def __init__(self, parent, current_time):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Test Time")
        self.dialog.transient(parent)
        self.result = None
        
        ttk.Label(self.dialog, text="Enter time (HH:MM):").pack(padx=5, pady=5)
        
        self.time_entry = ttk.Entry(self.dialog)
        self.time_entry.pack(padx=5, pady=5)
        self.time_entry.insert(0, current_time.strftime("%H:%M"))
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="OK", command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right')
        
        self.dialog.wait_window()

    def save(self):
        self.result = self.time_entry.get()
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()

class DelayInputDialog:
    def __init__(self, parent, current_delay):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Time Delay")
        self.dialog.transient(parent)
        self.result = None
        
        ttk.Label(self.dialog, text="Enter delay (milliseconds):").pack(padx=5, pady=5)
        
        self.delay_entry = ttk.Entry(self.dialog)
        self.delay_entry.pack(padx=5, pady=5)
        self.delay_entry.insert(0, str(current_delay))
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="OK", command=self.save).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side='right')
        
        self.dialog.wait_window()

    def save(self):
        try:
            self.result = int(self.delay_entry.get())
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def cancel(self):
        self.dialog.destroy()

if __name__ == "__main__":
    app = ScheduleTrackerTk(enable_test_mode=True)
    app.run()
