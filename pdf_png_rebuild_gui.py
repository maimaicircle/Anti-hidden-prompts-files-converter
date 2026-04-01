#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF -> PNG pages -> rebuilt PDF GUI
依赖:
    pip install pymupdf pillow

功能:
1. 选择一个 PDF
2. 自动把每一页导出为 PNG
3. 再把这些 PNG 合成为一个新的 PDF
4. 输出到用户指定目录
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


APP_TITLE = "PDF 每页转 PNG 后重组为 PDF"
DEFAULT_SCALE = 2.0  # 约等于 144 DPI


class PDFConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("760x520")
        self.root.minsize(700, 480)

        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.scale_var = tk.StringVar(value=str(DEFAULT_SCALE))
        self.keep_png_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="就绪")
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
            text="选择 PDF 后，程序会先把每一页导出为 PNG，再把这些 PNG 重新合成为一个新的 PDF。",
            wraplength=700,
        )
        desc.pack(anchor="w", pady=(0, 16))

        # PDF input
        pdf_frame = ttk.LabelFrame(main, text="1. 选择输入 PDF", padding=12)
        pdf_frame.pack(fill="x", pady=(0, 12))

        ttk.Entry(pdf_frame, textvariable=self.pdf_path).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(pdf_frame, text="浏览…", command=self.browse_pdf).pack(side="left")

        # Output
        out_frame = ttk.LabelFrame(main, text="2. 选择输出目录", padding=12)
        out_frame.pack(fill="x", pady=(0, 12))

        ttk.Entry(out_frame, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(out_frame, text="浏览…", command=self.browse_output_dir).pack(side="left")

        # Options
        opt_frame = ttk.LabelFrame(main, text="3. 参数", padding=12)
        opt_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(opt_frame, text="渲染倍率 scale：").grid(row=0, column=0, sticky="w")
        ttk.Entry(opt_frame, textvariable=self.scale_var, width=10).grid(row=0, column=1, sticky="w", padx=(8, 24))
        ttk.Label(opt_frame, text="建议 2.0；越大越清晰，但文件越大").grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(
            opt_frame,
            text="保留中间 PNG 文件",
            variable=self.keep_png_var
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(10, 0))

        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(4, 12))

        self.convert_btn = ttk.Button(btn_frame, text="开始转换", command=self.start_conversion)
        self.convert_btn.pack(side="left")

        ttk.Button(btn_frame, text="打开输出目录", command=self.open_output_dir).pack(side="left", padx=(8, 0))

        # Progress
        prog_frame = ttk.LabelFrame(main, text="4. 进度", padding=12)
        prog_frame.pack(fill="x", pady=(0, 12))

        self.progress = ttk.Progressbar(
            prog_frame, maximum=100, variable=self.progress_var, mode="determinate"
        )
        self.progress.pack(fill="x")
        ttk.Label(prog_frame, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))

        # Log box
        log_frame = ttk.LabelFrame(main, text="日志", padding=12)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log("程序已启动。")

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
            self.log("缺少依赖: " + ", ".join(missing))
            self.log("请先安装：pip install " + " ".join(missing))
            messagebox.showwarning(
                "缺少依赖",
                "检测到缺少依赖：\n\n"
                + "\n".join(missing)
                + "\n\n请先运行：\n"
                + "pip install " + " ".join(missing)
            )

    def browse_pdf(self):
        path = filedialog.askopenfilename(
            title="选择 PDF",
            filetypes=[("PDF 文件", "*.pdf")]
        )
        if path:
            self.pdf_path.set(path)
            self.log(f"已选择 PDF: {path}")

    def browse_output_dir(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)
            self.log(f"已选择输出目录: {path}")

    def open_output_dir(self):
        path = self.output_dir.get().strip()
        if not path:
            messagebox.showerror("错误", "输出目录为空。")
            return
        if not os.path.isdir(path):
            messagebox.showerror("错误", "输出目录不存在。")
            return

        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开输出目录：{e}")

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
            messagebox.showerror("错误", "依赖未安装完整，请先安装 pymupdf 和 pillow。")
            return

        pdf_path = self.pdf_path.get().strip()
        output_dir = self.output_dir.get().strip()

        if not pdf_path:
            messagebox.showerror("错误", "请先选择输入 PDF。")
            return
        if not os.path.isfile(pdf_path):
            messagebox.showerror("错误", "输入 PDF 不存在。")
            return
        if not output_dir:
            messagebox.showerror("错误", "请先选择输出目录。")
            return
        if not os.path.isdir(output_dir):
            messagebox.showerror("错误", "输出目录不存在。")
            return

        try:
            scale = float(self.scale_var.get().strip())
            if scale <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("错误", "scale 必须是大于 0 的数字，例如 2.0。")
            return

        self.convert_btn.config(state="disabled")
        self.set_progress(0)
        self.set_status("开始转换…")
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

            self.safe_log(f"开始处理: {pdf_path}")
            self.safe_log(f"PNG 输出目录: {png_dir}")
            self.safe_log(f"重组 PDF 输出: {rebuilt_pdf}")

            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if total_pages == 0:
                raise RuntimeError("PDF 没有页面。")

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
                self.safe_status(f"正在导出 PNG：第 {i+1}/{total_pages} 页")
                self.safe_log(f"已导出 PNG: {png_path.name}")

            doc.close()

            # Step 2: rebuild PDF from PNG
            pil_images = []
            for i, png_path in enumerate(png_paths):
                img = Image.open(png_path).convert("RGB")
                pil_images.append(img)

                progress = 70 + (i + 1) / total_pages * 25
                self.safe_progress(progress)
                self.safe_status(f"正在重组 PDF：第 {i+1}/{total_pages} 页")

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
            self.safe_status("转换完成")
            self.safe_log(f"完成。输出文件：{rebuilt_pdf}")
            self.root.after(0, lambda: messagebox.showinfo("完成", f"转换完成！\n\n输出文件：\n{rebuilt_pdf}"))

        except Exception as e:
            error_message = str(e)
            err = traceback.format_exc()
            self.safe_log("发生错误：")
            self.safe_log(err)
            self.safe_status("转换失败")
            self.root.after(0, lambda msg=error_message: messagebox.showerror("错误", f"转换失败：\n{msg}"))
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
