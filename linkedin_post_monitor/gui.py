"""
GUI - CustomTkinter interface for LinkedIn Post Monitor
"""

import asyncio
import threading
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from .config_manager import ConfigManager
from .monitor import LinkedInMonitor
from .utils import logger


class LinkedInMonitorGUI:
    """Modern GUI for LinkedIn Post Monitor using CustomTkinter."""
    
    def __init__(self):
        """Initialize the GUI application."""
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("LinkedIn Post Monitor")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Config and monitor
        self.config: Optional[ConfigManager] = None
        self.monitor: Optional[LinkedInMonitor] = None
        self.is_unlocked = False
        
        # Async event loop
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        
        # Build UI
        self._build_ui()
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame,
            text="🔍 LinkedIn Post Monitor",
            font=("Helvetica", 28, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Create pages
        self._create_unlock_page()
        self._create_main_page()
        
        # Show unlock page initially
        self._show_unlock_page()
    
    def _create_unlock_page(self):
        """Create passphrase unlock page."""
        self.unlock_frame = ctk.CTkFrame(self.main_frame)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self.unlock_frame,
            text="Enter your passphrase to unlock the application",
            font=("Helvetica", 14)
        )
        instructions.pack(pady=20)
        
        # Passphrase entry
        self.passphrase_entry = ctk.CTkEntry(
            self.unlock_frame,
            placeholder_text="Passphrase",
            show="*",
            width=300,
            height=40
        )
        self.passphrase_entry.pack(pady=10)
        self.passphrase_entry.bind("<Return>", lambda e: self._unlock())
        
        # Unlock button
        self.unlock_btn = ctk.CTkButton(
            self.unlock_frame,
            text="Unlock",
            command=self._unlock,
            width=300,
            height=40
        )
        self.unlock_btn.pack(pady=10)
        
        # Status label
        self.unlock_status = ctk.CTkLabel(
            self.unlock_frame,
            text="",
            text_color="red"
        )
        self.unlock_status.pack(pady=10)
    
    def _create_main_page(self):
        """Create main application page."""
        self.main_content = ctk.CTkFrame(self.main_frame)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(self.main_content)
        self.tabview.pack(fill="both", expand=True, pady=10)
        
        # Add tabs
        self.tabview.add("Monitor")
        self.tabview.add("Settings")
        self.tabview.add("Statistics")
        
        # Build tabs
        self._build_monitor_tab()
        self._build_settings_tab()
        self._build_statistics_tab()
    
    def _build_monitor_tab(self):
        """Build monitoring control tab."""
        monitor_tab = self.tabview.tab("Monitor")
        
        # Status frame
        status_frame = ctk.CTkFrame(monitor_tab)
        status_frame.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(
            status_frame,
            text="Monitoring Status",
            font=("Helvetica", 16, "bold")
        ).pack(pady=10)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="⚪ Not Running",
            font=("Helvetica", 14)
        )
        self.status_label.pack(pady=5)
        
        # Control buttons
        button_frame = ctk.CTkFrame(monitor_tab)
        button_frame.pack(fill="x", pady=10, padx=10)
        
        self.start_btn = ctk.CTkButton(
            button_frame,
            text="▶️ Start Monitoring",
            command=self._start_monitoring,
            width=200,
            height=50,
            font=("Helvetica", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_btn.pack(side="left", padx=10, pady=10)
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Stop Monitoring",
            command=self._stop_monitoring,
            width=200,
            height=50,
            font=("Helvetica", 14, "bold"),
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10, pady=10)
        
        # Info frame
        info_frame = ctk.CTkFrame(monitor_tab)
        info_frame.pack(fill="both", expand=True, pady=10, padx=10)
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Information",
            font=("Helvetica", 16, "bold")
        ).pack(pady=10)
        
        info_text = """
• Click "Start Monitoring" to begin
• The app checks for new posts every 10 minutes
• You'll get approval requests in Telegram
• Reply with /repost, /redo, or /skip
• Keep this window open while monitoring
        """
        
        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=("Helvetica", 12),
            justify="left"
        ).pack(pady=10, padx=20)
    
    def _build_settings_tab(self):
        """Build settings configuration tab."""
        settings_tab = self.tabview.tab("Settings")
        
        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(settings_tab)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # LinkedIn Settings
        self._add_settings_section(
            scroll_frame,
            "🔗 LinkedIn Settings",
            [
                ("Username/Email:", "linkedin.username", False),
                ("Password:", "linkedin.password_encrypted", True),
                ("Company Page URL:", "linkedin.company_page_url", False),
                ("Profile URL:", "linkedin.profile_url", False)
            ]
        )
        
        # Telegram Settings
        self._add_settings_section(
            scroll_frame,
            "📱 Telegram Settings",
            [
                ("Bot Token:", "telegram.bot_token_encrypted", True),
                ("Chat ID:", "telegram.chat_id", False)
            ]
        )
        
        # OpenAI Settings
        self._add_settings_section(
            scroll_frame,
            "🤖 OpenAI Settings",
            [
                ("API Key:", "openai.api_key_encrypted", True),
                ("Model:", "openai.model", False)
            ]
        )
        
        # AI Prompt Template (Special multi-line field)
        self._add_prompt_template_section(scroll_frame)
        
        # Workflow Settings
        self._add_settings_section(
            scroll_frame,
            "⚙️ Workflow Settings",
            [
                ("Polling Frequency (minutes):", "workflow.polling_frequency_minutes", False),
                ("Posts Per Check:", "workflow.posts_per_check", False),
                ("Posts Lookback Limit:", "workflow.posts_lookback", False)
            ]
        )
        
        # Save button
        save_btn = ctk.CTkButton(
            scroll_frame,
            text="💾 Save Settings",
            command=self._save_settings,
            width=200,
            height=40,
            font=("Helvetica", 14, "bold")
        )
        save_btn.pack(pady=20)
    
    def _add_settings_section(self, parent, title: str, fields: list):
        """Add a settings section with fields."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=("Helvetica", 14, "bold")
        ).pack(pady=10)
        
        for label_text, config_key, is_password in fields:
            field_frame = ctk.CTkFrame(section_frame)
            field_frame.pack(fill="x", pady=5, padx=10)
            
            ctk.CTkLabel(
                field_frame,
                text=label_text,
                width=150,
                anchor="w"
            ).pack(side="left", padx=5)
            
            entry = ctk.CTkEntry(
                field_frame,
                width=400,
                show="*" if is_password else None
            )
            entry.pack(side="left", padx=5)
            
            # Store reference
            if not hasattr(self, 'setting_entries'):
                self.setting_entries = {}
            self.setting_entries[config_key] = (entry, is_password)
            
            # Load current value
            if self.config and self.is_unlocked:
                current_value = self.config.get(config_key, decrypt=is_password)
                if current_value:
                    entry.insert(0, current_value)
    
    def _add_prompt_template_section(self, parent):
        """Add AI prompt template section with multi-line textbox."""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(
            section_frame,
            text="✍️ AI Prompt Template",
            font=("Helvetica", 14, "bold")
        ).pack(pady=10)
        
        # Info label
        info_label = ctk.CTkLabel(
            section_frame,
            text="Use [Text] placeholder for the original post content. If missing, it will be added automatically at the end.",
            font=("Helvetica", 10),
            text_color="gray"
        )
        info_label.pack(pady=5, padx=10)
        
        # Multi-line textbox for prompt template
        prompt_textbox = ctk.CTkTextbox(
            section_frame,
            width=580,
            height=120,
            font=("Courier", 11)
        )
        prompt_textbox.pack(pady=10, padx=10)
        
        # Store reference
        if not hasattr(self, 'setting_entries'):
            self.setting_entries = {}
        self.setting_entries["openai.system_prompt"] = (prompt_textbox, False, True)  # Third param indicates textbox
        
        # Load current value
        if self.config and self.is_unlocked:
            current_value = self.config.get("openai.system_prompt", decrypt=False)
            if current_value:
                prompt_textbox.insert("1.0", current_value)
    
    def _build_statistics_tab(self):
        """Build statistics display tab."""
        stats_tab = self.tabview.tab("Statistics")
        
        ctk.CTkLabel(
            stats_tab,
            text="📊 Statistics",
            font=("Helvetica", 16, "bold")
        ).pack(pady=10)
        
        # Stats text area
        self.stats_text = ctk.CTkTextbox(stats_tab, font=("Courier", 12))
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            stats_tab,
            text="🔄 Refresh",
            command=self._refresh_statistics,
            width=150
        )
        refresh_btn.pack(pady=10)
    
    def _show_unlock_page(self):
        """Show the unlock page."""
        self.main_content.pack_forget()
        self.unlock_frame.pack(fill="both", expand=True)
    
    def _show_main_page(self):
        """Show the main application page."""
        self.unlock_frame.pack_forget()
        self.main_content.pack(fill="both", expand=True)
    
    def _unlock(self):
        """Unlock the application with passphrase."""
        passphrase = self.passphrase_entry.get()
        
        if not passphrase:
            self.unlock_status.configure(text="❌ Please enter a passphrase")
            return
        
        try:
            # Create/load config
            self.config = ConfigManager()
            
            # Try to unlock
            if self.config.unlock(passphrase):
                self.is_unlocked = True
                self.unlock_status.configure(text="✅ Unlocked!", text_color="green")
                
                # Initialize monitor
                self.monitor = LinkedInMonitor(self.config)
                
                # Start event loop
                self._start_event_loop()
                
                # Load settings
                self._load_settings()
                
                # Show main page
                self.root.after(500, self._show_main_page)
                
                logger.info("✅ Application unlocked")
            else:
                self.unlock_status.configure(text="❌ Invalid passphrase")
        
        except Exception as e:
            self.unlock_status.configure(text=f"❌ Error: {e}")
            logger.error(f"Unlock error: {e}")
    
    def _load_settings(self):
        """Load settings into entry fields."""
        if not self.config or not self.is_unlocked:
            return
        
        for config_key, entry_data in self.setting_entries.items():
            # Check if it's a textbox (3 elements) or entry (2 elements)
            if len(entry_data) == 3:
                entry, is_password, is_textbox = entry_data
            else:
                entry, is_password = entry_data
                is_textbox = False
            
            value = self.config.get(config_key, decrypt=is_password)
            if value:
                if is_textbox:
                    entry.delete("1.0", "end")
                    entry.insert("1.0", value)
                else:
                    entry.delete(0, "end")
                    entry.insert(0, value)
    
    def _save_settings(self):
        """Save settings from entry fields."""
        if not self.config or not self.is_unlocked:
            messagebox.showerror("Error", "Configuration not unlocked")
            return
        
        try:
            for config_key, entry_data in self.setting_entries.items():
                # Check if it's a textbox (3 elements) or entry (2 elements)
                if len(entry_data) == 3:
                    entry, is_password, is_textbox = entry_data
                else:
                    entry, is_password = entry_data
                    is_textbox = False
                
                # Get value based on widget type
                if is_textbox:
                    value = entry.get("1.0", "end-1c").strip()
                    # Ensure [Text] placeholder is present
                    if value and "[Text]" not in value:
                        value = value + "\n\n[Text]"
                else:
                    value = entry.get()
                
                if value:
                    # Convert numeric fields to integers
                    if config_key in ["workflow.polling_frequency_minutes", "workflow.posts_per_check", "workflow.posts_lookback"]:
                        try:
                            value = int(value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {config_key}: {value}, using as string")
                    
                    self.config.set(config_key, value, encrypt=is_password)
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            logger.info("✅ Settings saved")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            logger.error(f"Failed to save settings: {e}")
    
    def _start_event_loop(self):
        """Start async event loop in separate thread."""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        logger.info("✅ Event loop started")
    
    def _start_monitoring(self):
        """Start monitoring."""
        if not self.monitor:
            messagebox.showerror("Error", "Monitor not initialized")
            return
        
        if not self.config.is_configured():
            messagebox.showerror("Error", "Please configure all settings first")
            return
        
        # Start monitoring in event loop
        asyncio.run_coroutine_threadsafe(
            self.monitor.start_monitoring(immediate_fetch=True),
            self.loop
        )
        
        # Update UI
        self.status_label.configure(text="🟢 Running")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        logger.info("✅ Monitoring started from GUI")
    
    def _stop_monitoring(self):
        """Stop monitoring."""
        if not self.monitor:
            return
        
        # Stop monitoring in event loop
        asyncio.run_coroutine_threadsafe(
            self.monitor.stop_monitoring(),
            self.loop
        )
        
        # Update UI
        self.status_label.configure(text="⚪ Not Running")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        logger.info("✅ Monitoring stopped from GUI")
    
    def _refresh_statistics(self):
        """Refresh statistics display."""
        if not self.monitor:
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("1.0", "Monitor not initialized")
            return
        
        stats = self.monitor.get_statistics()
        
        stats_text = f"""
