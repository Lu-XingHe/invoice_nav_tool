# -*- coding: utf-8 -*-
"""发票处理模块：识别、分类、生成文件名，AI自动修正后重命名"""

import os

from core.field_utils import extract_invoice_fields
from core.invoice_classifier import classify_invoice, generate_invoice_filename
from core.ocr_client import OCRClient


class InvoiceHandler:
    def __init__(self, ocr_client=None, ai_assistant=None):
        self.ocr_client = ocr_client or OCRClient()
        self.ai_assistant = ai_assistant

    def process(self, image_bytes, file_path):
        # 判断文件类型，非发票文件直接返回 None
        ext = os.path.splitext(file_path)[1].lower()
        # 发票识别支持的格式：PNG、JPG、JPEG、BMP、GIF、TIFF、WebP、PDF、OFD
        supported_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp', '.pdf', '.ofd']
        if ext not in supported_extensions:
            return None

        result = self.ocr_client.recognize_invoice(image_bytes)
        if not result:
            return None

        fields = extract_invoice_fields(result)
        category = classify_invoice(fields)

        # 先用原始字段生成初始文件名（用于AI上下文）
        initial_name = generate_invoice_filename(fields, category)

        # AI 自动修正
        ai_corrected = None
        correction_info = ""
        if self.ai_assistant:
            try:
                ai_corrected = self.ai_assistant.auto_correct_invoice_fields(fields, category, initial_name)
                correction_info = "AI已自动修正字段"
                # 使用修正后的字段
                fields = ai_corrected
            except Exception as e:
                correction_info = f"AI修正失败，使用原始字段 ({e})"

        # 重新生成文件名
        new_name = generate_invoice_filename(fields, category)

        return {
            'fields': fields,
            'category': category,
            'new_name': new_name,
            'correction_info': correction_info
        }
