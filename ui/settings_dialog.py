# -*- coding: utf-8 -*-
"""设置对话框（精简版 - 仅账号管理和其他设置）"""

from tkinter import *
from tkinter import ttk, messagebox

from utils.settings import load_config, save_config


class SettingsDialog:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.config = load_config()
        self.win = Toplevel(parent)
        self.win.title("系统设置")
        self.win.geometry("600x450")
        self.win.configure(bg='#f0f2f5')
        self.win.transient(parent)
        self.win.grab_set()
        self._create_widgets()

    def _create_widgets(self):
        notebook = ttk.Notebook(self.win)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 账号管理
        acc_frame = Frame(notebook, bg='#f0f2f5')
        notebook.add(acc_frame, text="账号管理")
        self._setup_account_tab(acc_frame)

        # 其他设置（含智谱 API Key）
        other_frame = Frame(notebook, bg='#f0f2f5')
        notebook.add(other_frame, text="其他设置")
        self._setup_other_tab(other_frame)

        btn_frame = Frame(self.win, bg='#f0f2f5')
        btn_frame.pack(fill=X, pady=10)
        Button(btn_frame, text="保存", command=self._save,
               bg='#3498db', fg='white', relief=FLAT, padx=20).pack(side=RIGHT, padx=5)
        Button(btn_frame, text="取消", command=self.win.destroy,
               bg='#95a5a6', fg='white', relief=FLAT, padx=20).pack(side=RIGHT, padx=5)

    # ---------- 账号管理 ----------
    def _setup_account_tab(self, parent):
        Label(parent, text="账号列表（点击切换）", bg='#f0f2f5', font=('微软雅黑', 10, 'bold')).pack(anchor=W, pady=5)
        self.acc_listbox = Listbox(parent, height=4, selectmode=SINGLE)
        self.acc_listbox.pack(fill=X, pady=5)
        for idx, acc in enumerate(self.config.get('accounts', [])):
            self.acc_listbox.insert(END, f"{acc.get('name')} ({acc.get('region')})")
        if self.config.get('current_account', 0) < self.acc_listbox.size():
            self.acc_listbox.selection_set(self.config.get('current_account', 0))

        frame = Frame(parent, bg='#f0f2f5')
        frame.pack(fill=X, pady=5)
        Button(frame, text="添加账号", command=self._add_account, bg='#2ecc71', fg='white', relief=FLAT).pack(side=LEFT,
                                                                                                              padx=2)
        Button(frame, text="删除账号", command=self._del_account, bg='#e74c3c', fg='white', relief=FLAT).pack(side=LEFT,
                                                                                                              padx=2)

        Label(parent, text="当前账号详情", bg='#f0f2f5', font=('微软雅黑', 10, 'bold')).pack(anchor=W, pady=5)
        row1 = Frame(parent, bg='#f0f2f5')
        row1.pack(fill=X, pady=2)
        Label(row1, text="名称:", bg='#f0f2f5', width=8).pack(side=LEFT)
        self.acc_name = Entry(row1, width=30)
        self.acc_name.pack(side=LEFT, fill=X, expand=True)

        row2 = Frame(parent, bg='#f0f2f5')
        row2.pack(fill=X, pady=2)
        Label(row2, text="AccessKey ID:", bg='#f0f2f5', width=8).pack(side=LEFT)
        self.acc_ak = Entry(row2, width=30)
        self.acc_ak.pack(side=LEFT, fill=X, expand=True)

        row3 = Frame(parent, bg='#f0f2f5')
        row3.pack(fill=X, pady=2)
        Label(row3, text="Secret:", bg='#f0f2f5', width=8).pack(side=LEFT)
        self.acc_sk = Entry(row3, width=30, show='*')
        self.acc_sk.pack(side=LEFT, fill=X, expand=True)

        row4 = Frame(parent, bg='#f0f2f5')
        row4.pack(fill=X, pady=2)
        Label(row4, text="Region:", bg='#f0f2f5', width=8).pack(side=LEFT)
        self.acc_region = ttk.Combobox(row4,
                                       values=['cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen', 'cn-chengdu'],
                                       width=28)
        self.acc_region.pack(side=LEFT, fill=X, expand=True)

        self.acc_listbox.bind('<<ListboxSelect>>', self._on_acc_select)
        if self.acc_listbox.size() > 0:
            self.acc_listbox.selection_set(0)
            self._on_acc_select(None)

    def _on_acc_select(self, event):
        sel = self.acc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        acc = self.config.get('accounts', [])[idx]
        self.acc_name.delete(0, END)
        self.acc_name.insert(0, acc.get('name', ''))
        self.acc_ak.delete(0, END)
        self.acc_ak.insert(0, acc.get('access_key_id', ''))
        self.acc_sk.delete(0, END)
        self.acc_sk.insert(0, acc.get('access_key_secret', ''))
        self.acc_region.set(acc.get('region', 'cn-hangzhou'))

    def _add_account(self):
        self.config.setdefault('accounts', []).append(
            {'name': '新账号', 'access_key_id': '', 'access_key_secret': '', 'region': 'cn-hangzhou'})
        self.acc_listbox.insert(END, "新账号 (cn-hangzhou)")
        self.acc_listbox.selection_clear(0, END)
        self.acc_listbox.selection_set(len(self.config['accounts']) - 1)
        self._on_acc_select(None)

    def _del_account(self):
        sel = self.acc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if len(self.config['accounts']) <= 1:
            messagebox.showwarning("提示", "至少保留一个账号")
            return
        del self.config['accounts'][idx]
        self.acc_listbox.delete(idx)
        if idx >= len(self.config['accounts']):
            idx = len(self.config['accounts']) - 1
        self.acc_listbox.selection_set(idx)
        self._on_acc_select(None)

    # ---------- 其他设置 ----------
    def _setup_other_tab(self, parent):
        # 并发数
        row1 = Frame(parent, bg='#f0f2f5')
        row1.pack(fill=X, pady=5)
        Label(row1, text="并发处理数:", bg='#f0f2f5').pack(side=LEFT)
        self.concurrency = StringVar(value=str(self.config.get('concurrency', 3)))
        Entry(row1, textvariable=self.concurrency, width=5).pack(side=LEFT, padx=5)

        # 历史记录
        row2 = Frame(parent, bg='#f0f2f5')
        row2.pack(fill=X, pady=5)
        self.history_var = BooleanVar(value=self.config.get('history_enabled', True))
        Checkbutton(row2, text="启用历史记录", variable=self.history_var, bg='#f0f2f5').pack(anchor=W)

        # 自动归档（保留但用户可关，因为AI会处理归档，但这里保留开关）
        row3 = Frame(parent, bg='#f0f2f5')
        row3.pack(fill=X, pady=5)
        self.archive_var = BooleanVar(value=self.config.get('auto_archive', False))
        Checkbutton(row3, text="启用自动归档", variable=self.archive_var, bg='#f0f2f5').pack(anchor=W)

        # 主题
        row4 = Frame(parent, bg='#f0f2f5')
        row4.pack(fill=X, pady=5)
        self.theme_var = StringVar(value=self.config.get('theme', 'light'))
        Label(row4, text="主题:", bg='#f0f2f5').pack(side=LEFT)
        ttk.Combobox(row4, textvariable=self.theme_var, values=['light', 'dark'], width=10).pack(side=LEFT, padx=5)

        # 命名预览
        row5 = Frame(parent, bg='#f0f2f5')
        row5.pack(fill=X, pady=5)
        self.preview_var = BooleanVar(value=self.config.get('preview_enabled', True))
        Checkbutton(row5, text="启用命名预览", variable=self.preview_var, bg='#f0f2f5').pack(anchor=W)

        # 智谱 API Key
        row6 = Frame(parent, bg='#f0f2f5')
        row6.pack(fill=X, pady=5)
        Label(row6, text="智谱 API Key:", bg='#f0f2f5').pack(side=LEFT)
        self.zai_api_key = Entry(row6, width=50, relief=SUNKEN, bd=1, show='*')
        self.zai_api_key.pack(side=LEFT, padx=5, fill=X, expand=True)
        self.zai_api_key.insert(0, self.config.get('zai_api_key', ''))

        # 提示
        Label(parent, text="💡 智谱 API Key 可从 https://open.bigmodel.cn 获取，格式示例: xxxxxx.yyyyyy",
              font=('微软雅黑', 9), fg='#95a5a6', bg='#f0f2f5').pack(anchor=W, pady=(0, 5))

    # ---------- 保存 ----------
    def _save(self):
        # 保存账号
        sel = self.acc_listbox.curselection()
        if sel:
            idx = sel[0]
            acc = self.config['accounts'][idx]
            acc['name'] = self.acc_name.get().strip() or '默认账号'
            acc['access_key_id'] = self.acc_ak.get().strip()
            acc['access_key_secret'] = self.acc_sk.get().strip()
            acc['region'] = self.acc_region.get().strip()
            self.config['current_account'] = idx

        # 其他设置
        try:
            self.config['concurrency'] = int(self.concurrency.get())
        except:
            self.config['concurrency'] = 3
        self.config['history_enabled'] = self.history_var.get()
        self.config['auto_archive'] = self.archive_var.get()
        self.config['theme'] = self.theme_var.get()
        self.config['preview_enabled'] = self.preview_var.get()
        self.config['zai_api_key'] = self.zai_api_key.get().strip()

        save_config(self.config)
        self.win.destroy()
        if self.callback:
            self.callback()
