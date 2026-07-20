# -*- coding: utf-8 -*-
from tkinter import *
from tkinter import ttk

from utils.settings import load_history


class HistoryDialog:
    def __init__(self, parent):
        self.win = Toplevel(parent)
        self.win.title("历史记录")
        self.win.geometry("800x500")
        self.win.configure(bg='#f0f2f5')
        self._create_widgets()

    def _create_widgets(self):
        tree = ttk.Treeview(self.win, columns=('时间', '文件数', '成功', '失败', '输出目录'), show='headings')
        tree.heading('时间', text='时间')
        tree.heading('文件数', text='文件数')
        tree.heading('成功', text='成功')
        tree.heading('失败', text='失败')
        tree.heading('输出目录', text='输出目录')
        tree.column('时间', width=180)
        tree.column('文件数', width=80)
        tree.column('成功', width=80)
        tree.column('失败', width=80)
        tree.column('输出目录', width=300)
        tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        history = load_history()
        for rec in reversed(history):
            tree.insert('', END, values=(
                rec.get('time', ''),
                rec.get('files_count', 0),
                rec.get('success_count', 0),
                rec.get('failed_count', 0),
                rec.get('output_dir', '')
            ))

        Button(self.win, text="关闭", command=self.win.destroy, bg='#3498db', fg='white', relief=FLAT, padx=20).pack(
            pady=10)
