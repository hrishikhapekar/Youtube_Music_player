import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yt_dlp
import os
import pygame
from PIL import Image, ImageTk, ImageDraw
import requests
import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import time

pygame.mixer.quit()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

class MusicPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT-DLP Music Player")
        self.geometry("500x800")

        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

        self.is_dark_mode = False
        self.colors = {
            True: {'bg': '#1e1e1e', 'fg': 'white', 'listbox_bg': '#2e2e2e', 'select_bg': '#444'},
            False: {'bg': 'white', 'fg': 'black', 'listbox_bg': 'white', 'select_bg': '#ddd'}
        }

        self.playlist = []
        self.current_index = -1
        self.paused = False
        self.duration = 0

        icon_dir = os.path.join(os.path.dirname(__file__), "icons")
        self.icons = {
            'play': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "play.png"))),
            'pause': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "pause.png"))),
            'next': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "next.png"))),
            'prev': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "prev.png"))),
            'stop': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "stop.png"))),
            'volume': ImageTk.PhotoImage(Image.open(os.path.join(icon_dir, "volume.png")))
        }
        self.placeholder_img = Image.open(os.path.join(icon_dir, "placeholder.jpg")).resize((200, 200))

        self.init_ui()
        self.apply_theme()
        self.update_timer()

    def init_ui(self):
        self.toggle_btn = tk.Button(self, text="Toggle Dark Mode", command=self.toggle_theme)
        self.toggle_btn.pack(pady=5)

        self.album_canvas = tk.Canvas(self, width=200, height=200, highlightthickness=0)
        self.album_canvas.pack(pady=5)
        self.album_img = None

        self.timer_label = tk.Label(self, text="00:00 / 00:00")
        self.timer_label.pack(pady=5)

        self.controls = tk.Frame(self)
        self.controls.pack(pady=10)
        tk.Button(self.controls, image=self.icons['prev'], command=self.play_prev, bd=0).pack(side=tk.LEFT, padx=10)
        self.play_btn = tk.Button(self.controls, image=self.icons['play'], command=self.toggle_play, bd=0)
        self.play_btn.pack(side=tk.LEFT, padx=10)
        tk.Button(self.controls, image=self.icons['next'], command=self.play_next, bd=0).pack(side=tk.LEFT, padx=10)

        self.volume_frame = tk.Frame(self)
        self.volume_frame.pack(pady=5)
        tk.Label(self.volume_frame, image=self.icons['volume']).pack(side=tk.LEFT, padx=5)
        self.volume = tk.DoubleVar(value=50)
        self.volume_slider = tk.Scale(self.volume_frame, variable=self.volume, from_=0, to=100, resolution=1,
                                      orient=tk.HORIZONTAL, command=self.set_volume, length=150)
        self.volume_slider.pack(side=tk.LEFT)
        pygame.mixer.music.set_volume(self.volume.get())

        self.search_frame = tk.Frame(self)
        self.search_frame.pack(pady=10)
        self.search_var = tk.StringVar()
        tk.Entry(self.search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        tk.Button(self.search_frame, text="Search & Download", command=self.start_download).pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(self, orient='horizontal', length=400, mode='determinate')
        self.progress.pack(pady=10)

        self.playlist_controls = tk.Frame(self)
        self.playlist_controls.pack(pady=5)
        tk.Button(self.playlist_controls, text="Refresh Playlist", command=self.refresh_playlist).pack()

        self.listbox = tk.Listbox(self, width=60)
        self.listbox.pack(pady=10)
        self.listbox.bind('<Double-1>', self.play_selected)

    def apply_theme(self):
        c = self.colors[self.is_dark_mode]
        self.configure(bg=c['bg'])
        for widget in [
            self.toggle_btn, self.search_frame, self.playlist_controls, self.listbox, self.album_canvas,
            self.timer_label, self.volume_frame, self.controls
        ]:
            widget.configure(bg=c['bg'])
        self.listbox.configure(bg=c['listbox_bg'], fg=c['fg'], selectbackground=c['select_bg'])
        self.timer_label.configure(fg=c['fg'])
        self.volume_slider.configure(bg=c['bg'], fg=c['fg'])

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def start_download(self):
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Input needed", "Please enter a search term or URL.")
            return
        threading.Thread(target=self.download_song, args=(query,), daemon=True).start()

    def download_song(self, query):
        outtmpl_path = os.path.join(self.download_dir, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'outtmpl': outtmpl_path,
            'progress_hooks': [self.hook],
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                entry = info['entries'][0]
                title = entry['title']
                thumbnail_url = entry.get('thumbnail')
                filename = os.path.join(self.download_dir, f"{title}.mp3")

                if thumbnail_url:
                    try:
                        img_data = requests.get(thumbnail_url, timeout=10).content
                        audio = MP3(filename, ID3=ID3)
                        try:
                            audio.add_tags()
                        except:
                            pass
                        audio.tags.add(
                            APIC(
                                encoding=3, mime='image/jpeg',
                                type=3, desc=u'Cover',
                                data=img_data
                            )
                        )
                        audio.save()
                    except Exception as e:
                        print(f"Embedding thumbnail failed: {e}")

                self.playlist.append({'path': filename, 'thumbnail': thumbnail_url})
                self.listbox.insert(tk.END, os.path.basename(filename))
        except Exception as e:
            messagebox.showerror("Download error", str(e))

    def refresh_playlist(self):
        self.listbox.delete(0, tk.END)
        self.playlist.clear()
        for file in os.listdir(self.download_dir):
            if file.endswith(".mp3"):
                path = os.path.join(self.download_dir, file)
                self.playlist.append({'path': path, 'thumbnail': None})
                self.listbox.insert(tk.END, file)

    def hook(self, d):
        if d['status'] == 'downloading' and d.get('total_bytes'):
            percent = d['downloaded_bytes'] / d['total_bytes'] * 100
            self.progress['value'] = percent
        elif d['status'] == 'finished':
            self.progress['value'] = 0

    def play_selected(self, event=None):
        idx = self.listbox.curselection()
        if idx:
            self.current_index = idx[0]
            self.load_song()
            self.play_song()

    def load_song(self):
        def rounded(img, radius=30):
            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, img.size[0], img.size[1]), radius=radius, fill=255)
            img.putalpha(mask)
            return img.convert('RGBA')

        song = self.playlist[self.current_index]
        if not os.path.exists(song['path']):
            messagebox.showerror("File not found", f"The file '{song['path']}' does not exist.")
            return

        pygame.mixer.music.load(song['path'])
        self.album_canvas.delete("all")
        self.album_img = None
        self.duration = 0
        img_loaded = False

        try:
            audio = MP3(song['path'])
            self.duration = int(audio.info.length)
            id3 = ID3(song['path'])
            for tag in id3.values():
                if tag.FrameID == 'APIC':
                    img_data = tag.data
                    pil_img = Image.open(io.BytesIO(img_data)).resize((200, 200))
                    rounded_img = rounded(pil_img)
                    self.album_img = ImageTk.PhotoImage(rounded_img)
                    self.album_canvas.create_image(0, 0, anchor='nw', image=self.album_img)
                    img_loaded = True
                    break
        except Exception as e:
            print("ID3 read error:", e)

        if not img_loaded and song.get('thumbnail'):
            def fetch_album():
                try:
                    resp = requests.get(song['thumbnail'], timeout=10)
                    pil_img = Image.open(io.BytesIO(resp.content)).resize((200, 200))
                    rounded_img = rounded(pil_img)
                    self.album_img = ImageTk.PhotoImage(rounded_img)
                    self.album_canvas.create_image(0, 0, anchor='nw', image=self.album_img)
                except Exception as e:
                    print("Thumbnail fetch error:", e)
                    self.set_placeholder()
            threading.Thread(target=fetch_album, daemon=True).start()
        elif not img_loaded:
            self.set_placeholder()

    def set_placeholder(self):
        pil_img = self.placeholder_img.copy()
        rounded_img = Image.new('RGBA', pil_img.size)
        mask = Image.new('L', pil_img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, pil_img.size[0], pil_img.size[1]), radius=30, fill=255)
        rounded_img.paste(pil_img, (0, 0), mask)
        self.album_img = ImageTk.PhotoImage(rounded_img)
        self.album_canvas.create_image(0, 0, anchor='nw', image=self.album_img)

    def play_song(self):
        pygame.mixer.music.play()
        self.paused = False
        self.play_btn.config(image=self.icons['pause'])

    def toggle_play(self):
        if self.current_index == -1 and self.playlist:
            self.current_index = 0
            self.load_song()
            self.play_song()
        else:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                self.play_btn.config(image=self.icons['pause'])
            else:
                pygame.mixer.music.pause()
                self.paused = True
                self.play_btn.config(image=self.icons['play'])

    def play_next(self):
        if self.playlist:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.load_song()
            self.play_song()

    def play_prev(self):
        if self.playlist:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            self.load_song()
            self.play_song()

    def set_volume(self, val):
        pygame.mixer.music.set_volume(float(val) / 100)

    def update_timer(self):
        if pygame.mixer.music.get_busy():
            pos = pygame.mixer.music.get_pos() // 1000
            mins, secs = divmod(pos, 60)
            t_mins, t_secs = divmod(self.duration, 60)
            self.timer_label.config(text=f"{mins:02d}:{secs:02d} / {t_mins:02d}:{t_secs:02d}")
        self.after(500, self.update_timer)

if __name__ == '__main__':
    app = MusicPlayer()
    app.mainloop()
