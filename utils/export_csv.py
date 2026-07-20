# -*- coding: utf-8 -*-
import csv
import os
from tkinter import filedialog, messagebox


def export_to_csv(file_list):
    if not file_list:
        messagebox.showinfo("提示", "列表为空")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV文件", "*.csv")])
    if not file_path:
        return
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['原文件名', '类型', '状态', '新文件名', '发票号码', '开票日期', '项目名称', '金额', '分类'])
            for item in file_list:
                fields = item.get('fields', {})
                writer.writerow([
                    os.path.basename(item['path']),
                    item['type'],
                    item['status'],
                    item['new_name'],
                    fields.get('number', ''),
                    fields.get('date', ''),
                    fields.get('item', ''),
                    fields.get('amount', ''),
                    item.get('category', '')
                ])
        messagebox.showinfo("完成", f"导出成功！\n{file_path}")
    except Exception as e:
        messagebox.showerror("错误", f"导出失败: {str(e)}")