╔══════════════════════════════════╗
║      MONITORING STATISTICS       ║
╚══════════════════════════════════╝

Status: {'🟢 Running' if stats['is_running'] else '⚪ Not Running'}

Posts Found: {stats['posts_found']}
Posts Approved: {stats['posts_approved']}
Posts Skipped: {stats['posts_skipped']}
Posts Posted: {stats['posts_posted']}
Errors: {stats['errors']}

DATABASE STATISTICS:
Total Posts: {stats['database'].get('total', 0)}
Pending Approval: {stats['database'].get('pending_approval', 0)}
Successfully Posted: {stats['database'].get('posted', 0)}
Skipped: {stats['database'].get('skipped', 0)}
Failed: {stats['database'].get('failed', 0)}
        """
        
        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", stats_text)
    
    def _on_closing(self):
        """Handle window close event."""
        if self.monitor and self.monitor.is_running:
            if messagebox.askyesno("Quit", "Monitoring is running. Stop and quit?"):
                self._stop_monitoring()
                self.root.after(1000, self._cleanup_and_quit)
        else:
            self._cleanup_and_quit()
    
    def _cleanup_and_quit(self):
        """Cleanup and quit application."""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        self.root.destroy()
        logger.info("✅ Application closed")
    
    def run(self):
        """Run the GUI application."""
        logger.info("🚀 Starting LinkedIn Post Monitor GUI")
        self.root.mainloop()


if __name__ == "__main__":
    app = LinkedInMonitorGUI()
    app.run()
