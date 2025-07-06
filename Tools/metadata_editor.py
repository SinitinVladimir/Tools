import os
import stat
import platform
import getpass
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from PIL import Image, PngImagePlugin
import piexif

# Optional IPTC support
try:
    import iptcinfo3
except ImportError:
    iptcinfo3 = None

# Optional drag-and-drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseApp = TkinterDnD.Tk
    HAVE_DND = True
except ImportError:
    BaseApp = tk.Tk
    HAVE_DND = False

# Windows API to set creation time
def to_filetime(dt: datetime) -> wintypes.FILETIME:
    us = int(dt.timestamp() * 1e7) + 116444736000000000
    return wintypes.FILETIME(us & 0xFFFFFFFF, us >> 32)

def set_creation_time(path: str, dt: datetime):
    FILE_WRITE_ATTRIBUTES = 0x0100
    handle = ctypes.windll.kernel32.CreateFileW(
        path, FILE_WRITE_ATTRIBUTES, 0, None,
        3, 0x02000000, None
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError()
    ft = to_filetime(dt)
    if not ctypes.windll.kernel32.SetFileTime(handle,
                                              ctypes.byref(ft),
                                              None, None):
        ctypes.windll.kernel32.CloseHandle(handle)
        raise ctypes.WinError()
    ctypes.windll.kernel32.CloseHandle(handle)

class FullMetadataEditor(BaseApp):
    def __init__(self):
        super().__init__()
        self.title("🖼 Full Metadata Editor")
        self.configure(bg="#2e2e2e")
        self.geometry("1000x700")
        self.filepath = None
        self.meta = {}

        self.safe_cats = [
            "File-System Metadata",
            "EXIF (safe)",
            "IPTC (safe)",
            "PNG Text (safe)"
        ]
        self.risky_cats = [
            "Basic Image Info",
            "Camera Settings",
            "Maker Notes",
            "Other Potential Metadata",
            "XMP (read-only)"
        ]

        # Top buttons
        top = tk.Frame(self, bg="#2e2e2e")
        top.pack(fill="x", pady=4)
        tk.Button(top, text="Open Image…",   command=self.open_image,
                  bg="#444", fg="#fff", padx=8, pady=4, relief="flat")\
          .pack(side="left", padx=5)
        tk.Button(top, text="Anonymize Safe", command=self.anonymize,
                  bg="#884444", fg="#fff", padx=8, pady=4, relief="flat")\
          .pack(side="left", padx=5)
        tk.Button(top, text="Save All",       command=self.save_all,
                  bg="#444", fg="#fff", padx=8, pady=4, relief="flat")\
          .pack(side="left", padx=5)

        # Treeview
        cols = ("Category","Field","Value")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#333", fieldbackground="#333",
                        foreground="#fff", rowheight=24)
        style.map("Treeview", background=[("selected","#555")])
        self.tree = ttk.Treeview(self, columns=cols, show="tree headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=300, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.tag_configure("safe",    background="#222", foreground="#fff")
        self.tree.tag_configure("risky",   background="#550000", foreground="#fff")
        self.tree.tag_configure("section", font=('TkDefaultFont', 12, 'bold'))

        # Bottom editor
        bottom = tk.Frame(self, bg="#2e2e2e")
        bottom.pack(fill="x", pady=4)
        tk.Label(bottom, text="New Value:", bg="#2e2e2e", fg="#fff")\
          .pack(side="left", padx=5)
        self.val_var = tk.StringVar()
        tk.Entry(bottom, textvariable=self.val_var,
                 bg="#222", fg="#fff", insertbackground="#fff")\
          .pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(bottom, text="Update Field", command=self.update_field,
                  bg="#444", fg="#fff", padx=8, relief="flat")\
          .pack(side="left", padx=5)

        if HAVE_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", lambda e: self.load(e.data.strip("{}")))

    def open_image(self):
        p = filedialog.askopenfilename(
            filetypes=[("Images","*.jpg;*.jpeg;*.png;*.tiff;*.bmp")])
        if p:
            self.load(p)

    def load(self, path):
        if not os.path.isfile(path):
            return
        self.filepath = path
        self.meta.clear()
        self.tree.delete(*self.tree.get_children())

        # 1) File-System
        st = os.stat(path)
        fs = {
            "File name":   os.path.basename(path),
            "File size":   f"{st.st_size} bytes",
            "Created":     datetime.fromtimestamp(st.st_ctime).isoformat(),
            "Modified":    datetime.fromtimestamp(st.st_mtime).isoformat(),
            "Accessed":    datetime.fromtimestamp(st.st_atime).isoformat(),
            "Owner":       getpass.getuser(),
            "Permissions": stat.filemode(st.st_mode)
        }
        self.meta["File-System Metadata"] = fs

        # 2) EXIF safe
        ex_safe = {}
        try:
            exif = piexif.load(path)
            for name, tag, ifd in [
                ("DateTimeOriginal", piexif.ExifIFD.DateTimeOriginal, "Exif"),
                ("DateTimeDigitized", piexif.ExifIFD.DateTimeDigitized, "Exif"),
                ("DateTime", piexif.ImageIFD.DateTime, "0th")
            ]:
                v = exif[ifd].get(tag)
                ex_safe[name] = v.decode() if isinstance(v, bytes) else v
            for name, tag in [
                ("GPSLatitude", piexif.GPSIFD.GPSLatitude),
                ("GPSLongitude", piexif.GPSIFD.GPSLongitude),
                ("GPSAltitude", piexif.GPSIFD.GPSAltitude),
                ("GPSDateStamp", piexif.GPSIFD.GPSDateStamp),
                ("GPSTimeStamp", piexif.GPSIFD.GPSTimeStamp)
            ]:
                ex_safe[name] = exif["GPS"].get(tag)
        except:
            pass
        self.meta["EXIF (safe)"] = ex_safe

        # 3) EXIF risky
        risky = {}
        try:
            exif = piexif.load(path)
            img = Image.open(path)
            bi = {"Width":img.width,"Height":img.height,"Mode":img.mode}
            dpi = img.info.get("dpi")
            if dpi: bi["DPI"]=f"{dpi[0]}×{dpi[1]}"
            bi["Orientation"]=exif["0th"].get(piexif.ImageIFD.Orientation)
            risky["Basic Image Info"] = bi
            cs = {}
            for name, tag in [
                ("Make", piexif.ImageIFD.Make),("Model",piexif.ImageIFD.Model),
                ("F-Number",piexif.ExifIFD.FNumber),("ExposureTime",piexif.ExifIFD.ExposureTime),
                ("ISO",piexif.ExifIFD.ISOSpeedRatings),("FocalLength",piexif.ExifIFD.FocalLength),
                ("Flash",piexif.ExifIFD.Flash),("WhiteBalance",piexif.ExifIFD.WhiteBalance),
                ("MeteringMode",piexif.ExifIFD.MeteringMode),
                ("ExposureProgram",piexif.ExifIFD.ExposureProgram),
                ("ExposureBias",piexif.ExifIFD.ExposureBiasValue),
            ]:
                v=exif["Exif"].get(tag)
                if v is not None: cs[name]=v
            risky["Camera Settings"]=cs
            mn=exif["Exif"].get(piexif.ExifIFD.MakerNote)
            risky["Maker Notes"]={"MakerNote":mn}
            oth={}
            sw=exif["0th"].get(piexif.ImageIFD.Software)
            if sw: oth["Software"]= sw.decode() if isinstance(sw,bytes) else sw
            if "icc_profile" in img.info: oth["ICC Profile"]=True
            risky["Other Potential Metadata"]=oth
        except:
            pass
        self.meta.update(risky)

        # 4) IPTC safe
        ip_safe={}
        if iptcinfo3:
            try:
                info=iptcinfo3.IPTCInfo(path,force=True)
                ip_safe=dict(info._data)
            except:
                pass
        self.meta["IPTC (safe)"]=ip_safe

        # 5) Read-only XMP
        xm = {}
        raw = open(path,"rb").read().decode(errors="ignore")
        s,e = raw.find("<x:xmpmeta"), raw.find("</x:xmpmeta>")+12
        xm["Raw XMP"]= raw[s:e] if s>-1 and e>s else ""
        self.meta["XMP (read-only)"]=xm

        # 6) PNG Text safe
        png_safe={}
        if path.lower().endswith(".png"):
            png_safe=dict(Image.open(path).info)
        self.meta["PNG Text (safe)"]=png_safe

        # show immediately
        self.populate_tree()

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        safe_root = self.tree.insert("", "end", text="Safe to Edit", tags=("section",))
        risky_root = self.tree.insert("", "end", text="Risky to Edit", tags=("section",))
        for cat in self.safe_cats:
            if cat in self.meta:
                cr = self.tree.insert(safe_root,"end",text=cat,tags=("section",))
                for f,v in self.meta[cat].items():
                    self.tree.insert(cr,"end",text="",values=(cat,f,v),tags=("safe",))
        for cat in self.risky_cats:
            if cat in self.meta:
                cr = self.tree.insert(risky_root,"end",text=cat,tags=("section",))
                for f,v in self.meta.get(cat,{}).items():
                    self.tree.insert(cr,"end",text="",values=(cat,f,v),tags=("risky",))

    def on_select(self,_):
        sel=self.tree.focus()
        tags=self.tree.item(sel,"tags")
        vals=self.tree.item(sel)["values"]
        if "safe" in tags and len(vals)==3:
            self.val_var.set(vals[2])
        else:
            self.val_var.set("")

    def update_field(self):
        sel=self.tree.focus()
        tags=self.tree.item(sel,"tags")
        vals=self.tree.item(sel)["values"]
        if "safe" not in tags or len(vals)!=3: return
        cat,f,_=vals
        new=self.val_var.get()
        self.meta[cat][f]=new
        self.tree.item(sel,values=(cat,f,new))

    def anonymize(self):
        placeholder="2000-01-01T00:00:00"
        fs=self.meta.get("File-System Metadata",{})
        for k in ("Created","Modified","Accessed"):
            if k in fs: fs[k]=placeholder
        fs["Owner"]=""
        ex=self.meta.get("EXIF (safe)",{})
        for k in list(ex):
            if "DateTime" in k: ex[k]=placeholder
            if k.startswith("GPS"): ex[k]=None
        ip=self.meta.get("IPTC (safe)",{})
        for k in list(ip): ip[k]=""
        png=self.meta.get("PNG Text (safe)",{})
        for k in list(png): png[k]=""
        self.populate_tree()

    def save_all(self):
        path=self.filepath
        # filesystem
        fs=self.meta.get("File-System Metadata",{})
        try:
            m=datetime.fromisoformat(fs["Modified"]).timestamp()
            a=datetime.fromisoformat(fs["Accessed"]).timestamp()
            os.utime(path,(a,m))
            if platform.system()=="Windows":
                dtc=datetime.fromisoformat(fs["Created"])
                set_creation_time(path,dtc)
        except: pass

        # EXIF safe
        try:
            exif=piexif.load(path)
            tagmap={
                "DateTimeOriginal":(piexif.ExifIFD.DateTimeOriginal,"Exif"),
                "DateTimeDigitized":(piexif.ExifIFD.DateTimeDigitized,"Exif"),
                "DateTime":(piexif.ImageIFD.DateTime,"0th"),
                "GPSLatitude":(piexif.GPSIFD.GPSLatitude,"GPS"),
                "GPSLongitude":(piexif.GPSIFD.GPSLongitude,"GPS"),
                "GPSAltitude":(piexif.GPSIFD.GPSAltitude,"GPS"),
                "GPSDateStamp":(piexif.GPSIFD.GPSDateStamp,"GPS"),
                "GPSTimeStamp":(piexif.GPSIFD.GPSTimeStamp,"GPS"),
            }
            for k,v in self.meta.get("EXIF (safe)",{}).items():
                if k in tagmap:
                    tag,ifd=tagmap[k]
                    exif[ifd][tag]=v
            piexif.insert(piexif.dump(exif),path)
        except: pass

        # IPTC safe
        if iptcinfo3:
            try:
                info=iptcinfo3.IPTCInfo(path,force=True)
                for k,v in self.meta.get("IPTC (safe)",{}).items():
                    info[k]=v
                info.save_as(path)
            except: pass

        # PNG safe
        if path.lower().endswith(".png"):
            try:
                img=Image.open(path)
                meta=PngImagePlugin.PngInfo()
                for k,v in self.meta.get("PNG Text (safe)",{}).items():
                    meta.add_text(k,v)
                img.save(path,pnginfo=meta)
            except: pass

        messagebox.showinfo("Saved","Safe metadata saved successfully.")

if __name__=="__main__":
    FullMetadataEditor().mainloop()
