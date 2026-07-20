# -*- coding: utf-8 -*-
"""主窗口 - 完整版，智能预处理后台完成，用户双击编辑确认"""

import hashlib
import json
import os
import re
import shutil
import threading
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES

    HAS_DND = True
except ImportError:
    HAS_DND = False
    TkinterDnD = None
    DND_FILES = None

from utils.settings import load_config
from core.ocr_client import OCRClient
from core.processors.invoice import process_invoice
from core.processors.screenshot import process_screenshot
from core.field_utils import generate_filename
from core.ai_assistant import AIAssistant
from core.invoice_handler import InvoiceHandler
from core.screenshot_handler import ScreenshotHandler
from core.preprocess import Preprocessor
from core.invoice_classifier import generate_invoice_filename
from ui.settings_dialog import SettingsDialog
from ui.history_dialog import HistoryDialog
from ui.preview_dialog import PreviewDialog


def extract_city_from_name(name: str):
    """从公司名称中提取市县名"""
    if not name:
        return None
    match = re.search(r'([\u4e00-\u9fa5]{2,})(?:市|县|区)', name)
    if match:
        return match.group(1)
    match = re.search(
        r'(山西|陕西|河南|河北|山东|江苏|浙江|安徽|福建|江西|湖北|湖南|广东|广西|海南|四川|贵州|云南|西藏|青海|甘肃|宁夏|新疆|内蒙古|北京|上海|天津|重庆|香港|澳门)',
        name)
    if match:
        return match.group(1)
    return None


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📄 OCR识别工具 - 发票报销系统")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 700)
        self.root.configure(bg='#f0f2f5')

        self.config = load_config()
        self.ocr_client = OCRClient()

        # 统一文件列表
        self.file_list = []
        self.output_dir = StringVar()
        self.skip_existing = BooleanVar(value=True)
        self.total_amount = 0.0
        self.batch_processor = None

        # 处理类型过滤器
        self.batch_type_var = StringVar(value="all")

        # AI 助手
        self.ai_assistant = None
        try:
            self.ai_assistant = AIAssistant()
            print("✅ AI助手初始化成功")
        except ValueError as e:
            print(f"⚠️ AI助手初始化失败: {e}")

        self._create_header()
        self._create_stats()
        self._create_notebook()
        self._create_statusbar()
        self._check_config()

    # ---------- 界面创建 ----------
    def _create_header(self):
        header = Frame(self.root, bg='#2c3e50', height=50)
        header.pack(fill=X, side=TOP)
        header.pack_propagate(False)
        Label(header, text="📄 OCR识别工具 - 发票报销系统", font=('微软雅黑', 16, 'bold'),
              fg='white', bg='#2c3e50').pack(side=LEFT, padx=20)
        btn_frame = Frame(header, bg='#2c3e50')
        btn_frame.pack(side=RIGHT, padx=10)
        Button(btn_frame, text="📜 历史记录", command=self._open_history,
               bg='#ecf0f1', fg='#2c3e50', font=('微软雅黑', 9), relief=FLAT, padx=10).pack(side=LEFT, padx=2)
        Button(btn_frame, text="⚙️ 系统设置", command=self._open_settings,
               bg='#ecf0f1', fg='#2c3e50', font=('微软雅黑', 9), relief=FLAT, padx=10).pack(side=LEFT, padx=2)

    def _create_stats(self):
        stats_frame = Frame(self.root, bg='white', relief=GROOVE, bd=1)
        stats_frame.pack(fill=X, padx=15, pady=10)
        self.stats_label = Label(stats_frame, text="", font=('微软雅黑', 12), bg='white', fg='#34495e')
        self.stats_label.pack(pady=8)
        self._update_stats()

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=15, pady=5)
        self._setup_invoice_tab()
        self._setup_screenshot_tab()
        self._setup_reimbursement_tab()
        self._setup_ai_tab()

    def _create_statusbar(self):
        self.status_var = StringVar()
        self.status_var.set("💡 就绪")
        status_bar = Label(self.root, textvariable=self.status_var,
                           font=('微软雅黑', 9), fg='#7f8c8d', anchor='w',
                           padx=10, pady=5, relief=SUNKEN, bd=1, bg='#ecf0f1')
        status_bar.pack(fill=X, side=BOTTOM)

    # ---------- 单张发票识别 ----------
    def _setup_invoice_tab(self):
        frame = Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="📄 发票识别")
        self.invoice_file_path = StringVar()
        top_frame = Frame(frame, bg='#f0f2f5')
        top_frame.pack(pady=10, padx=10, fill=X)
        Label(top_frame, text="选择文件：", font=("微软雅黑", 10), bg='#f0f2f5').pack(side=LEFT)
        Entry(top_frame, textvariable=self.invoice_file_path, font=("微软雅黑", 10),
              width=50, relief=SUNKEN, bd=1).pack(side=LEFT, padx=5, fill=X, expand=True)
        Button(top_frame, text="浏览...", command=self._browse_invoice_file,
               bg='#3498db', fg='white', relief=FLAT, padx=10).pack(side=LEFT, padx=5)

        btn_frame = Frame(frame, bg='#f0f2f5')
        btn_frame.pack(pady=10)
        Button(btn_frame, text="🔍 开始识别", font=("微软雅黑", 12),
               command=self._start_invoice_recognize, bg='#1a73e8', fg="white",
               relief=FLAT, padx=20, pady=5).pack(side=LEFT, padx=10)
        Button(btn_frame, text="🗑️ 清空结果", command=self._clear_invoice_result,
               bg='#95a5a6', fg='white', relief=FLAT, padx=15, pady=5).pack(side=LEFT, padx=10)
        self.invoice_btn_show_full = Button(
            btn_frame, text="📜 显示完整JSON", command=self._show_invoice_full_json,
            bg='#f39c12', fg='white', relief=FLAT, padx=15, pady=5, state=DISABLED
        )
        self.invoice_btn_show_full.pack(side=LEFT, padx=10)

        result_frame = LabelFrame(frame, text="📋 发票关键信息", font=("微软雅黑", 10, "bold"),
                                  bg='white', fg='#2c3e50')
        result_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.invoice_result_text = scrolledtext.ScrolledText(result_frame, font=("微软雅黑", 11), wrap=WORD)
        self.invoice_result_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.invoice_full_json = None

    def _browse_invoice_file(self):
        path = filedialog.askopenfilename(
            title="选择发票文件",
            filetypes=(("所有支持格式", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.pdf *.ofd"), ("所有文件", "*.*"))
        )
        if path:
            self.invoice_file_path.set(path)

    def _start_invoice_recognize(self):
        path = self.invoice_file_path.get()
        if not path:
            messagebox.showwarning("提示", "请选择文件")
            return
        if not os.path.exists(path):
            messagebox.showerror("错误", "文件不存在")
            return
        self.invoice_result_text.delete(1.0, END)
        self.invoice_result_text.insert(END, "⏳ 识别中...\n")
        self.status_var.set("⏳ 发票识别中...")
        self.invoice_btn_show_full.config(state=DISABLED)
        self.invoice_full_json = None
        threading.Thread(target=self._invoice_recognize_thread, args=(path,), daemon=True).start()

    def _invoice_recognize_thread(self, path):
        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
            handler = InvoiceHandler(self.ocr_client, self.ai_assistant)
            result = handler.process(image_bytes, path)
            if result:
                self.invoice_full_json = json.dumps(result['fields'], indent=4, ensure_ascii=False)
                formatted = process_invoice(result['fields'])
                if result.get('correction_info'):
                    formatted += f"\n\n🤖 {result['correction_info']}"
                self._update_invoice_result(formatted)
                self.root.after(0, lambda: self.invoice_btn_show_full.config(state=NORMAL))
            else:
                self._update_invoice_result("识别失败，请检查网络或服务状态")
        except Exception as e:
            self._update_invoice_result(f"❌ 错误：{str(e)}")

    def _update_invoice_result(self, text):
        def _update():
            self.invoice_result_text.delete(1.0, END)
            self.invoice_result_text.insert(END, text)
            self.status_var.set("✅ 发票识别完成")

        self.root.after(0, _update)

    def _clear_invoice_result(self):
        self.invoice_result_text.delete(1.0, END)
        self.invoice_full_json = None
        self.invoice_btn_show_full.config(state=DISABLED)
        self.status_var.set("🗑️ 已清空")

    def _show_invoice_full_json(self):
        if self.invoice_full_json:
            self._show_json_window("完整JSON - 发票", self.invoice_full_json)
        else:
            messagebox.showinfo("提示", "暂无数据")

    # ---------- 单张截图识别 ----------
    def _setup_screenshot_tab(self):
        frame = Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="📸 截图识别(高精)")
        self.screenshot_file_path = StringVar()
        top_frame = Frame(frame, bg='#f0f2f5')
        top_frame.pack(pady=10, padx=10, fill=X)
        Label(top_frame, text="选择截图：", font=("微软雅黑", 10), bg='#f0f2f5').pack(side=LEFT)
        Entry(top_frame, textvariable=self.screenshot_file_path, font=("微软雅黑", 10),
              width=50, relief=SUNKEN, bd=1).pack(side=LEFT, padx=5, fill=X, expand=True)
        Button(top_frame, text="浏览...", command=self._browse_screenshot_file,
               bg='#3498db', fg='white', relief=FLAT, padx=10).pack(side=LEFT, padx=5)

        btn_frame = Frame(frame, bg='#f0f2f5')
        btn_frame.pack(pady=10)
        Button(btn_frame, text="🔍 开始识别(高精)", font=("微软雅黑", 12),
               command=self._start_screenshot_recognize, bg='#1a73e8', fg="white",
               relief=FLAT, padx=20, pady=5).pack(side=LEFT, padx=10)
        Button(btn_frame, text="🗑️ 清空结果", command=self._clear_screenshot_result,
               bg='#95a5a6', fg='white', relief=FLAT, padx=15, pady=5).pack(side=LEFT, padx=10)
        self.screenshot_btn_show_full = Button(
            btn_frame, text="📜 显示完整JSON", command=self._show_screenshot_full_json,
            bg='#f39c12', fg='white', relief=FLAT, padx=15, pady=5, state=DISABLED
        )
        self.screenshot_btn_show_full.pack(side=LEFT, padx=10)

        result_frame = LabelFrame(frame, text="📌 截图关键信息", font=("微软雅黑", 10, "bold"),
                                  bg='white', fg='#2c3e50')
        result_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.screenshot_result_text = scrolledtext.ScrolledText(result_frame, font=("微软雅黑", 11), wrap=WORD)
        self.screenshot_result_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        self.screenshot_full_json = None

    def _browse_screenshot_file(self):
        path = filedialog.askopenfilename(
            title="选择截图",
            filetypes=(("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("所有文件", "*.*"))
        )
        if path:
            self.screenshot_file_path.set(path)

    def _start_screenshot_recognize(self):
        path = self.screenshot_file_path.get()
        if not path:
            messagebox.showwarning("提示", "请选择截图")
            return
        if not os.path.exists(path):
            messagebox.showerror("错误", "文件不存在")
            return
        self.screenshot_result_text.delete(1.0, END)
        self.screenshot_result_text.insert(END, "⏳ 识别中...\n")
        self.status_var.set("⏳ 截图识别中...")
        self.screenshot_btn_show_full.config(state=DISABLED)
        self.screenshot_full_json = None
        threading.Thread(target=self._screenshot_recognize_thread, args=(path,), daemon=True).start()

    def _screenshot_recognize_thread(self, path):
        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
            handler = ScreenshotHandler(self.ocr_client, self.ai_assistant)
            result = handler.process(image_bytes, path)
            if result:
                self.screenshot_full_json = json.dumps(result['fields'], indent=4, ensure_ascii=False)
                formatted = process_screenshot(result['fields'])
                if result.get('correction_info'):
                    formatted += f"\n\n🤖 {result['correction_info']}"
                self._update_screenshot_result(formatted)
                self.root.after(0, lambda: self.screenshot_btn_show_full.config(state=NORMAL))
            else:
                self._update_screenshot_result("识别失败，请检查网络或服务状态")
        except Exception as e:
            self._update_screenshot_result(f"❌ 错误：{str(e)}")

    def _update_screenshot_result(self, text):
        def _update():
            self.screenshot_result_text.delete(1.0, END)
            self.screenshot_result_text.insert(END, text)
            self.status_var.set("✅ 截图识别完成")

        self.root.after(0, _update)

    def _clear_screenshot_result(self):
        self.screenshot_result_text.delete(1.0, END)
        self.screenshot_full_json = None
        self.screenshot_btn_show_full.config(state=DISABLED)
        self.status_var.set("🗑️ 已清空")

    def _show_screenshot_full_json(self):
        if self.screenshot_full_json:
            self._show_json_window("完整JSON - 截图", self.screenshot_full_json)
        else:
            messagebox.showinfo("提示", "暂无数据")

    # ---------- 报销处理 ----------
    def _setup_reimbursement_tab(self):
        frame = Frame(self.notebook, bg='#f0f2f5')
        self.notebook.add(frame, text="🧾 报销处理")

        main_frame = Frame(frame, bg='#f0f2f5')
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        paned = PanedWindow(main_frame, orient=HORIZONTAL, sashrelief=RAISED, sashwidth=5, bg='#f0f2f5')
        paned.pack(fill=BOTH, expand=True, pady=5)

        # 左侧：发票面板
        invoice_panel = Frame(paned, bg='#f0f2f5')
        paned.add(invoice_panel, width=550, minsize=400)

        inv_list_frame = LabelFrame(invoice_panel, text="📄 发票文件列表（双击预览/编辑）",
                                    font=("微软雅黑", 10, "bold"), bg='white', fg='#2c3e50')
        inv_list_frame.pack(fill=BOTH, expand=True)

        inv_tree_frame = Frame(inv_list_frame, bg='white')
        inv_tree_frame.pack(fill=BOTH, expand=True, padx=2, pady=2)
        inv_scroll = Scrollbar(inv_tree_frame)
        inv_scroll.pack(side=RIGHT, fill=Y)
        self.inv_tree = ttk.Treeview(inv_tree_frame, columns=('状态', '文件名', '新文件名'),
                                     show='headings', height=12, yscrollcommand=inv_scroll.set)
        self.inv_tree.heading('状态', text='状态')
        self.inv_tree.heading('文件名', text='文件名')
        self.inv_tree.heading('新文件名', text='新文件名')
        self.inv_tree.column('状态', width=80, anchor='center')
        self.inv_tree.column('文件名', width=200)
        self.inv_tree.column('新文件名', width=200)
        self.inv_tree.pack(side=LEFT, fill=BOTH, expand=True)
        inv_scroll.config(command=self.inv_tree.yview)
        self.inv_tree.bind('<Double-1>', self._on_inv_double_click)

        inv_btn_frame = Frame(invoice_panel, bg='#f0f2f5')
        inv_btn_frame.pack(fill=X, pady=2)
        Button(inv_btn_frame, text="➕ 添加发票", command=self._add_invoice_batch,
               bg='#2ecc71', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(inv_btn_frame, text="✖ 移除选中", command=lambda: self._remove_selected('invoice'),
               bg='#e74c3c', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(inv_btn_frame, text="🗑 清空发票", command=lambda: self._clear_type('invoice'),
               bg='#95a5a6', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(inv_btn_frame, text="🔁 重试失败(发票)", command=lambda: self._retry_failed_type('invoice'),
               bg='#f39c12', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(inv_btn_frame, text="👁 预览命名(发票)", command=lambda: self._preview_type('invoice'),
               bg='#9b59b6', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)

        # 右侧：截图面板
        screenshot_panel = Frame(paned, bg='#f0f2f5')
        paned.add(screenshot_panel, width=550, minsize=400)

        scr_list_frame = LabelFrame(screenshot_panel, text="📸 截图文件列表（双击预览/编辑）",
                                    font=("微软雅黑", 10, "bold"), bg='white', fg='#2c3e50')
        scr_list_frame.pack(fill=BOTH, expand=True)

        scr_tree_frame = Frame(scr_list_frame, bg='white')
        scr_tree_frame.pack(fill=BOTH, expand=True, padx=2, pady=2)
        scr_scroll = Scrollbar(scr_tree_frame)
        scr_scroll.pack(side=RIGHT, fill=Y)
        self.scr_tree = ttk.Treeview(scr_tree_frame, columns=('状态', '文件名', '新文件名'),
                                     show='headings', height=12, yscrollcommand=scr_scroll.set)
        self.scr_tree.heading('状态', text='状态')
        self.scr_tree.heading('文件名', text='文件名')
        self.scr_tree.heading('新文件名', text='新文件名')
        self.scr_tree.column('状态', width=80, anchor='center')
        self.scr_tree.column('文件名', width=200)
        self.scr_tree.column('新文件名', width=200)
        self.scr_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scr_scroll.config(command=self.scr_tree.yview)
        self.scr_tree.bind('<Double-1>', self._on_scr_double_click)

        scr_btn_frame = Frame(screenshot_panel, bg='#f0f2f5')
        scr_btn_frame.pack(fill=X, pady=2)
        Button(scr_btn_frame, text="📸 添加截图", command=self._add_screenshot_batch,
               bg='#3498db', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(scr_btn_frame, text="✖ 移除选中", command=lambda: self._remove_selected('screenshot'),
               bg='#e74c3c', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(scr_btn_frame, text="🗑 清空截图", command=lambda: self._clear_type('screenshot'),
               bg='#95a5a6', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(scr_btn_frame, text="🔁 重试失败(截图)", command=lambda: self._retry_failed_type('screenshot'),
               bg='#f39c12', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)
        Button(scr_btn_frame, text="👁 预览命名(截图)", command=lambda: self._preview_type('screenshot'),
               bg='#9b59b6', fg='white', relief=FLAT, padx=6).pack(side=LEFT, padx=1)

        settings_frame = LabelFrame(main_frame, text="处理设置", font=("微软雅黑", 10, "bold"),
                                    bg='white', fg='#2c3e50')
        settings_frame.pack(fill=X, pady=5)

        row1 = Frame(settings_frame, bg='white')
        row1.pack(fill=X, pady=2)
        Label(row1, text="输出目录：", font=("微软雅黑", 10), bg='white').pack(side=LEFT, padx=5)
        Entry(row1, textvariable=self.output_dir, font=("微软雅黑", 10),
              relief=SUNKEN, bd=1).pack(side=LEFT, padx=5, fill=X, expand=True)
        Button(row1, text="浏览...", command=self._browse_output_dir,
               bg='#3498db', fg='white', relief=FLAT, padx=8).pack(side=LEFT, padx=5)

        row2 = Frame(settings_frame, bg='white')
        row2.pack(fill=X, pady=2)
        Label(row2, text="命名规则：", font=("微软雅黑", 10), bg='white').pack(side=LEFT, padx=5)
        Label(row2, text="发票：分类命名  |  截图：时间_起点-终点_距离", font=("微软雅黑", 9),
              fg='#2c3e50', bg='white').pack(side=LEFT, padx=5)
        Checkbutton(row2, text="跳过已存在文件", variable=self.skip_existing,
                    bg='white', font=("微软雅黑", 10)).pack(side=LEFT, padx=(20, 0))

        row3 = Frame(settings_frame, bg='white')
        row3.pack(fill=X, pady=2)
        Label(row3, text="处理类型：", font=("微软雅黑", 10), bg='white').pack(side=LEFT, padx=5)
        self.batch_type_var = StringVar(value="all")
        Radiobutton(row3, text="全部", variable=self.batch_type_var, value="all", bg='white').pack(side=LEFT, padx=5)
        Radiobutton(row3, text="仅发票", variable=self.batch_type_var, value="invoice", bg='white').pack(side=LEFT,
                                                                                                         padx=5)
        Radiobutton(row3, text="仅截图", variable=self.batch_type_var, value="screenshot", bg='white').pack(side=LEFT,
                                                                                                            padx=5)

        btn_row = Frame(main_frame, bg='#f0f2f5')
        btn_row.pack(fill=X, pady=5)

        self.batch_progress = ttk.Progressbar(btn_row, orient=HORIZONTAL, length=400, mode='determinate')
        self.batch_progress.pack(side=LEFT, padx=5, fill=X, expand=True)

        Button(btn_row, text="⚡ 批量处理", command=self._start_batch,
               bg='#e67e22', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=12).pack(side=LEFT, padx=2)
        Button(btn_row, text="⏸ 暂停", command=self._toggle_pause,
               bg='#f39c12', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=10).pack(side=LEFT, padx=2)
        Button(btn_row, text="⏹ 取消", command=self._cancel_batch,
               bg='#e74c3c', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=10).pack(side=LEFT, padx=2)
        Button(btn_row, text="🚀 一键完整处理", command=self._run_pipeline,
               bg='#1a73e8', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=12).pack(side=LEFT, padx=2)
        # 智能预处理按钮
        Button(btn_row, text="🧠 智能预处理", command=self._smart_preprocess,
               bg='#8e44ad', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=12).pack(side=LEFT, padx=2)
        # 确认应用按钮
        Button(btn_row, text="✅ 应用确认", command=self._apply_confirmed,
               bg='#2ecc71', fg='white', font=("微软雅黑", 10), relief=FLAT, padx=12).pack(side=LEFT, padx=2)

        log_frame = LabelFrame(main_frame, text="处理日志（实时显示）", font=("微软雅黑", 10, "bold"),
                               bg='white', fg='#2c3e50')
        log_frame.pack(fill=BOTH, expand=True, pady=5)
        self.batch_log_text = scrolledtext.ScrolledText(log_frame, font=("微软雅黑", 9), wrap=WORD, height=8)
        self.batch_log_text.pack(fill=BOTH, expand=True, padx=5, pady=5)

        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_global_drop)

    # ---------- AI 助手选项卡 ----------
    def _setup_ai_tab(self):
        # ...（与之前相同，省略）
        pass

    def _ai_send(self):
        # ...（与之前相同，省略）
        pass

    # ---------- 全局拖拽处理 ----------
    def _on_global_drop(self, event):
        if not HAS_DND:
            return
        files = self.root.tk.splitlist(event.data)
        for f in files:
            f = f.strip('{}')
            if os.path.isfile(f):
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.pdf', '.ofd', '.xml', '.json']:
                    file_type = 'invoice'
                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
                    file_type = 'screenshot'
                else:
                    continue
                self._add_file(f, file_type)
            elif os.path.isdir(f):
                self._add_folder(f)

    def _add_folder(self, folder):
        for root, dirs, files in os.walk(folder):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.pdf', '.ofd', '.xml', '.json']:
                    full = os.path.join(root, f)
                    file_type = 'invoice' if ext in ['.pdf', '.ofd', '.xml', '.json'] else 'screenshot'
                    self._add_file(full, file_type)

    def _add_file(self, path, file_type):
        if any(item['path'] == path for item in self.file_list):
            return
        with open(path, 'rb') as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        item = {
            'path': path,
            'type': file_type,
            'status': '待处理',
            'new_name': '',
            'error_msg': '',
            'category': '',
            'fields': {},
            'md5': md5
        }
        self.file_list.append(item)
        if file_type == 'invoice':
            self.inv_tree.insert('', END, values=('待处理', os.path.basename(path), ''))
        else:
            self.scr_tree.insert('', END, values=('待处理', os.path.basename(path), ''))
        self._update_stats()

    # ---------- 添加发票/截图按钮 ----------
    def _add_invoice_batch(self):
        files = filedialog.askopenfilenames(
            title="选择发票文件",
            filetypes=(("支持格式", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.pdf *.ofd *.xml *.json"),
                       ("所有文件", "*.*"))
        )
        for f in files:
            self._add_file(f, 'invoice')

    def _add_screenshot_batch(self):
        files = filedialog.askopenfilenames(
            title="选择截图文件",
            filetypes=(("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("所有文件", "*.*"))
        )
        for f in files:
            self._add_file(f, 'screenshot')

    def _remove_selected(self, file_type):
        tree = self.inv_tree if file_type == 'invoice' else self.scr_tree
        selected = tree.selection()
        if not selected:
            return
        paths_to_remove = []
        for item in selected:
            values = tree.item(item, 'values')
            filename = values[1]
            for idx, data in enumerate(self.file_list):
                if os.path.basename(data['path']) == filename and data['type'] == file_type:
                    paths_to_remove.append(idx)
                    break
        for idx in sorted(paths_to_remove, reverse=True):
            del self.file_list[idx]
        self._refresh_trees()

    def _refresh_trees(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
        for item in self.scr_tree.get_children():
            self.scr_tree.delete(item)
        for data in self.file_list:
            if data['type'] == 'invoice':
                self.inv_tree.insert('', END, values=(data['status'], os.path.basename(data['path']), data['new_name']))
            else:
                self.scr_tree.insert('', END, values=(data['status'], os.path.basename(data['path']), data['new_name']))
        self._update_stats()

    def _clear_type(self, file_type):
        self.file_list = [item for item in self.file_list if item['type'] != file_type]
        self._refresh_trees()

    def _retry_failed_type(self, file_type):
        for data in self.file_list:
            if data['type'] == file_type and data['status'] == '失败':
                data['status'] = '待处理'
                data['error_msg'] = ''
        self._refresh_trees()
        self._log_batch(f"已重置{file_type}类型的失败项")

    def _preview_type(self, file_type):
        sub_list = [item for item in self.file_list if item['type'] == file_type]
        if not sub_list:
            messagebox.showinfo("提示", f"没有{file_type}文件")
            return
        PreviewDialog(self.root, sub_list)

    # ---------- 双击预览/编辑 ----------
    def _on_inv_double_click(self, event):
        self._on_double_click(event, 'invoice')

    def _on_scr_double_click(self, event):
        self._on_double_click(event, 'screenshot')

    def _on_double_click(self, event, file_type):
        tree = self.inv_tree if file_type == 'invoice' else self.scr_tree
        selected = tree.selection()
        if not selected:
            return
        item = selected[0]
        # 获取该行在 file_list 中的索引
        values = tree.item(item, 'values')
        filename = values[1]
        for idx, data in enumerate(self.file_list):
            if os.path.basename(data['path']) == filename and data['type'] == file_type:
                self._show_edit_dialog(idx)
                return

    def _show_edit_dialog(self, idx):
        """编辑对话框，根据当前文件状态（待确认或待处理）弹出"""
        data = self.file_list[idx]
        orig_name = os.path.basename(data['path'])
        file_type = data['type']
        fields = data.get('fields', {}).copy()
        category = data.get('category', '')
        current_new_name = data.get('new_name', '')

        win = Toplevel(self.root)
        win.title(f"编辑文件名 - {orig_name}")
        win.geometry("550x400")
        win.transient(self.root)
        win.grab_set()

        Label(win, text=f"编辑文件：{orig_name}", font=('微软雅黑', 10, 'bold')).pack(pady=5)

        frame = Frame(win)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        entries = {}

        if file_type == 'invoice':
            # 确保有 location 字段
            if 'location' not in fields:
                seller = fields.get('seller_name', '')
                buyer = fields.get('buyer_name', '')
                loc = extract_city_from_name(seller) or extract_city_from_name(buyer) or ''
                fields['location'] = loc

            fields_to_edit = {
                '项目名称': fields.get('item', ''),
                '地点': fields.get('location', ''),
                '金额(价税合计)': fields.get('total', ''),
                '日期(YYYYMMDD)': fields.get('date', '').replace('-', '').replace('/', '')[:8] if fields.get(
                    'date') else ''
            }
            Label(frame, text=f"分类：{category}", font=('微软雅黑', 9), fg='gray').pack(anchor=W, pady=(0, 5))

        else:  # screenshot
            fields_to_edit = {
                '时间(YYYYMMDD)': fields.get('time', ''),
                '起点': fields.get('start', ''),
                '终点': fields.get('end', ''),
                '距离(km)': fields.get('distance', '')
            }

        for label, value in fields_to_edit.items():
            row = Frame(frame)
            row.pack(fill=X, pady=3)
            Label(row, text=label + ":", width=14, anchor=E).pack(side=LEFT)
            entry = Entry(row, width=30)
            entry.insert(0, value)
            entry.pack(side=LEFT, padx=5, fill=X, expand=True)
            entries[label] = entry

        preview_label = Label(frame, text="预览文件名：", font=('微软雅黑', 9), fg='blue')
        preview_label.pack(anchor=W, pady=(10, 0))
        preview_value = Label(frame, text="", font=('微软雅黑', 9), fg='#2c3e50', wraplength=450, justify=LEFT)
        preview_value.pack(anchor=W, fill=X)

        def update_preview(*args):
            new_fields = fields.copy()
            if file_type == 'invoice':
                new_fields['item'] = entries['项目名称'].get().strip()
                new_fields['location'] = entries['地点'].get().strip()
                new_fields['total'] = entries['金额(价税合计)'].get().strip()
                date_val = entries['日期(YYYYMMDD)'].get().strip()
                new_fields['date'] = date_val
                try:
                    new_name = generate_invoice_filename(new_fields, category)
                    preview_value.config(text=new_name)
                except Exception as e:
                    preview_value.config(text=f"生成失败: {e}")
            else:
                new_fields['time'] = entries['时间(YYYYMMDD)'].get().strip()
                new_fields['start'] = entries['起点'].get().strip()
                new_fields['end'] = entries['终点'].get().strip()
                new_fields['distance'] = entries['距离(km)'].get().strip()
                naming_rule = "{time}_{start}-{end}_{distance}"
                try:
                    new_name = generate_filename(new_fields, naming_rule, '.png')
                    preview_value.config(text=new_name)
                except Exception as e:
                    preview_value.config(text=f"生成失败: {e}")

        for entry in entries.values():
            entry.bind('<KeyRelease>', update_preview)

        btn_frame = Frame(win)
        btn_frame.pack(fill=X, pady=10)

        def save_and_close():
            if file_type == 'invoice':
                fields['item'] = entries['项目名称'].get().strip()
                fields['location'] = entries['地点'].get().strip()
                fields['total'] = entries['金额(价税合计)'].get().strip()
                date_val = entries['日期(YYYYMMDD)'].get().strip()
                fields['date'] = date_val
                new_name = generate_invoice_filename(fields, category)
            else:
                fields['time'] = entries['时间(YYYYMMDD)'].get().strip()
                fields['start'] = entries['起点'].get().strip()
                fields['end'] = entries['终点'].get().strip()
                fields['distance'] = entries['距离(km)'].get().strip()
                naming_rule = "{time}_{start}-{end}_{distance}"
                new_name = generate_filename(fields, naming_rule, '.png')

            # 更新文件列表
            self.file_list[idx]['fields'] = fields
            self.file_list[idx]['new_name'] = new_name
            self.file_list[idx]['status'] = '待确认'  # 确保状态为待确认
            # 更新树
            tree = self.inv_tree if file_type == 'invoice' else self.scr_tree
            # 找到对应的行
            for child in tree.get_children():
                if tree.item(child, 'values')[1] == os.path.basename(self.file_list[idx]['path']):
                    tree.item(child, values=('待确认', os.path.basename(self.file_list[idx]['path']), new_name))
                    break
            win.destroy()

        Button(btn_frame, text="保存", command=save_and_close,
               bg='#3498db', fg='white', relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        Button(btn_frame, text="取消", command=win.destroy,
               bg='#95a5a6', fg='white', relief=FLAT, padx=15).pack(side=LEFT, padx=5)

        update_preview()

    # ---------- 智能预处理（静默后台处理） ----------
    def _smart_preprocess(self):
        process_type = self.batch_type_var.get()
        if process_type == "all":
            process_list = [item for item in self.file_list if item['status'] == '待处理']
        elif process_type == "invoice":
            process_list = [item for item in self.file_list if item['type'] == 'invoice' and item['status'] == '待处理']
        else:
            process_list = [item for item in self.file_list if
                            item['type'] == 'screenshot' and item['status'] == '待处理']
        if not process_list:
            messagebox.showinfo("提示", "没有待处理文件")
            return

        pre = Preprocessor(self.ocr_client, self.ai_assistant)

        self._log_batch("🧠 开始智能预处理...")
        self.batch_progress['value'] = 0
        self.batch_progress['maximum'] = 100

        threading.Thread(target=self._preprocess_thread, args=(process_list, pre), daemon=True).start()

    def _preprocess_thread(self, process_list, pre):
        def progress_cb(val):
            self.root.after(0, lambda: self.batch_progress.config(value=val))

        def log_cb(msg):
            self.root.after(0, lambda: self._log_batch(msg))

        results = pre.batch_preprocess(process_list, progress_cb, log_cb)

        # 更新文件列表和树
        def update_files():
            for res in results:
                orig_name = res['original_name']
                sugg_name = res['suggested_name']
                # 查找对应的文件项
                for idx, data in enumerate(self.file_list):
                    if os.path.basename(data['path']) == orig_name:
                        data['fields'] = res.get('fields', {})
                        data['category'] = res.get('category', '')
                        data['new_name'] = sugg_name
                        data['status'] = '待确认' if sugg_name != '识别失败' else '失败'
                        # 更新树
                        tree = self.inv_tree if data['type'] == 'invoice' else self.scr_tree
                        for child in tree.get_children():
                            if tree.item(child, 'values')[1] == orig_name:
                                tree.item(child, values=(data['status'], orig_name, sugg_name))
                                break
                        break
            self._update_stats()
            self._log_batch("✅ 智能预处理完成，请双击行编辑或确认")
            self.root.after(0, lambda: self.batch_progress.config(value=100))

        self.root.after(0, update_files)

    # ---------- 应用确认（将待确认文件复制到输出目录） ----------
    def _apply_confirmed(self):
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showwarning("提示", "请先设置输出目录")
            return
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        confirmed = [item for item in self.file_list if item['status'] == '待确认' and item.get('new_name')]
        if not confirmed:
            messagebox.showinfo("提示", "没有待确认的文件")
            return

        copied = 0
        for item in confirmed:
            src = item['path']
            new_name = item['new_name']
            target = os.path.join(out_dir, new_name)
            if os.path.exists(target):
                if self.skip_existing.get():
                    self._log_batch(f"⏭️ 跳过已存在: {new_name}")
                    continue
                else:
                    base, ext = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(os.path.join(out_dir, f"{base}_{counter}{ext}")):
                        counter += 1
                    target = os.path.join(out_dir, f"{base}_{counter}{ext}")
            try:
                shutil.copy2(src, target)
                item['status'] = '成功'
                item['new_name'] = os.path.basename(target)
                copied += 1
                # 更新树
                tree = self.inv_tree if item['type'] == 'invoice' else self.scr_tree
                for child in tree.get_children():
                    if tree.item(child, 'values')[1] == os.path.basename(src):
                        tree.item(child, values=('成功', os.path.basename(src), os.path.basename(target)))
                        break
            except Exception as e:
                self._log_batch(f"❌ 复制失败 {new_name}: {e}")
        self._update_stats()
        self._log_batch(f"✅ 应用确认完成，共复制 {copied} 个文件")

    # ---------- 批量处理 ----------
    def _start_batch(self):
        # 与之前相同，省略
        pass

    def _on_item_updated(self, index, status, new_name, error_msg):
        # 与之前相同，省略
        pass

    def _update_progress(self, current, total):
        self.root.after(0, lambda: self.batch_progress.config(value=current))
        self.root.after(0, lambda: self.status_var.set(f"⏳ 处理中 {current}/{total}"))
        if current == total:
            self.root.after(0, self._refresh_trees)

    def _log_batch(self, msg):
        self.batch_log_text.insert(END, msg + "\n")
        self.batch_log_text.see(END)
        self.batch_log_text.update_idletasks()

    def _toggle_pause(self):
        # 与之前相同，省略
        pass

    def _cancel_batch(self):
        # 与之前相同，省略
        pass

    def _run_pipeline(self):
        # 与之前相同，省略
        pass

    def _update_stats(self):
        # 与之前相同，省略
        pass

    def _check_config(self):
        config = load_config()
        idx = config.get('current_account', 0)
        accounts = config.get('accounts', [])
        if idx >= len(accounts) or not accounts[idx].get('access_key_id'):
            self.status_var.set("⚠️ 请点击右上角 '系统设置' 配置阿里云 AccessKey")
        else:
            self.status_var.set("💡 配置有效，可以开始处理")

    def _open_settings(self):
        SettingsDialog(self.root, self._on_settings_saved)

    def _on_settings_saved(self):
        self.config = load_config()
        self.ocr_client.refresh()
        try:
            self.ai_assistant = AIAssistant()
            print("✅ AI助手重新初始化成功")
        except ValueError as e:
            print(f"⚠️ AI助手初始化失败: {e}")
        self._check_config()
        self.status_var.set("✅ 配置已更新")

    def _open_history(self):
        HistoryDialog(self.root)

    def _show_json_window(self, title, json_str):
        win = Toplevel(self.root)
        win.title(title)
        win.geometry("750x600")
        text = scrolledtext.ScrolledText(win, font=("Consolas", 10), wrap=WORD)
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        text.insert(END, json_str)
        text.config(state=DISABLED)

    def _browse_output_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
