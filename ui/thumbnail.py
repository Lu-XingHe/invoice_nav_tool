# -*- coding: utf-8 -*-
"""缩略图与PDF预览（支持图片、PDF多页翻页）"""

import io  # 新增
import os
import sys
from tkinter import *
from tkinter import messagebox

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fitz  # PyMuPDF

    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def show_thumbnail(parent, file_path):
    """
    根据文件类型打开预览
    - 图片：显示缩略图窗口
    - PDF：使用 PyMuPDF 渲染为图像，支持翻页
    - 其他：提示不支持
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']:
        _show_image_preview(parent, file_path)

    elif ext == '.pdf':
        if not HAS_FITZ:
            messagebox.showinfo("提示", "请安装 PyMuPDF 以支持 PDF 预览:\npip install PyMuPDF")
            return
        _show_pdf_preview(parent, file_path)

    elif ext == '.ofd':
        # OFD 预览较复杂，提示用户使用外部程序
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            else:
                import subprocess
                if sys.platform == 'darwin':
                    subprocess.run(['open', file_path])
                else:
                    subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开 OFD 文件: {str(e)}")

    else:
        messagebox.showinfo("提示", f"暂不支持预览此文件类型: {ext}")


def _show_image_preview(parent, file_path):
    """图片缩略图预览"""
    if not HAS_PIL:
        messagebox.showinfo("提示", "请安装PIL库以支持缩略图预览: pip install pillow")
        return
    try:
        img = Image.open(file_path)
        max_size = 600
        img.thumbnail((max_size, max_size))
        img_tk = ImageTk.PhotoImage(img)
        win = Toplevel(parent)
        win.title(f"图片预览: {os.path.basename(file_path)}")
        label = Label(win, image=img_tk)
        label.image = img_tk
        label.pack(padx=10, pady=10)
        Button(win, text="关闭", command=win.destroy).pack(pady=5)
        win.transient(parent)
        win.grab_set()
        win.focus_force()
        parent.wait_window(win)
    except Exception as e:
        messagebox.showerror("错误", f"无法预览图片: {str(e)}")


def _show_pdf_preview(parent, file_path):
    """PDF 多页预览（使用 PyMuPDF）"""
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        if total_pages == 0:
            messagebox.showinfo("提示", "PDF 文件为空")
            return

        current_page = 0

        win = Toplevel(parent)
        win.title(f"PDF 预览: {os.path.basename(file_path)}")
        win.geometry("700x750")
        win.transient(parent)
        win.grab_set()

        # 显示页码
        page_label = Label(win, text=f"第 1/{total_pages} 页", font=("微软雅黑", 10))
        page_label.pack(pady=5)

        # 图像显示区域
        img_frame = Frame(win)
        img_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        img_label = Label(img_frame)
        img_label.pack(fill=BOTH, expand=True)

        def render_page(page_num):
            """渲染指定页并显示"""
            page = doc[page_num]
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            max_w = 650
            max_h = 600
            img.thumbnail((max_w, max_h))
            img_tk = ImageTk.PhotoImage(img)
            img_label.config(image=img_tk)
            img_label.image = img_tk
            page_label.config(text=f"第 {page_num + 1}/{total_pages} 页")

        def prev_page():
            nonlocal current_page
            if current_page > 0:
                current_page -= 1
                render_page(current_page)

        def next_page():
            nonlocal current_page
            if current_page < total_pages - 1:
                current_page += 1
                render_page(current_page)

        btn_frame = Frame(win)
        btn_frame.pack(pady=10)
        Button(btn_frame, text="◀ 上一页", command=prev_page, state=NORMAL if total_pages > 1 else DISABLED).pack(
            side=LEFT, padx=5)
        Button(btn_frame, text="下一页 ▶", command=next_page, state=NORMAL if total_pages > 1 else DISABLED).pack(
            side=LEFT, padx=5)
        Button(btn_frame, text="关闭", command=win.destroy).pack(side=LEFT, padx=5)

        render_page(0)
        win.focus_force()
        parent.wait_window(win)
        doc.close()

    except Exception as e:
        messagebox.showerror("错误", f"无法预览 PDF: {str(e)}")
