import os
import random
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageSequence

# Optional: Try importing send2trash for true Recycle Bin deletion, fallback to os.remove if missing
try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

class DannyImageScrubber:
    def __init__(self, root):
        self.root = root
        self.root.title("Danny Image Scrubber v1.0")
        self.root.geometry("1150x750")
        self.root.configure(bg="#1e1e1e")

        # State variables
        self.playlist = []
        self.current_index = 0
        self.dir1_path = ""
        self.dir2_path = ""
        
        # GIF animation variables
        self.animating = False
        self.anim_frames = []
        self.anim_index = 0
        self.anim_job = None
        self.current_image_tk = None

        self.setup_ui()
        self.bind_keys()

    def setup_ui(self):
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=1)

        # --- LEFT SIDE: Viewing Area ---
        self.canvas_frame = tk.Frame(self.root, bg="#000000", bd=2, relief="sunken")
        self.canvas_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.image_label = tk.Label(self.canvas_frame, bg="#000000")
        self.image_label.pack(fill="both", expand=True)
        self.image_label.bind("<Configure>", self.on_resize)

        # --- RIGHT SIDE: Playlist & Controls ---
        right_panel = tk.Frame(self.root, bg="#1e1e1e")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        right_panel.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)

        # Playlist Queue Listbox
        queue_frame = tk.Frame(right_panel, bg="#1e1e1e")
        queue_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        queue_frame.rowconfigure(1, weight=1)
        queue_frame.columnconfigure(0, weight=1)

        queue_label = tk.Label(queue_frame, text="Playlist Queue", fg="#ffffff", bg="#1e1e1e", font=("Arial", 10, "bold"))
        queue_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.playlist_box = tk.Listbox(queue_frame, bg="#121212", fg="#00ffcc", selectbackground="#333333", 
                                       relief="flat", highlightthickness=0, font=("Consolas", 10))
        self.playlist_box.grid(row=1, column=0, sticky="nsew")
        self.playlist_box.bind('<<ListboxSelect>>', self.on_listbox_select)

        # Action Panel on Right (Dir 1, Dir 2, Shuffle, and Delete)
        action_frame = tk.Frame(right_panel, bg="#1e1e1e")
        action_frame.grid(row=1, column=0, sticky="ew")
        action_frame.columnconfigure(0, weight=1)

        self.btn_shuffle = tk.Button(action_frame, text="🔀 Shuffle Playlist", bg="#2a2a2a", fg="#ffffff", relief="flat", command=self.shuffle_playlist)
        self.btn_shuffle.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)

        self.btn_dir1 = tk.Button(action_frame, text="Move to Dir 1", bg="#005a9e", fg="#ffffff", relief="flat", command=lambda: self.move_file(1))
        self.btn_dir1.grid(row=1, column=0, sticky="ew", pady=2)
        
        self.entry_dir1 = tk.Entry(action_frame, bg="#2d2d2d", fg="#b0b0b0", insertbackground="white", relief="flat")
        self.entry_dir1.insert(0, "Target 1 path...")
        self.entry_dir1.grid(row=2, column=0, sticky="ew", pady=2)
        
        self.btn_set_dir1 = tk.Button(action_frame, text="Set Dir 1", bg="#333333", fg="#ffffff", relief="flat", command=lambda: self.set_directory(1))
        self.btn_set_dir1.grid(row=2, column=1, sticky="ew", pady=2, padx=(2,0))

        self.btn_dir2 = tk.Button(action_frame, text="Move to Dir 2", bg="#512b58", fg="#ffffff", relief="flat", command=lambda: self.move_file(2))
        self.btn_dir2.grid(row=3, column=0, sticky="ew", pady=2)
        
        self.entry_dir2 = tk.Entry(action_frame, bg="#2d2d2d", fg="#b0b0b0", insertbackground="white", relief="flat")
        self.entry_dir2.insert(0, "Target 2 path...")
        self.entry_dir2.grid(row=4, column=0, sticky="ew", pady=2)
        
        self.btn_set_dir2 = tk.Button(action_frame, text="Set Dir 2", bg="#333333", fg="#ffffff", relief="flat", command=lambda: self.set_directory(2))
        self.btn_set_dir2.grid(row=4, column=1, sticky="ew", pady=2, padx=(2,0))

        # Delete Button placed on the right panel underneath target directories
        self.btn_delete = tk.Button(action_frame, text="Delete (Recycle Bin) [Delete]", bg="#8b0000", fg="#ffffff", relief="flat", command=self.delete_current_file)
        self.btn_delete.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 2))

        # --- BOTTOM CONTROL BAR ---
        bottom_bar = tk.Frame(self.root, bg="#1e1e1e", height=50)
        bottom_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        bottom_bar.columnconfigure(3, weight=1)

        self.btn_add = tk.Button(bottom_bar, text="Add Folder", bg="#333333", fg="#ffffff", relief="flat", command=self.load_folder)
        self.btn_add.grid(row=0, column=0, padx=2, sticky="ew")

        self.btn_prev = tk.Button(bottom_bar, text="◄ Prev", bg="#333333", fg="#ffffff", relief="flat", command=self.prev_image)
        self.btn_prev.grid(row=0, column=1, padx=2, sticky="ew")

        self.btn_next = tk.Button(bottom_bar, text="Next ►", bg="#333333", fg="#ffffff", relief="flat", command=self.next_image)
        self.btn_next.grid(row=0, column=2, padx=2, sticky="ew")

    def bind_keys(self):
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Delete>", lambda e: self.delete_current_file())

    def load_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
            self.playlist = [
                os.path.normpath(os.path.join(folder_selected, f)) for f in os.listdir(folder_selected)
                if f.lower().endswith(valid_exts)
            ]
            self.playlist.sort()
            
            self.update_playlist_box()
            if self.playlist:
                self.current_index = 0
                self.load_current_media()

    def update_playlist_box(self):
        self.playlist_box.delete(0, tk.END)
        for path in self.playlist:
            self.playlist_box.insert(tk.END, os.path.basename(path))

    def load_current_media(self):
        if not self.playlist:
            self.image_label.configure(image="")
            self.current_image_tk = None
            return
        
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None
        self.animating = False

        file_path = self.playlist[self.current_index]
        
        self.playlist_box.selection_clear(0, tk.END)
        self.playlist_box.selection_set(self.current_index)
        self.playlist_box.see(self.current_index)

        if file_path.lower().endswith('.gif'):
            self.load_gif(file_path)
        else:
            self.load_static_image(file_path)

    def load_static_image(self, file_path):
        try:
            image = Image.open(file_path)
            self.display_scaled_image(image)
        except Exception as e:
            print(f"Error loading image: {e}")

    def load_gif(self, file_path):
        try:
            self.anim_frames = []
            img = Image.open(file_path)
            for frame in ImageSequence.Iterator(img):
                self.anim_frames.append(frame.copy().convert('RGBA'))
            
            self.anim_index = 0
            self.animating = True
            self.animate_gif()
        except Exception as e:
            print(f"Error loading GIF: {e}")

    def animate_gif(self):
        if not self.animating or not self.anim_frames:
            return
        
        frame = self.anim_frames[self.anim_index]
        self.display_scaled_image(frame)
        
        self.anim_index = (self.anim_index + 1) % len(self.anim_frames)
        self.anim_job = self.root.after(100, self.animate_gif)

    def display_scaled_image(self, pil_image):
        c_width = self.image_label.winfo_width()
        c_height = self.image_label.winfo_height()

        if c_width < 10 or c_height < 10:
            c_width, c_height = 600, 600

        img_width, img_height = pil_image.size
        ratio = min(c_width / img_width, c_height / img_height)
        new_width = max(1, int(img_width * ratio))
        new_height = max(1, int(img_height * ratio))

        resized_img = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.current_image_tk = ImageTk.PhotoImage(resized_img)
        self.image_label.configure(image=self.current_image_tk)

    def on_resize(self, event):
        if self.playlist and not self.animating:
            self.load_current_media()

    def next_image(self):
        if self.playlist:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.load_current_media()

    def prev_image(self):
        if self.playlist:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            self.load_current_media()

    def on_listbox_select(self, event):
        selection = self.playlist_box.curselection()
        if selection:
            self.current_index = selection[0]
            self.load_current_media()

    def shuffle_playlist(self):
        if len(self.playlist) > 1:
            current_file = self.playlist[self.current_index]
            random.shuffle(self.playlist)
            self.current_index = self.playlist.index(current_file)
            self.update_playlist_box()
            self.load_current_media()

    def set_directory(self, target_num):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            if target_num == 1:
                self.dir1_path = os.path.normpath(folder_selected)
                self.entry_dir1.delete(0, tk.END)
                self.entry_dir1.insert(0, folder_selected)
            elif target_num == 2:
                self.dir2_path = os.path.normpath(folder_selected)
                self.entry_dir2.delete(0, tk.END)
                self.entry_dir2.insert(0, folder_selected)

    def get_unique_destination(self, target_dir, file_path):
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        counter = 1
        destination = os.path.join(target_dir, base_name)
        
        while os.path.exists(destination):
            destination = os.path.join(target_dir, f"{name} ({counter}){ext}")
            counter += 1
        return os.path.normpath(destination)

    def move_file(self, target_num):
        if not self.playlist:
            return
        
        target_dir = self.dir1_path if target_num == 1 else self.dir2_path
        if not target_dir or not os.path.exists(target_dir):
            messagebox.showwarning("Warning", f"Target Directory {target_num} is not set or invalid!")
            return

        file_path = os.path.normpath(self.playlist[self.current_index])
        destination = self.get_unique_destination(target_dir, file_path)

        try:
            if self.anim_job:
                self.root.after_cancel(self.anim_job)
                self.anim_job = None
            self.animating = False

            shutil.move(file_path, destination)
            
            self.playlist.pop(self.current_index)
            self.update_playlist_box()
            
            if self.playlist:
                if self.current_index >= len(self.playlist):
                    self.current_index = len(self.playlist) - 1
                self.load_current_media()
            else:
                self.image_label.configure(image="")
                self.current_image_tk = None
                messagebox.showinfo("Info", "Playlist is now empty.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")

    def delete_current_file(self):
        if not self.playlist:
            return

        file_path = os.path.normpath(self.playlist[self.current_index])
        try:
            if self.anim_job:
                self.root.after_cancel(self.anim_job)
                self.anim_job = None
            self.animating = False

            if HAS_SEND2TRASH:
                try:
                    send2trash.send2trash(file_path)
                except Exception:
                    # Fallback to standard removal if send2trash hits a OneDrive long-path quirk
                    os.remove(file_path)
            else:
                os.remove(file_path)

            self.playlist.pop(self.current_index)
            self.update_playlist_box()

            if self.playlist:
                if self.current_index >= len(self.playlist):
                    self.current_index = len(self.playlist) - 1
                self.load_current_media()
            else:
                self.image_label.configure(image="")
                self.current_image_tk = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DannyImageScrubber(root)
    root.mainloop()