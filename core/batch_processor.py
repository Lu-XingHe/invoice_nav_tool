# -*- coding: utf-8 -*-
"""批量处理核心（并发、OCR、分类、归档、重命名 + AI自动修正）"""

import os
import queue
import shutil
import threading
import time
from datetime import datetime

from core.invoice_handler import InvoiceHandler
from core.screenshot_handler import ScreenshotHandler
from utils.settings import load_config, add_history_record


class BatchProcessor:
    def __init__(self, file_list, output_dir, skip_existing,
                 progress_callback, log_callback, stats_callback,
                 item_update_callback=None, ocr_client=None, ai_assistant=None):
        self.file_list = file_list
        self.output_dir = output_dir
        self.skip_existing = skip_existing
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.stats_callback = stats_callback
        self.item_update_callback = item_update_callback
        self.ocr_client = ocr_client
        self.ai_assistant = ai_assistant
        self.config = load_config()
        self.total_amount = 0.0
        self.pause_flag = False
        self.cancel_flag = False
        self.is_running = False
        self.work_thread = None

        self.invoice_handler = InvoiceHandler(ocr_client, ai_assistant)
        self.screenshot_handler = ScreenshotHandler(ocr_client, ai_assistant)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.pause_flag = False
        self.cancel_flag = False
        self.work_thread = threading.Thread(target=self._worker, daemon=True)
        self.work_thread.start()

    def toggle_pause(self):
        self.pause_flag = not self.pause_flag
        return self.pause_flag

    def cancel(self):
        self.cancel_flag = True
        if self.work_thread and self.work_thread.is_alive():
            self.work_thread.join(0.1)
        self.is_running = False

    def _worker(self):
        total = len(self.file_list)
        out_dir = self.output_dir
        concurrency = self.config.get('concurrency', 3)

        if total == 0:
            self.log_callback("⚠️ 没有待处理的文件。")
            self.is_running = False
            self.progress_callback(0, total)
            return

        task_queue = queue.Queue()
        for idx in range(total):
            task_queue.put(idx)

        self.progress_callback(0, total)
        completed = 0

        def worker():
            nonlocal completed
            while True:
                if self.cancel_flag:
                    break
                if self.pause_flag:
                    time.sleep(0.5)
                    continue
                try:
                    idx = task_queue.get(timeout=1)
                except queue.Empty:
                    break
                self._process_item(idx, out_dir)
                completed += 1
                self.progress_callback(completed, total)

        threads = []
        for _ in range(concurrency):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.is_running = False
        if self.config.get('history_enabled', True):
            success_count = sum(1 for item in self.file_list if item['status'] == '成功')
            failed_count = sum(1 for item in self.file_list if item['status'] == '失败')
            add_history_record({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files_count': total,
                'success_count': success_count,
                'failed_count': failed_count,
                'output_dir': out_dir,
                'details': [{'file': os.path.basename(item['path']), 'status': item['status'],
                             'new_name': item['new_name']} for item in self.file_list]
            })

    def _process_item(self, idx, out_dir):
        item = self.file_list[idx]
        try:
            with open(item['path'], 'rb') as f:
                image_bytes = f.read()

            if item['type'] == 'invoice':
                result = self.invoice_handler.process(image_bytes, item['path'])
                if not result:
                    self._update_item(idx, '失败', '', "OCR 返回空结果")
                    self.log_callback(f"❌ 失败: {os.path.basename(item['path'])} - OCR 返回空结果")
                    return
                fields = result['fields']
                category = result['category']
                new_name = result['new_name']
                item['category'] = category
                if result.get('correction_info'):
                    self.log_callback(f"🤖 {result['correction_info']}")
            else:
                result = self.screenshot_handler.process(image_bytes, item['path'])
                if not result:
                    self._update_item(idx, '失败', '', "OCR 返回空结果")
                    self.log_callback(f"❌ 失败: {os.path.basename(item['path'])} - OCR 返回空结果")
                    return
                fields = result['fields']
                new_name = result['new_name']
                category = ''
                if result.get('correction_info'):
                    self.log_callback(f"🤖 {result['correction_info']}")

            item['fields'] = fields

            target_dir = out_dir
            if self.config.get('auto_archive', False) and category:
                for rule in self.config.get('archive_rules', []):
                    if rule.get('category') == category:
                        target_dir = os.path.join(out_dir, rule.get('folder', category))
                        break
                else:
                    target_dir = os.path.join(out_dir, category)
                os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, new_name)
            item['new_name'] = new_name

            if os.path.exists(target_path):
                if self.skip_existing:
                    self._update_item(idx, '已跳过', new_name, "文件已存在")
                    self.log_callback(f"⏭️ 跳过: {os.path.basename(item['path'])} -> {new_name} (文件已存在)")
                    return
                else:
                    base, ext2 = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(os.path.join(target_dir, f"{base}_{counter}{ext2}")):
                        counter += 1
                    new_name = f"{base}_{counter}{ext2}"
                    item['new_name'] = new_name
                    target_path = os.path.join(target_dir, new_name)

            shutil.copy2(item['path'], target_path)
            self._update_item(idx, '成功', new_name, "")
            self.log_callback(f"✅ 成功: {os.path.basename(item['path'])} -> {new_name}")

            if item['type'] == 'invoice':
                amount_str = fields.get('amount', '').replace('元', '').strip()
                try:
                    amount = float(amount_str)
                    self.total_amount += amount
                except:
                    pass

        except Exception as e:
            self._update_item(idx, '失败', '', str(e))
            self.log_callback(f"❌ 失败: {os.path.basename(item['path'])} - {str(e)}")

    def _update_item(self, index, status, new_name, error_msg):
        item = self.file_list[index]
        item['status'] = status
        item['new_name'] = new_name
        item['error_msg'] = error_msg
        if self.item_update_callback:
            self.item_update_callback(index, status, new_name, error_msg)
