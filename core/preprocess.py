# -*- coding: utf-8 -*-
"""智能预处理模块：批量识别、AI建议、用户确认"""

import os

from core.ai_assistant import AIAssistant
from core.invoice_handler import InvoiceHandler
from core.ocr_client import OCRClient
from core.screenshot_handler import ScreenshotHandler


class Preprocessor:
    def __init__(self, ocr_client=None, ai_assistant=None):
        self.ocr_client = ocr_client or OCRClient()
        self.ai_assistant = ai_assistant or AIAssistant()
        self.invoice_handler = InvoiceHandler(self.ocr_client, self.ai_assistant)
        self.screenshot_handler = ScreenshotHandler(self.ocr_client, self.ai_assistant)

    def process_file(self, file_path):
        """处理单个文件，根据扩展名决定调用哪个处理器"""
        try:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
        except:
            return None

        ext = os.path.splitext(file_path)[1].lower()
        # 发票文件扩展名
        invoice_exts = ['.pdf', '.ofd', '.xml', '.json']
        # 截图文件扩展名
        screenshot_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp']

        result = None
        if ext in invoice_exts:
            # PDF/OFD/XML/JSON 当作发票处理
            result = self.invoice_handler.process(image_bytes, file_path)
        elif ext in screenshot_exts:
            # 图片格式当作截图处理
            result = self.screenshot_handler.process(image_bytes, file_path)
        else:
            # 其他格式不支持
            return {
                'type': 'error',
                'original_name': os.path.basename(file_path),
                'suggested_name': '不支持的文件格式',
                'fields': {},
                'correction_info': f'文件格式 {ext} 不支持'
            }

        if result:
            return {
                'type': 'invoice' if ext in invoice_exts else 'screenshot',
                'original_name': os.path.basename(file_path),
                'suggested_name': result['new_name'],
                'fields': result['fields'],
                'category': result.get('category', ''),
                'correction_info': result.get('correction_info', '')
            }
        else:
            return {
                'type': 'error',
                'original_name': os.path.basename(file_path),
                'suggested_name': '识别失败',
                'fields': {},
                'correction_info': 'OCR未识别到有效信息'
            }

    def batch_preprocess(self, file_list, progress_callback, log_callback):
        """批量预处理，返回结果列表"""
        results = []
        total = len(file_list)
        for idx, item in enumerate(file_list):
            log_callback(f"⏳ 处理 {idx + 1}/{total}: {os.path.basename(item['path'])}")
            res = self.process_file(item['path'])
            if res:
                results.append(res)
            else:
                results.append({
                    'type': 'error',
                    'original_name': os.path.basename(item['path']),
                    'suggested_name': '识别失败',
                    'fields': {},
                    'correction_info': 'OCR未识别到有效信息'
                })
            progress_callback((idx + 1) / total * 100)
        return results
