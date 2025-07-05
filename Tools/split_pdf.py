import os
import threading
import argparse
import tkinter as tk
from typing import Callable
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from pypdf import PdfReader, PdfWriter

def parse_pages(pages_str: str | None, total: int) -> list[int]:
    """Return zero-based page indexes to extract from a PDF."""
    if not pages_str:
        return list(range(total))

    pages: set[int] = set()
    for part in pages_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start = int(start_s) - 1
            end = int(end_s) - 1
            pages.update(range(start, min(end + 1, total)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total)

def split_pdf(
    pdf_path: str,
    out_dir: str | None = None,
    pattern: str = "{base}_{num:03d}.pdf",
    pages: str | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
):
    """Split *pdf_path* into pages and save them.

    Parameters
    ----------
    pdf_path: path to the PDF file
    out_dir: directory to place output files (defaults to PDF directory)
    pattern: file name pattern using ``base`` and ``num`` placeholders
    pages: page ranges in ``1-3,5`` form, or ``None`` for all pages
    progress_cb: optional callback ``(current, total)`` for progress
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)

    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        raise RuntimeError("PDF is encrypted")

    total_pages = len(reader.pages)
    page_indexes = parse_pages(pages, total_pages)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = out_dir or os.path.dirname(pdf_path)
    os.makedirs(out_dir, exist_ok=True)

    for idx, page_no in enumerate(page_indexes, start=1):
        writer = PdfWriter()
        writer.add_page(reader.pages[page_no])
        filename = pattern.format(base=base, num=idx, page=page_no + 1)
        with open(os.path.join(out_dir, filename), "wb") as f:
            writer.write(f)
        if progress_cb:
            progress_cb(idx, len(page_indexes))


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

        # Options frame
        self.out_var = tk.StringVar(value="")
        self.pattern_var = tk.StringVar(value="{base}_{num:03d}.pdf")
        self.pages_var = tk.StringVar(value="")

        opt = tk.Frame(self, bg="#333333")
        tk.Label(opt, text="Output Dir:", fg="#ffffff", bg="#333333").grid(row=0, column=0, sticky="e")
        out_entry = tk.Entry(opt, textvariable=self.out_var, width=40)
        out_entry.grid(row=0, column=1, padx=5)
        tk.Button(opt, text="Browse", command=self._choose_output, bg="#555555", fg="#ffffff", relief="flat").grid(row=0, column=2)

        tk.Label(opt, text="Pattern:", fg="#ffffff", bg="#333333").grid(row=1, column=0, sticky="e", pady=2)
        tk.Entry(opt, textvariable=self.pattern_var, width=40).grid(row=1, column=1, columnspan=2, padx=5, pady=2, sticky="w")

        tk.Label(opt, text="Pages:", fg="#ffffff", bg="#333333").grid(row=2, column=0, sticky="e")
        tk.Entry(opt, textvariable=self.pages_var, width=40).grid(row=2, column=1, columnspan=2, padx=5, sticky="w")
        opt.pack(pady=5)

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

    def _choose_output(self):
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.out_var.set(directory)

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
        args = (
            pdf_path,
            self.out_var.get() or None,
            self.pattern_var.get() or "{base}_{num:03d}.pdf",
            self.pages_var.get() or None,
        )
        threading.Thread(target=self._split, args=args, daemon=True).start()

    def _split(self, pdf_path, out_dir, pattern, pages):
        try:
            split_pdf(
                pdf_path,
                out_dir=out_dir,
                pattern=pattern,
                pages=pages,
                progress_cb=lambda i, t: self._update_progress(i, t),
            )
            messagebox.showinfo("PDF Splitter", "Split completed")
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

    def _update_progress(self, i, total):
        self.progress["value"] = (i / total) * 100

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a PDF into pages")
    parser.add_argument("pdf", nargs="?", help="PDF file to split")
    parser.add_argument("--output", "-o", help="Output directory")
    parser.add_argument("--pattern", "-p", default="{base}_{num:03d}.pdf",
                        help="Filename pattern")
    parser.add_argument("--pages", "-P", help="Pages to extract, e.g. '1-3,5'")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    args = parser.parse_args()

    if args.pdf and not args.gui:
        try:
            split_pdf(
                args.pdf,
                out_dir=args.output,
                pattern=args.pattern,
                pages=args.pages,
                progress_cb=lambda i, t: print(f"{i}/{t}", end="\r"),
            )
            print("Done")
        except Exception as exc:
            print(f"Error: {exc}")
    else:
        root = TkinterDnD.Tk()
        PDFSplitter(root)
        root.mainloop()
