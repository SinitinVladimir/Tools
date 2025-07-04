import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from pypdf import PdfReader, PdfWriter

class PDFSplitter(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#333333")
        master.title("PDF Splitter")
        master.geometry("777x333")
        master.configure(bg="#333333")

        # Progress bar style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.Horizontal.TProgressbar",
                        troughcolor="#444444",
                        background="#888888")

        # Drop area
        self.drop_label = tk.Label(
            self,
            text="Drag & drop a PDF here\nor click to browse",
            bg="#444444",
            fg="#ffffff",
            width=40,
            height=6,
            relief="ridge",
            bd=2
        )
        self.drop_label.pack(pady=(20,10))
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_label.bind("<Button-1>", lambda e: self._on_browse())
        self.drop_label.bind("<Enter>", lambda e: self.drop_label.config(bg="#555555"))
        self.drop_label.bind("<Leave>", lambda e: self.drop_label.config(bg="#444444"))

        # Progress bar
        self.progress = ttk.Progressbar(
            self,
            style="Dark.Horizontal.TProgressbar",
            orient="horizontal",
            length=400,
            mode="determinate"
        )
        self.progress.pack(pady=(0,10))
        self.progress["value"] = 0

        # Browse button
        self.browse_btn = tk.Button(
            self,
            text="Browse PDF",
            command=self._on_browse,
            bg="#555555",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=5
        )
        self.browse_btn.pack()

        self.pack(expand=True)

    def _on_drop(self, event):
        path = event.data.strip("{}")
        self._start_split(path)

    def _on_browse(self):
        path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf")]
        )
        if path:
            self._start_split(path)

    def _start_split(self, pdf_path):
        self.browse_btn.config(state="disabled")
        self.drop_label.config(text="Processing...", fg="#ffdd00")
        threading.Thread(target=self._split, args=(pdf_path,), daemon=True).start()

    def _split(self, pdf_path):
        try:
            reader = PdfReader(pdf_path)
            total = len(reader.pages)
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            out_dir = os.path.dirname(pdf_path)

            for i, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                filename = f"{base}_{str(i).zfill(3)}.pdf"
                with open(os.path.join(out_dir, filename), "wb") as f:
                    writer.write(f)
                # update progress bar
                self.progress["value"] = (i / total) * 100

            messagebox.showinfo("PDF Splitter",
                                f"Successfully split into {total} files:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            # reset UI
            self.browse_btn.config(state="normal")
            self.drop_label.config(
                text="Drag & drop a PDF here\nor click to browse",
                fg="#ffffff"
            )
            self.progress["value"] = 0

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    PDFSplitter(root)
    root.mainloop()
