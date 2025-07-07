import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import string

def caesar_shift(text: str, shift: int, preserve: bool) -> str:
    seps = {'.', '-', '|'}
    result = []
    for ch in text:
        if ch in seps:
            # treat separators as space
            result.append(' ')
        elif ch.isupper():
            idx = (ord(ch) - ord('A') + shift) % 26
            result.append(chr(idx + ord('A')))
        elif ch.islower():
            idx = (ord(ch) - ord('a') + shift) % 26
            result.append(chr(idx + ord('a')))
        else:
            if preserve:
                result.append(ch)
    return ''.join(result)

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg_color, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.inner = tk.Frame(self.canvas, bg=bg_color)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set,
                              xscrollcommand=self.hsb.set)
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

class CaesarVisualizer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Caesar Cipher Visualizer")
        self.state('zoomed')  # start full screen

        # Three themes
        self.themes = {
            "Futuristic Dark": {
                "bg":"#111111","fg":"#00FFCC",
                "entry_bg":"#222222","entry_fg":"#00FFCC",
                "btn_bg":"#00CCFF","btn_fg":"#111111",
                "canvas_bg":"#111111","box_fill":"#222222",
                "box_outline":"#00FFCC","arrow":"#00FFCC","error":"#FF5555"
            },
            "Roman Antique Dark": {
                "bg":"#1a1204","fg":"#d4af37",
                "entry_bg":"#2b1e10","entry_fg":"#d4af37",
                "btn_bg":"#5c432b","btn_fg":"#f8e4a1",
                "canvas_bg":"#1a1204","box_fill":"#2b1e10",
                "box_outline":"#d4af37","arrow":"#d4af37","error":"#e74c3c"
            },
            "Bright": {
                "bg":"#f0f0f0","fg":"#202020",
                "entry_bg":"#ffffff","entry_fg":"#202020",
                "btn_bg":"#dddddd","btn_fg":"#202020",
                "canvas_bg":"#f0f0f0","box_fill":"#ffffff",
                "box_outline":"#202020","arrow":"#202020","error":"#ff0000"
            }
        }
        self.current_theme = tk.StringVar(value="Roman Antique Dark")
        self.colors = self.themes[self.current_theme.get()]

        # State
        self.shift = tk.StringVar(value="5")
        self.cycles = tk.IntVar(value=3)
        self.preserve = tk.BooleanVar(value=True)
        self.box_size = tk.IntVar(value=30)
        self.font_size = tk.IntVar(value=12)
        self.mode = tk.StringVar(value="animate")
        self.step_index = (0,0)
        self.precomputed = []

        # Configure UI
        self.configure(bg=self.colors["bg"])
        self.bind("<Return>", lambda e: self.encrypt())
        self.bind("<Control-z>", lambda e: self.clear_all())

        # Top controls
        top = tk.Frame(self, bg=self.colors["bg"])
        top.pack(fill="x", pady=5)

        # Theme selector
        tk.Label(top, text="Theme:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left", padx=5)
        ttk.OptionMenu(top, self.current_theme,
                       self.current_theme.get(),
                       *self.themes.keys(),
                       command=self.on_theme_change)\
            .pack(side="left", padx=5)

        # Shift input
        tk.Label(top, text="Shift:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left")
        vcmd = (self.register(self.validate_input), '%P')
        tk.Entry(top, textvariable=self.shift, width=3,
                 validate="key", validatecommand=vcmd,
                 bg=self.colors["entry_bg"], fg=self.colors["entry_fg"],
                 relief="flat")\
            .pack(side="left", padx=5)

        # Cycle count
        tk.Label(top, text="Cycles:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left")
        tk.Spinbox(top, from_=1, to=10, textvariable=self.cycles, width=3,
                   command=self.rebuild_cycles,
                   bg=self.colors["entry_bg"], fg=self.colors["entry_fg"],
                   relief="flat")\
            .pack(side="left", padx=5)

        # Preserve punctuation
        tk.Checkbutton(top, text="Preserve Punct", variable=self.preserve,
                       bg=self.colors["bg"], fg=self.colors["fg"],
                       selectcolor=self.colors["bg"])\
            .pack(side="left", padx=5)

        # Box & font size
        tk.Label(top, text="Box:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left")
        tk.Spinbox(top, from_=10, to=60, textvariable=self.box_size, width=3,
                   command=self.rebuild_cycles,
                   bg=self.colors["entry_bg"], fg=self.colors["entry_fg"],
                   relief="flat")\
            .pack(side="left", padx=5)

        tk.Label(top, text="Font:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left")
        tk.Spinbox(top, from_=8, to=24, textvariable=self.font_size, width=3,
                   command=self.rebuild_cycles,
                   bg=self.colors["entry_bg"], fg=self.colors["entry_fg"],
                   relief="flat")\
            .pack(side="left", padx=5)

        # Mode & step controls
        tk.Radiobutton(top, text="Animate", variable=self.mode, value="animate",
                       bg=self.colors["bg"], fg=self.colors["fg"],
                       selectcolor=self.colors["bg"])\
            .pack(side="left", padx=5)
        tk.Radiobutton(top, text="Step", variable=self.mode, value="step",
                       bg=self.colors["bg"], fg=self.colors["fg"],
                       selectcolor=self.colors["bg"])\
            .pack(side="left", padx=5)
        tk.Button(top, text="Prev", command=self.prev_step,
                  bg=self.colors["btn_bg"], fg=self.colors["btn_fg"],
                  relief="flat")\
            .pack(side="left", padx=5)
        tk.Button(top, text="Next", command=self.next_step,
                  bg=self.colors["btn_bg"], fg=self.colors["btn_fg"],
                  relief="flat")\
            .pack(side="left", padx=5)

        # Copy / Save / Clear
        tk.Button(top, text="Copy Output", command=self.copy_output,
                  bg=self.colors["btn_bg"], fg=self.colors["btn_fg"],
                  relief="flat")\
            .pack(side="right", padx=5)
        tk.Button(top, text="Save Output", command=self.save_output,
                  bg=self.colors["btn_bg"], fg=self.colors["btn_fg"],
                  relief="flat")\
            .pack(side="right", padx=5)
        tk.Button(top, text="Clear All", command=self.clear_all,
                  bg=self.colors["btn_bg"], fg=self.colors["btn_fg"],
                  relief="flat")\
            .pack(side="right", padx=5)

        # Input field
        frm_in = tk.Frame(self, bg=self.colors["bg"])
        frm_in.pack(fill="x", pady=5)
        tk.Label(frm_in, text="Input:", bg=self.colors["bg"], fg=self.colors["fg"])\
            .pack(side="left", padx=5)
        self.input_var = tk.StringVar()
        tk.Entry(frm_in, textvariable=self.input_var,
                 bg=self.colors["entry_bg"], fg=self.colors["entry_fg"],
                 relief="flat", validate="key",
                 validatecommand=(self.register(self.validate_input), '%P'))\
            .pack(side="left", fill="x", expand=True)

        # Scrollable cycles
        self.scroll_frame = ScrollableFrame(self, bg_color=self.colors["bg"])
        self.scroll_frame.pack(fill="both", expand=True, pady=5)
        self.rebuild_cycles()

        # Live preview
        self.preview = tk.Label(self, text="", bg=self.colors["bg"], fg=self.colors["fg"])
        self.preview.pack(fill="x", pady=5)

        self.validate_widgets()

    def validate_input(self, proposed: str) -> bool:
        # limit to 50 chars and numeric shift <=25
        if len(proposed) > 50:
            return False
        # allow digits, letters, space, sep chars
        return True

    def on_theme_change(self, _):
        self.colors = self.themes[self.current_theme.get()]
        self.apply_theme()
        self.rebuild_cycles()

    def apply_theme(self):
        c = self.colors
        self.configure(bg=c["bg"])
        for w in self.winfo_children():
            try: w.configure(bg=c["bg"], fg=c["fg"])
            except: pass
            for w2 in w.winfo_children():
                try:
                    w2.configure(bg=c.get("entry_bg",c["bg"]),
                                 fg=c.get("entry_fg",c["fg"]))
                except: pass

    def validate_widgets(self):
        valid_shift = self.shift.get().isdigit() and 1 <= int(self.shift.get()) <= 25
        has_text = bool(self.input_var.get())
        state = 'normal' if (valid_shift and has_text) else 'disabled'
        for btn in self.winfo_children()[0].winfo_children():
            if isinstance(btn, tk.Button) and btn['text'] in ("Encrypt","Decrypt"):
                btn['state'] = state

    def rebuild_cycles(self):
        for child in self.scroll_frame.inner.winfo_children():
            child.destroy()
        self.canvases = []
        for i in range(self.cycles.get()):
            frm = tk.LabelFrame(self.scroll_frame.inner, text=f"Cycle {i+1}",
                                fg=self.colors["fg"], bg=self.colors["bg"])
            frm.pack(fill="x", padx=10, pady=5)
            # dynamic width based on max content (50 chars)
            total_width = 20 + (self.box_size.get() + 5) * 50
            cv = tk.Canvas(frm, height=self.box_size.get()*2+60,
                           width=total_width,
                           bg=self.colors["canvas_bg"], highlightthickness=0)
            cv.pack(fill="both", expand=True)
            map_cv = tk.Canvas(frm, height=self.box_size.get()+20,
                               width=20 + (self.box_size.get()//2+2)*26,
                               bg=self.colors["canvas_bg"], highlightthickness=0)
            map_cv.pack(fill="x")
            self.canvases.append((cv, map_cv))
        self.validate_widgets()

    def clear_all(self):
        self.input_var.set("")
        self.shift.set("5")
        self.cycles.set(3)
        self.preserve.set(True)
        self.box_size.set(30)
        self.font_size.set(12)
        self.mode.set("animate")
        self.preview['text'] = ""
        self.scroll_frame.inner.yview_moveto(0)
        self.rebuild_cycles()

    def encrypt(self): self._prepare("encrypt")
    def decrypt(self): self._prepare("decrypt")

    def _prepare(self, action):
        self.validate_widgets()
        txt = self.input_var.get()
        try:
            s = int(self.shift.get())
        except:
            messagebox.showerror("Error","Shift must be 1–25"); return
        shift = s if action=="encrypt" else -s
        preserve = self.preserve.get()
        self.precomputed = []
        for _ in range(self.cycles.get()):
            out = caesar_shift(txt, shift, preserve)
            self.precomputed.append((txt, out))
            txt = out
        if self.mode.get()=="animate":
            self.after(100, lambda: self.animate_cycle(0,0))
        else:
            self.step_index = (0,0)
            self.draw_step()

    def animate_cycle(self, ci, li):
        if ci >= len(self.precomputed):
            self.preview['text'] = "Final: " + self.precomputed[-1][1]
            return
        inp, outp = self.precomputed[ci]
        cv, map_cv = self.canvases[ci]
        if li == 0:
            cv.delete("all"); map_cv.delete("all")
        if li < len(inp):
            self._draw_letters(cv, inp[:li+1], outp[:li+1])
            self.after(200, lambda: self.animate_cycle(ci, li+1))
        else:
            shift_val = (ord(outp[0]) - ord(inp[0])) % 26 if inp else 0
            self.draw_mapping(map_cv, shift_val)
            self.after(500, lambda: self.animate_cycle(ci+1, 0))

    def draw_step(self):
        ci, li = self.step_index
        for idx,(cv, map_cv) in enumerate(self.canvases):
            cv.delete("all"); map_cv.delete("all")
            if idx < ci:
                inp, outp = self.precomputed[idx]
                self._draw_letters(cv, inp, outp)
                self.draw_mapping(map_cv, (ord(outp[0]) - ord(inp[0])) % 26)
        if ci < len(self.precomputed):
            inp, outp = self.precomputed[ci]
            cv, map_cv = self.canvases[ci]
            self._draw_letters(cv, inp[:li+1], outp[:li+1])
            self.draw_mapping(map_cv, (ord(outp[0]) - ord(inp[0])) % 26)
        self.preview['text'] = "Final: " + self.precomputed[-1][1]

    def next_step(self):
        ci, li = self.step_index
        if ci < len(self.precomputed):
            if li < len(self.precomputed[ci][0]) - 1:
                self.step_index = (ci, li+1)
            else:
                self.step_index = (ci+1, 0)
            self.draw_step()

    def prev_step(self):
        ci, li = self.step_index
        if li > 0:
            self.step_index = (ci, li-1)
        elif ci > 0:
            prev_len = len(self.precomputed[ci-1][0])
            self.step_index = (ci-1, prev_len-1)
        self.draw_step()

    def _draw_letters(self, cv, inp, outp):
        cv.delete("all")
        x = 10; bs = self.box_size.get(); sp = 5
        for c1,c2 in zip(inp, outp):
            y1 = 10; y2 = y1 + bs + 40
            col = self.colors["error"] if not c1.isalpha() else self.colors["box_outline"]
            cv.create_rectangle(x, y1, x+bs, y1+bs,
                                fill=self.colors["box_fill"],
                                outline=col, width=2)
            cv.create_text(x+bs/2, y1+bs/2, text=c1,
                           fill=col, font=("Serif", self.font_size.get()))
            cv.create_line(x+bs/2, y1+bs, x+bs/2, y2,
                           arrow=tk.LAST, fill=self.colors["arrow"], width=2)
            cv.create_rectangle(x, y2, x+bs, y2+bs,
                                fill=self.colors["box_fill"],
                                outline=self.colors["box_outline"], width=2)
            cv.create_text(x+bs/2, y2+bs/2, text=c2,
                           fill=self.colors["fg"], font=("Serif", self.font_size.get()))
            x += bs + sp

    def draw_mapping(self, canvas, shift):
        canvas.delete("all")
        x = 10; bs = self.box_size.get()//2; sp = 2; y = 10
        for i,ch in enumerate(string.ascii_uppercase):
            canvas.create_rectangle(x, y, x+bs, y+bs,
                                    fill=self.colors["box_fill"],
                                    outline=self.colors["box_outline"])
            canvas.create_text(x+bs/2, y+bs/2, text=ch,
                               fill=self.colors["fg"],
                               font=("Serif", int(self.font_size.get()*0.8)))
            shifted = chr((i+shift)%26 + ord('A'))
            canvas.create_text(x+bs/2, y+bs+bs/2+5, text=shifted,
                               fill=self.colors["fg"],
                               font=("Serif", int(self.font_size.get()*0.8)))
            x += bs + sp

    def copy_output(self):
        if self.precomputed:
            self.clipboard_clear()
            self.clipboard_append(self.precomputed[-1][1])

    def save_output(self):
        if not self.precomputed:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files","*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.precomputed[-1][1])
            messagebox.showinfo("Saved", "Output saved to file.")

if __name__ == "__main__":
    CaesarVisualizer().mainloop()