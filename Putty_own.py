import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import paramiko
import threading
import time
from datetime import datetime
import re

class EnhancedSSHClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Monetx NCM Emulator")
        self.root.geometry("900x700")
        
        self.client = None
        self.shell = None
        self.connected = False
        self.command_history = []
        self.history_index = -1
        self.pagination_enabled = True  # Auto-handle pagination
        
        self.create_widgets()
    
    def create_widgets(self):
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection Settings", padding="10")
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        # Connection details
        conn_grid = ttk.Frame(conn_frame)
        conn_grid.pack(fill="x")
        
        ttk.Label(conn_grid, text="Host:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.host_entry = ttk.Entry(conn_grid, width=20)
        self.host_entry.grid(row=0, column=1, padx=5, pady=2)
        self.host_entry.insert(0, "192.168.1.1")  # Default example
        
        ttk.Label(conn_grid, text="Port:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.port_entry = ttk.Entry(conn_grid, width=10)
        self.port_entry.insert(0, "22")
        self.port_entry.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(conn_grid, text="Username:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.user_entry = ttk.Entry(conn_grid, width=20)
        self.user_entry.grid(row=1, column=1, padx=5, pady=2)
        self.user_entry.insert(0, "admin")  # Default example
        
        ttk.Label(conn_grid, text="Password:").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.pass_entry = ttk.Entry(conn_grid, width=15, show="*")
        self.pass_entry.grid(row=1, column=3, padx=5, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.connect_btn = ttk.Button(btn_frame, text="Connect", command=self.connect_ssh)
        self.connect_btn.pack(side="left", padx=5)
        
        self.disconnect_btn = ttk.Button(btn_frame, text="Disconnect", 
                                        command=self.disconnect_ssh, state="disabled")
        self.disconnect_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Save Session", command=self.save_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Load Session", command=self.load_session).pack(side="left", padx=5)
        
        # Terminal output
        term_frame = ttk.LabelFrame(self.root, text="Terminal", padding="10")
        term_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Enhanced Terminal toolbar
        term_toolbar = ttk.Frame(term_frame)
        term_toolbar.pack(fill="x", pady=(0, 5))
        
        # Left side buttons
        left_toolbar = ttk.Frame(term_toolbar)
        left_toolbar.pack(side="left")
        
        self.clear_btn = ttk.Button(left_toolbar, text="🗑️ Clear Terminal", command=self.clear_terminal)
        self.clear_btn.pack(side="left", padx=2)
        
        ttk.Button(left_toolbar, text="📋 Copy", command=self.copy_text).pack(side="left", padx=2)
        ttk.Button(left_toolbar, text="📜 Paste", command=self.paste_text).pack(side="left", padx=2)
        ttk.Button(left_toolbar, text="💾 Save Output", command=self.save_output).pack(side="left", padx=2)
        
        # Pagination controls
        pagination_frame = ttk.Frame(term_toolbar)
        pagination_frame.pack(side="left", padx=20)
        
        ttk.Label(pagination_frame, text="Pagination:").pack(side="left")
        self.pagination_var = tk.BooleanVar(value=True)
        self.pagination_cb = ttk.Checkbutton(pagination_frame, text="Auto-handle --More--", 
                                           variable=self.pagination_var,
                                           command=self.toggle_pagination)
        self.pagination_cb.pack(side="left", padx=5)
        
        self.more_btn = ttk.Button(pagination_frame, text="⏩ Send Space", 
                                 command=self.send_space, state="disabled")
        self.more_btn.pack(side="left", padx=2)
        
        # Right side status
        right_toolbar = ttk.Frame(term_toolbar)
        right_toolbar.pack(side="right")
        
        self.status_label = ttk.Label(right_toolbar, text="🔴 Disconnected", foreground="red")
        self.status_label.pack(side="right", padx=5)
        
        self.output_text = scrolledtext.ScrolledText(term_frame, height=20, width=80, 
                                                   font=("Courier New", 10))
        self.output_text.pack(fill="both", expand=True)
        self.output_text.config(state="disabled")
        
        # Command input with history
        input_frame = ttk.LabelFrame(term_frame, text="Command Input", padding="5")
        input_frame.pack(fill="x", pady=5)
        
        cmd_grid = ttk.Frame(input_frame)
        cmd_grid.pack(fill="x")
        
        ttk.Label(cmd_grid, text="Command:").grid(row=0, column=0, sticky="w")
        self.cmd_entry = ttk.Entry(cmd_grid, width=60, font=("Courier New", 10))
        self.cmd_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.cmd_entry.bind("<Return>", self.send_command)
        self.cmd_entry.bind("<Up>", self.command_history_up)
        self.cmd_entry.bind("<Down>", self.command_history_down)
        
        cmd_grid.columnconfigure(1, weight=1)
        
        btn_frame_cmd = ttk.Frame(cmd_grid)
        btn_frame_cmd.grid(row=0, column=2, padx=5)
        
        self.send_btn = ttk.Button(btn_frame_cmd, text="Send", command=self.send_command)
        self.send_btn.pack(side="left", padx=2)
        
        ttk.Button(btn_frame_cmd, text="Clear", command=self.clear_input).pack(side="left", padx=2)
        
        # Quick command buttons for common network commands
        quick_cmd_frame = ttk.LabelFrame(term_frame, text="Quick Commands", padding="5")
        quick_cmd_frame.pack(fill="x", pady=5)
        
        quick_commands = [
            ("show version", "show version"),
            ("show run", "show running-config"),
            ("show ip route", "show ip route"),
            ("show interfaces", "show interfaces"),
            ("show log", "show logging"),
            ("ping", "ping 8.8.8.8"),
            ("traceroute", "traceroute 8.8.8.8")
        ]
        
        for i, (label, cmd) in enumerate(quick_commands):
            ttk.Button(quick_cmd_frame, text=label, 
                      command=lambda c=cmd: self.quick_command(c)).grid(
                      row=i//4, column=i%4, padx=2, pady=2, sticky="ew")
            quick_cmd_frame.columnconfigure(i%4, weight=1)
    
    def toggle_pagination(self):
        """Toggle automatic pagination handling"""
        if self.pagination_var.get():
            self.more_btn.config(state="disabled")
        else:
            self.more_btn.config(state="normal")
    
    def send_space(self):
        """Send space to handle --More-- pagination"""
        if self.connected and self.shell:
            self.shell.send(' ')
            self._update_output("[SENT SPACE for pagination]\n")
    
    def quick_command(self, command):
        """Insert quick command into input field"""
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, command)
        self.cmd_entry.focus()
    
    def clear_terminal(self):
        """Clear the terminal output"""
        self.output_text.config(state="normal")
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state="disabled")
        self._update_output(f"[{datetime.now().strftime('%H:%M:%S')}] Terminal cleared\n")
    
    def copy_text(self):
        """Copy selected text to clipboard"""
        try:
            selected_text = self.output_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            messagebox.showinfo("Copy", "No text selected")
    
    def paste_text(self):
        """Paste text from clipboard to command input"""
        try:
            clipboard_text = self.root.clipboard_get()
            self.cmd_entry.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            pass
    
    def save_output(self):
        """Save terminal output to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.output_text.config(state="normal")
                content = self.output_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.output_text.config(state="disabled")
                messagebox.showinfo("Save", f"Output saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save: {e}")
    
    def save_session(self):
        """Save connection settings"""
        session_data = {
            'host': self.host_entry.get(),
            'port': self.port_entry.get(),
            'username': self.user_entry.get()
        }
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(session_data, f)
                messagebox.showinfo("Save Session", "Session saved successfully")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save session: {e}")
    
    def load_session(self):
        """Load connection settings"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    session_data = json.load(f)
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, session_data.get('host', ''))
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, session_data.get('port', '22'))
                self.user_entry.delete(0, tk.END)
                self.user_entry.insert(0, session_data.get('username', ''))
                messagebox.showinfo("Load Session", "Session loaded successfully")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load session: {e}")
    
    def clear_input(self):
        """Clear command input"""
        self.cmd_entry.delete(0, tk.END)
    
    def command_history_up(self, event):
        """Navigate command history up"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.command_history[self.history_index])
        return "break"
    
    def command_history_down(self, event):
        """Navigate command history down"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.cmd_entry.delete(0, tk.END)
            self.cmd_entry.insert(0, self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.cmd_entry.delete(0, tk.END)
        return "break"
    
    def connect_ssh(self):
        hostname = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip() or "22")
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        
        if not all([hostname, username]):
            messagebox.showerror("Error", "Hostname and username are required")
            return
        
        # Connect in separate thread
        threading.Thread(target=self._connect_thread, 
                        args=(hostname, port, username, password), 
                        daemon=True).start()
    
    def _connect_thread(self, hostname, port, username, password):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname, port, username, password)
            
            self.connected = True
            self.shell = self.client.invoke_shell()
            
            # Update UI in main thread
            self.root.after(0, self._on_connect_success)
            
            # Buffer to handle partial lines and pagination
            buffer = ""
            last_buffer = ""
            
            # Start reading output
            while self.connected and self.shell:
                if self.shell.recv_ready():
                    data = self.shell.recv(1024).decode('utf-8', errors='ignore')
                    buffer += data
                    
                    # Process complete lines
                    lines = buffer.split('\n')
                    # Keep the last incomplete line in buffer
                    buffer = lines[-1]
                    
                    for line in lines[:-1]:
                        processed_line = line.rstrip('\r')
                        
                        # Check for --More-- pattern (common in Cisco devices)
                        if self.pagination_var.get() and '--More--' in processed_line:
                            # Auto-send space to continue
                            self.shell.send(' ')
                            # Remove the --More-- from display
                            # processed_line = processed_line.replace('--More--', '[More...]')
                        
                        # Send to UI
                        self.root.after(0, self._update_output, processed_line + '\n')
                    
                    # Handle the case where we have a complete line with --More--
                    if buffer and '--More--' in buffer:
                        if self.pagination_var.get():
                            self.shell.send(' ')
                            buffer = buffer.replace('--More--', '[More...]')
                    
                    # Small delay to prevent CPU spinning
                    time.sleep(0.01)
                    
                else:
                    # Small delay when no data is available
                    time.sleep(0.1)
                    
        except Exception as e:
            self.root.after(0, self._on_connect_error, str(e))
    
    def _on_connect_success(self):
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_label.config(text="🟢 Connected", foreground="green")
        self._update_output(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to SSH server\n")
        self._update_output(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-pagination: {'ON' if self.pagination_var.get() else 'OFF'}\n")
    
    def _on_connect_error(self, error):
        messagebox.showerror("Connection Error", f"Failed to connect: {error}")
        self.status_label.config(text="🔴 Connection Failed", foreground="red")
    
    def _update_output(self, text):
        self.output_text.config(state="normal")
        self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.config(state="disabled")
    
    def send_command(self, event=None):
        if not self.connected or not self.shell:
            messagebox.showerror("Error", "Not connected to any server")
            return
        
        command = self.cmd_entry.get().strip()
        if command:
            # Add to command history
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            
            # Send command
            self.shell.send(command + '\n')
            self.cmd_entry.delete(0, "end")
    
    def disconnect_ssh(self):
        self.connected = False
        if self.shell:
            self.shell.close()
        if self.client:
            self.client.close()
        
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.more_btn.config(state="disabled")
        self.status_label.config(text="🔴 Disconnected", foreground="red")
        self._update_output(f"\n[{datetime.now().strftime('%H:%M:%S')}] Disconnected from server\n")

def main_gui():
    root = tk.Tk()
    app = EnhancedSSHClientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main_gui()