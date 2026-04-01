#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF -> PNG pages -> rebuilt PDF GUI
depends on:
    pip install pymupdf pillow

How does it work:
1. Select a PDF file and an output directory
2. Automatically export each page of the PDF as a PNG image (with adjustable scale)
3. Merge the PNG images back into a new PDF (with the same page size as the original)
4. Output the new PDF to the selected directory, with "_rebuilt_from_png" suffix
"""

import os
import threading
import traceback
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image
except Exception:
    Image = None


APP_TITLE = "PDF to PNG then Rebuild to PDF"
DEFAULT_SCALE = 2.0  # Approximately 144 DPI


class PDFConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("760x520")
        self.root.minsize(700, 480)

        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.scale_var = tk.StringVar(value=str(DEFAULT_SCALE))
        self.keep_png_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self._set_default_output_dir()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        desc = ttk.Label(
            main,
            text="Select a PDF file and an output directory. The program will export each page as a PNG image and then merge them into a new PDF.",
            wraplength=700,
        )
        desc.pack(anchor="w", pady=(0, 16))

        # PDF input
        pdf_frame = ttk.LabelFrame(main, text="1. Select Input PDF", padding=12)
        pdf_frame.pack(fill="x", pady=(0, 12))

        ttk.Entry(pdf_frame, textvariable=self.pdf_path).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(pdf_frame, text="Browse…", command=self.browse_pdf).pack(side="left")

        # Output
        out_frame = ttk.LabelFrame(main, text="2. Select Output Directory", padding=12)
        out_frame.pack(fill="x", pady=(0, 12))

        ttk.Entry(out_frame, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(out_frame, text="Browse…", command=self.browse_output_dir).pack(side="left")

        # Options
        opt_frame = ttk.LabelFrame(main, text="3. Parameters", padding=12)
        opt_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(opt_frame, text="Rendering Scale:").grid(row=0, column=0, sticky="w")
        ttk.Entry(opt_frame, textvariable=self.scale_var, width=10).grid(row=0, column=1, sticky="w", padx=(8, 24))
        ttk.Label(opt_frame, text="Recommended 2.0; higher values result in clearer images but larger files").grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(
            opt_frame,
            text="Keep Intermediate PNG Files",
            variable=self.keep_png_var
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(4, 12))

        self.convert_btn = ttk.Button(btn_frame, text="Start Conversion", command=self.start_conversion)
        self.convert_btn.pack(side="left")

        ttk.Button(btn_frame, text="Open Output Directory", command=self.open_output_dir).pack(side="left", padx=(8, 0))

        # Progress
        prog_frame = ttk.LabelFrame(main, text="4. Progress", padding=12)
        prog_frame.pack(fill="x", pady=(0, 12))

        self.progress = ttk.Progressbar(
            prog_frame, maximum=100, variable=self.progress_var, mode="determinate"
        )
        self.progress.pack(fill="x")
        ttk.Label(prog_frame, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))

        # Log box
        log_frame = ttk.LabelFrame(main, text="Log", padding=12)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log("Program started.")

        self._check_dependencies()

    def _set_default_output_dir(self):
        self.output_dir.set(os.path.join(os.path.expanduser("~"), "Desktop"))

    def _check_dependencies(self):
        missing = []
        if fitz is None:
            missing.append("pymupdf")
        if Image is None:
            missing.append("pillow")

        if missing:
            self.log("Missing dependencies: " + ", ".join(missing))
            self.log("Please install first: pip install " + " ".join(missing))
            messagebox.showwarning(
                "Missing Dependencies",
                "Missing dependencies detected:\n\n"
                + "\n".join(missing)
                + "\n\nPlease install first:\n"
                + "pip install " + " ".join(missing)
            )

    def browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if path:
            self.pdf_path.set(path)
            self.log(f"Selected PDF: {path}")

    def browse_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir.set(path)
            self.log(f"Selected output directory: {path}")

    def open_output_dir(self):
        path = self.output_dir.get().strip()
        if not path:
            messagebox.showerror("Error", "Output directory is empty.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Error", "Output directory does not exist.")
            return

        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Unable to open output directory: {e}")

    def log(self, text: str):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def set_status(self, text: str):
        self.status_var.set(text)
        self.root.update_idletasks()

    def set_progress(self, value: float):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def start_conversion(self):
        if fitz is None or Image is None:
            messagebox.showerror("Error", "Dependencies are not installed completely. Please install pymupdf and pillow.")
            return

        pdf_path = self.pdf_path.get().strip()
        output_dir = self.output_dir.get().strip()

        if not pdf_path:
            messagebox.showerror("Error", "Please select an input PDF.")
            return
        if not os.path.isfile(pdf_path):
            messagebox.showerror("Error", "Input PDF does not exist.")
            return
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return
        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Output directory does not exist.")
            return

        try:
            scale = float(self.scale_var.get().strip())
            if scale <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Scale must be a number greater than 0, e.g., 2.0.")
            return

        self.convert_btn.config(state="disabled")
        self.set_progress(0)
        self.set_status("Starting conversion…")
        self.log("=" * 60)

        worker = threading.Thread(
            target=self.convert_pdf,
            args=(pdf_path, output_dir, scale, self.keep_png_var.get()),
            daemon=True
        )
        worker.start()

    def convert_pdf(self, pdf_path: str, output_dir: str, scale: float, keep_png: bool):
        try:
            pdf_name = Path(pdf_path).stem
            png_dir = Path(output_dir) / f"{pdf_name}_png_pages"
            rebuilt_pdf = Path(output_dir) / f"{pdf_name}_rebuilt_from_png.pdf"

            png_dir.mkdir(parents=True, exist_ok=True)

            self.safe_log(f"Starting processing: {pdf_path}")
            self.safe_log(f"PNG output directory: {png_dir}")
            self.safe_log(f"Rebuilt PDF output: {rebuilt_pdf}")

            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if total_pages == 0:
                raise RuntimeError("PDF has no pages.")

            png_paths = []

            # Step 1: export pages to PNG
            for i, page in enumerate(doc):
                matrix = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                png_path = png_dir / f"page_{i+1:04d}.png"
                pix.save(str(png_path))
                png_paths.append(png_path)

                progress = (i + 1) / total_pages * 70
                self.safe_progress(progress)
                self.safe_status(f"Exporting PNG: Page {i+1}/{total_pages}")
                self.safe_log(f"Exported PNG: {png_path.name}")

            doc.close()

            # Step 2: rebuild PDF from PNG
            pil_images = []
            for i, png_path in enumerate(png_paths):
                img = Image.open(png_path).convert("RGB")
                pil_images.append(img)

                progress = 70 + (i + 1) / total_pages * 25
                self.safe_progress(progress)
                self.safe_status(f"Rebuilding PDF: Page {i+1}/{total_pages}")

            first, rest = pil_images[0], pil_images[1:]
            first.save(str(rebuilt_pdf), save_all=True, append_images=rest)

            for img in pil_images:
                img.close()

            # Step 3: optional cleanup
            if not keep_png:
                for png_path in png_paths:
                    try:
                        png_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                try:
                    png_dir.rmdir()
                except Exception:
                    pass

            self.safe_progress(100)
            self.safe_status("Conversion completed")
            self.safe_log(f"Completed. Output file: {rebuilt_pdf}")
            self.root.after(0, lambda: messagebox.showinfo("Completed", f"Conversion completed!\n\nOutput file:\n{rebuilt_pdf}"))

        except Exception as e:
            error_message = str(e)
            err = traceback.format_exc()
            self.safe_log("Error occurred:")
            self.safe_log(err)
            self.safe_status("Conversion failed")
            self.root.after(0, lambda msg=error_message: messagebox.showerror("Error", f"Conversion failed:\n{msg}"))
        finally:
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))

    def safe_log(self, text: str):
        self.root.after(0, lambda: self.log(text))

    def safe_status(self, text: str):
        self.root.after(0, lambda: self.set_status(text))

    def safe_progress(self, value: float):
        self.root.after(0, lambda: self.set_progress(value))


def main():
    root = tk.Tk()
    try:
        from tkinter import ttk
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass

    app = PDFConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
