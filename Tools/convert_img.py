import os
import re
import tkinter as tk
from tkinter import filedialog, simpledialog, colorchooser, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import (
    Image, ImageTk, ImageEnhance, ImageDraw, ImageFont,
    ImageOps, ExifTags
)
from datetime import datetime

GIF_THRESHOLD = 5.0  # seconds

class Layer:
    def __init__(self, pil_img, x, y, path):
        self.orig = pil_img.convert("RGBA")
        self.img = self.orig.copy()
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.x = x
        self.y = y
        self.scale = 1.0
        self.id = None
        self.path = path
        self.taken_time = self._get_timestamp(path)

    def _get_timestamp(self, path):
        try:
            exif = self.orig._getexif() or {}
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == "DateTimeOriginal":
                    dt = datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                    return dt.timestamp()
        except Exception:
            pass
        return os.path.getmtime(path)

    def update_canvas(self, canvas):
        w = int(self.orig.width * self.scale)
        h = int(self.orig.height * self.scale)
        self.img = self.orig.resize((w, h), Image.LANCZOS)
        self.tkimg = ImageTk.PhotoImage(self.img)
        if self.id:
            canvas.delete(self.id)
        self.id = canvas.create_image(self.x, self.y, image=self.tkimg, anchor="nw")

    def contains(self, px, py):
        if not self.id:
            return False
        w, h = self.img.size
        return self.x <= px <= self.x + w and self.y <= py <= self.y + h


