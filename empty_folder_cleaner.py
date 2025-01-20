"""
Empty Folder Cleaner
Copyright © 2025 William Edwards. All rights reserved.
Version 1.1

This program is protected by copyright law and international treaties.
Unauthorized reproduction or distribution of this program, or any portion of it,
may result in severe civil and criminal penalties.
"""

import os
import threading
import customtkinter as ctk
import json
from tkinter import filedialog, messagebox
from pathlib import Path
from functools import lru_cache


class EmptyFolderCleaner(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Set theme and color
        saved_theme = self.load_theme_preference()
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("dark-blue")

        self.title("Empty Folder Cleaner")

        # Calculate window position
        root_w = 1200
        root_h = 800
        x = (self.winfo_screenwidth() / 2) - (root_w / 2)
        y = (self.winfo_screenheight() / 2) - (root_h / 2)
        self.geometry('%dx%d+%d+%d' % (root_w, root_h, x, y))

        # Selected path variable
        self.selected_path = ctk.StringVar()
        self.empty_folders = []
        self.folder_vars = []
        self.selected_count = ctk.StringVar()
        self.selected_count.set("Selected folders: 0")
        self.scanning = False
        self.status_message = ctk.StringVar(value="Ready")

        # Create and pack widgets
        self.create_widgets()

    def create_widgets(self):
        # Path selection frame
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(pady=10, padx=10, fill='x')

        browse_btn = ctk.CTkButton(path_frame, text="Browse", command=self.browse_folder)
        browse_btn.pack(side='left', padx=(0, 5))

        path_label = ctk.CTkLabel(path_frame, textvariable=self.selected_path, width=400, anchor='w')
        path_label.pack(side='left', padx=(0, 5), fill='x', expand=True)

        theme_btn = ctk.CTkButton(path_frame, text="Toggle Theme",
                                  command=self.toggle_theme,
                                  width=100)
        theme_btn.pack(side='right', padx=5)

        # Depth selector frame
        depth_frame = ctk.CTkFrame(self)
        depth_frame.pack(pady=5)

        ctk.CTkLabel(depth_frame, text="Max Folder Depth:").pack(side='left', padx=5)
        self.depth_var = ctk.StringVar(value="unlimited")
        depth_menu = ctk.CTkOptionMenu(depth_frame,
                                       values=["unlimited", "1", "2", "3", "4", "5"],
                                       variable=self.depth_var)
        depth_menu.pack(side='left', padx=5)

        # Button frame
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=5)

        # Preview button
        self.preview_btn = ctk.CTkButton(button_frame, text="Preview Empty Folders",
                                         command=self.start_preview)
        self.preview_btn.pack(side='left', padx=5)

        # Cancel button
        self.cancel_btn = ctk.CTkButton(button_frame, text="Cancel Scan",
                                        command=self.cancel_scan,
                                        state='disabled')
        self.cancel_btn.pack(side='left', padx=5)

        # Progress bar (hidden initially)
        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_message)
        self.status_label.pack(pady=5)

        # Create Treeview frame
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(pady=5, padx=10, fill='both', expand=True)

        # Create scrollable frame for results
        self.tree = ctk.CTkScrollableFrame(self.tree_frame)
        self.tree.pack(fill='both', expand=True)

        # Status bar
        self.status_bar = ctk.CTkLabel(self, textvariable=self.selected_count, anchor='w')
        self.status_bar.pack(side='bottom', fill='x', padx=5, pady=5)

        # Execute button
        self.execute_btn = ctk.CTkButton(self, text="Execute Cleanup",
                                         command=self.remove_selected_folders,
                                         state='disabled')
        self.execute_btn.pack(pady=10)

        # Create columns for the scrollable frame
        self.create_header()

        # Add copyright label at bottom
        copyright_label = ctk.CTkLabel(self, text="© 2024 All rights reserved.")
        copyright_label.pack(side='bottom', pady=5)

    def create_header(self):
        header_frame = ctk.CTkFrame(self.tree)
        header_frame.pack(fill='x', padx=5, pady=5)

        ctk.CTkLabel(header_frame, text="Path", width=600).pack(side='left', padx=5)
        ctk.CTkLabel(header_frame, text="Selected", width=80).pack(side='left', padx=5)

    def toggle_theme(self):
        current_theme = ctk.get_appearance_mode()
        new_theme = "Light" if current_theme == "Dark" else "Dark"
        ctk.set_appearance_mode(new_theme)
        self.save_theme_preference(new_theme)

    @lru_cache(maxsize=1000)
    def is_empty_folder(self, path):
        try:
            with threading.Lock():
                return not any(Path(path).iterdir())
        except (PermissionError, OSError):
            return False

    def start_preview(self):
        if not self.selected_path.get():
            messagebox.showwarning("Warning", "Please select a folder first!")
            return

        self.clear_tree()
        self.scanning = True

        # Update UI state
        self.preview_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.execute_btn.configure(state='disabled')
        self.progress.pack(pady=5)
        self.progress.start()
        self.status_message.set("Starting scan...")

        # Start background scan
        self.scan_thread = threading.Thread(target=self.run_scan_process)
        self.scan_thread.daemon = True
        self.scan_thread.start()

        # Schedule progress checks
        self.after(100, self.check_scan_progress)

    def run_scan_process(self):
        try:
            self.scan_results = self.scan_folders()
        finally:
            self.scanning = False

    def check_scan_progress(self):
        if self.scanning:
            self.after(100, self.check_scan_progress)
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.preview_btn.configure(state='normal')
            self.cancel_btn.configure(state='disabled')

            if hasattr(self, 'scan_results'):
                for folder in self.scan_results:
                    self.add_folder_row(folder)
                if self.scan_results:
                    self.execute_btn.configure(state='normal')
                else:
                    messagebox.showinfo("Result", "No empty folders found!")
                self.update_selected_count()
                delattr(self, 'scan_results')

    def scan_folders(self):
        empty_folders = []
        batch_size = 50
        batch = []
        max_depth = self.depth_var.get()
        folders_checked = 0

        try:
            max_depth = int(max_depth)
        except ValueError:
            max_depth = float('inf')

        for root, dirs, files in os.walk(self.selected_path.get(), topdown=True):
            if not self.scanning:
                break

            current_depth = root[len(self.selected_path.get()):].count(os.sep)
            if current_depth >= max_depth:
                dirs.clear()
                continue

            for dir_name in dirs:
                if not self.scanning:
                    break

                folders_checked += 1
                if folders_checked % 10 == 0:
                    self.status_message.set(f"Scanning... Checked {folders_checked} folders")

                dir_path = Path(root) / dir_name
                if self.is_empty_folder(dir_path):
                    batch.append(dir_path)
                    if len(batch) >= batch_size:
                        empty_folders.extend(batch)
                        batch = []

        if batch:
            empty_folders.extend(batch)

        self.status_message.set(f"Scan complete. Found {len(empty_folders)} empty folders")
        return empty_folders

    def cancel_scan(self):
        self.scanning = False
        self.status_message.set("Scan cancelled")
        self.cancel_btn.configure(state='disabled')
        self.preview_btn.configure(state='normal')

    def add_folder_row(self, folder_path):
        row_frame = ctk.CTkFrame(self.tree)
        row_frame.pack(fill='x', padx=5, pady=2)

        # Create label with double-click binding
        path_label = ctk.CTkLabel(row_frame, text=str(folder_path), width=600, anchor='w', cursor="hand2")
        path_label.pack(side='left', padx=5)
        path_label.bind('<Double-Button-1>', lambda e: self.open_folder(folder_path))

        checkbox_var = ctk.BooleanVar(value=True)
        self.folder_vars.append((folder_path, checkbox_var))
        ctk.CTkCheckBox(row_frame, text="", variable=checkbox_var, command=self.update_selected_count).pack(side='left',
                                                                                                            padx=5)

    def open_folder(self, folder_path):
        # Open folder in system file explorer
        os.startfile(str(folder_path))

    def clear_tree(self):
        for widget in self.tree.winfo_children():
            if widget != self.tree.winfo_children()[0]:
                widget.destroy()
        self.folder_vars.clear()

    def update_selected_count(self):
        selected_count = sum(1 for _, var in self.folder_vars if var.get())
        self.selected_count.set(f"Selected folders: {selected_count}")

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.selected_path.set(folder_path)
            self.execute_btn.configure(state='disabled')
            self.clear_tree()
            self.empty_folders = []
            self.update_selected_count()

    def remove_selected_folders(self):
        removed_count = 0
        for folder_path, var in self.folder_vars:
            if var.get():
                try:
                    folder_path.rmdir()
                    removed_count += 1
                except (PermissionError, OSError):
                    continue

        messagebox.showinfo("Complete", f"Cleanup finished!\nRemoved {removed_count} empty folders.")
        self.start_preview()

    def load_theme_preference(self):
        try:
            with open('theme_preference.json', 'r') as f:
                preferences = json.load(f)
                return preferences.get('theme', 'Dark')
        except FileNotFoundError:
            return 'Dark'

    def save_theme_preference(self, theme):
        with open('theme_preference.json', 'w') as f:
            json.dump({'theme': theme}, f)


if __name__ == "__main__":
    app = EmptyFolderCleaner()
    app.mainloop()
