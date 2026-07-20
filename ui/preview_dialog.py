# -*- coding: utf-8 -*-
"""命名预览对话框"""

import os
from tkinter import *
from tkinter import scrolledtext


class PreviewDialog:
    def __init__(self, parent, file_list):
        self.win = Toplevel(parent)
        self.win.title("命名预览")
        self.win.geometry("600x400")
        self._create_widgets(file_list)

    def _create_widgets(self, file_list):
        text = scrolledtext.ScrolledText(self.win, font=("Consolas", 10), wrap=WORD)
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        text.insert(END, "预览文件名（根据固定规则）:\n\n")
        for item in file_list[:20]:
            # 如果已有新文件名（说明已处理），直接显示
            if item.get('new_name'):
                text.insert(END, f"✅ {os.path.basename(item['path'])} -> {item['new_name']}\n")
            else:
                text.insert(END, f"⏳ {os.path.basename(item['path'])} -> 尚未识别，无法预览\n")
        if len(file_list) > 20:
            text.insert(END, f"\n... 共 {len(file_list)} 项，仅显示前20项")