class MiniImageEditor(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mini Image Editor")
        self.configure(bg="#2e2e2e")
        self.layers = []
        self.selected = None
        self.drag_offset = (0, 0)
        self.crop_start = None
        self.crop_rect = None

        # Toolbar
        toolbar = tk.Frame(self, bg="#2e2e2e")
        toolbar.pack(fill="x", pady=2)
        ops = [
            ("New Canvas", self.new_canvas),
            ("Open Image", self.open_image),
            ("Resize", self.resize_layer),
            ("Crop", self.crop_layer),
            ("Brightness", self.brightness_layer),
            ("Negative", self.negative_layer),
            ("Add Text", self.add_text),
            ("Save As...", self.save_image)
        ]
        for txt, cmd in ops:
            btn = tk.Button(toolbar, text=txt, command=cmd,
                            bg="#444444", fg="#ffffff", relief="flat",
                            activebackground="#555555", padx=6, pady=4)
            btn.pack(side="left", padx=2)

        # Canvas
        self.canvas = tk.Canvas(self, bg="#333333", cursor="arrow")
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind("<<Drop>>", self.on_drop)
        self.new_canvas()

        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def new_canvas(self):
        w = simpledialog.askinteger("Canvas Width", "Width (px):", initialvalue=800)
        h = simpledialog.askinteger("Canvas Height", "Height (px):", initialvalue=600)
        if not w or not h:
            return
        self.canvas.config(width=w, height=h)
        self.layers.clear()
        self.canvas.delete("all")
        self.selected = None

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff")]
        )
        if path:
            self._add_layer(path)

    def on_drop(self, event):
        # parse {path} or plain path strings
        data = event.data
        paths = re.findall(r'\{([^}]+)\}', data) or data.split()
        for p in paths:
            p = p.strip()
            if os.path.isfile(p):
                self._add_layer(p)

    def _add_layer(self, path):
        try:
            pil = Image.open(path)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open {path}\n{e}")
            return
        layer = Layer(pil, x=10, y=10, path=path)
        layer.update_canvas(self.canvas)
        self.layers.append(layer)
        self.select_layer(layer)
        if len(self.layers) >= 2 and self._check_gif():
            self._make_gif()

    def select_layer(self, layer):
        self.selected = layer
        self.layers.remove(layer)
        self.layers.append(layer)
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        for layer in self.layers:
            layer.update_canvas(self.canvas)
        if self.selected:
            x, y = self.selected.x, self.selected.y
            w, h = self.selected.img.size
            self.canvas.create_rectangle(x, y, x+w, y+h,
                                         outline="#00ffff", width=2)

    def on_click(self, e):
        if self.crop_start:
            return
        for layer in reversed(self.layers):
            if layer.contains(e.x, e.y):
                self.select_layer(layer)
                dx = e.x - layer.x
                dy = e.y - layer.y
                self.drag_offset = (dx, dy)
                return
        self.selected = None
        self.redraw()

    def on_drag(self, e):
        if self.crop_start and self.selected:
            x0, y0 = self.crop_start
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
            self.crop_rect = self.canvas.create_rectangle(
                x0, y0, e.x, e.y,
                outline="#ffff00", dash=(4,2)
            )
        elif self.selected:
            dx, dy = self.drag_offset
            self.selected.x = e.x - dx
            self.selected.y = e.y - dy
            self.redraw()

    def on_release(self, e):
        if self.crop_start and self.selected:
            x0, y0 = self.crop_start
            x1, y1 = e.x, e.y
            lx, ly = self.selected.x, self.selected.y
            rel0 = (max(0, x0-lx), max(0, y0-ly))
            rel1 = (max(0, x1-lx), max(0, y1-ly))
            bbox = (
                min(rel0[0], rel1[0]), min(rel0[1], rel1[1]),
                max(rel0[0], rel1[0]), max(rel0[1], rel1[1])
            )
            cropped = self.selected.img.crop(bbox)
            self.selected.orig = cropped
            self.selected.scale = 1.0
            self.selected.update_canvas(self.canvas)
            self.canvas.delete(self.crop_rect)
            self.crop_rect = None
            self.crop_start = None

    def resize_layer(self):
        if not self.selected:
            messagebox.showinfo("Resize", "Select a layer first")
            return
        factor = simpledialog.askfloat(
            "Resize", "Scale factor (e.g. 1.0 = 100%):",
            initialvalue=self.selected.scale
        )
        if factor and factor > 0:
            self.selected.scale = factor
            self.redraw()

    def crop_layer(self):
        if not self.selected:
            messagebox.showinfo("Crop", "Select a layer first")
            return
        messagebox.showinfo("Crop", "Click and drag to crop the selected layer")
        self.crop_start = None
        def set_start(e):
            if not self.crop_start:
                self.crop_start = (e.x, e.y)
                self.canvas.unbind("<Button-1>", bind_id)
        bind_id = self.canvas.bind("<Button-1>", set_start)

    def brightness_layer(self):
        if not self.selected:
            messagebox.showinfo("Brightness", "Select a layer first")
            return
        dlg = tk.Toplevel(self, bg="#2e2e2e")
        dlg.title("Brightness")
        dlg.configure(bg="#2e2e2e")
        tk.Label(dlg, text="Brightness (0.0–2.0)", bg="#2e2e2e", fg="#ffffff").pack(padx=10, pady=5)
        var = tk.DoubleVar(value=1.0)
        slider = tk.Scale(dlg, variable=var, from_=0.0, to=2.0,
                          resolution=0.01, orient="horizontal", length=300,
                          bg="#2e2e2e", fg="#ffffff", troughcolor="#444444", highlightthickness=0)
        slider.pack(padx=10, pady=5)
        def apply():
            enh = ImageEnhance.Brightness(self.selected.orig)
            self.selected.orig = enh.enhance(var.get())
            self.selected.scale = 1.0
            self.redraw()
            dlg.destroy()
        tk.Button(dlg, text="Apply", command=apply, bg="#444444", fg="#ffffff").pack(pady=5)

    def negative_layer(self):
        if not self.selected:
            messagebox.showinfo("Negative", "Select a layer first")
            return
        # invert RGB and preserve alpha
        rgb = self.selected.orig.convert("RGB")
        inv = ImageOps.invert(rgb)
        r, g, b = inv.split()
        alpha = self.selected.orig.split()[3]
        neg = Image.merge("RGBA", (r, g, b, alpha))
        self.selected.orig = neg
        self.selected.scale = 1.0
        self.redraw()

    def add_text(self):
        if not self.selected:
            messagebox.showinfo("Text", "Select a layer first")
            return
        txt = simpledialog.askstring("Add Text", "Enter text:")
        if not txt:
            return
        color = colorchooser.askcolor()[1] or "white"
        size = simpledialog.askinteger("Font Size", "Enter font size:", initialvalue=24)
        messagebox.showinfo("Add Text", "Click where to place text")
        def place(e):
            dx = e.x - self.selected.x
            dy = e.y - self.selected.y
            draw = ImageDraw.Draw(self.selected.orig)
            try:
                font = ImageFont.truetype("arial.ttf", size)
            except:
                font = ImageFont.load_default()
            draw.text((dx, dy), txt, fill=color, font=font)
            self.selected.scale = 1.0
            self.redraw()
            self.canvas.unbind("<Button-1>", bind_id)
        bind_id = self.canvas.bind("<Button-1>", place)

    def save_image(self):
        w = int(self.canvas["width"])
        h = int(self.canvas["height"])
        base = Image.new("RGBA", (w, h), (255,255,255,255))
        for layer in self.layers:
            base.paste(layer.img, (layer.x, layer.y), layer.img)
        types = [
            ("PNG","*.png"), ("JPEG","*.jpg;*.jpeg"),
            ("BMP","*.bmp"), ("TIFF","*.tif;*.tiff"),
            ("GIF","*.gif")
        ]
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=types)
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        out = base
        fmt = "PNG"
        if ext in (".jpg",".jpeg"):
            fmt = "JPEG"; out = base.convert("RGB")
        elif ext == ".bmp":
            fmt = "BMP"; out = base.convert("RGB")
        elif ext in (".tif",".tiff"):
            fmt = "TIFF"
        elif ext == ".gif":
            fmt = "GIF"; out = base.convert("RGB")
        out.save(path, format=fmt)
        messagebox.showinfo("Saved", f"Saved to {path}")

    def _check_gif(self):
        times = [l.taken_time for l in self.layers]
        return max(times) - min(times) <= GIF_THRESHOLD

    def _make_gif(self):
        frames = [l.orig for l in sorted(self.layers, key=lambda L: L.taken_time)]
        path = filedialog.asksaveasfilename(
            defaultextension=".gif", filetypes=[("GIF","*.gif")]
        )
        if not path:
            return
        frames[0].save(
            path, save_all=True, append_images=frames[1:],
            duration=500, loop=0
        )
        messagebox.showinfo("GIF Saved", f"Animated GIF saved at:\n{path}")


if __name__ == "__main__":
    app = MiniImageEditor()
    app.mainloop()
