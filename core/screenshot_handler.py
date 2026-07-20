# -*- coding: utf-8 -*-
"""截图处理模块：识别、生成文件名，AI自动修正后重命名"""

import os
import re
from datetime import datetime

from core.field_utils import generate_filename, extract_screenshot_fields
from core.ocr_client import OCRClient


class ScreenshotHandler:
    def __init__(self, ocr_client=None, ai_assistant=None):
        self.ocr_client = ocr_client or OCRClient()
        self.ai_assistant = ai_assistant

    def process(self, image_bytes, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.png', '.bmp', '.gif']:
            result = self.ocr_client.recognize_general(image_bytes)
        else:
            result = self.ocr_client.recognize_advanced(image_bytes)

        if not result:
            return None

        fields = extract_screenshot_fields(result)

        # 检查是否提取到任何有效信息
        has_valid_data = any([
            fields.get('time'),
            fields.get('start'),
            fields.get('end'),
            fields.get('distance')
        ])

        # 如果没有提取到有效信息，返回 None，不进行AI处理
        if not has_valid_data:
            return None

        # 处理时间：只保留日期部分
        if 'time' in fields and fields['time']:
            time_str = fields['time']
            match = re.search(r'(\d{4}[./-]\d{1,2}[./-]\d{1,2})', time_str)
            if match:
                date_part = match.group(1)
                date_part = re.sub(r'[./-]', '', date_part)
                fields['time'] = date_part
            else:
                fields['time'] = datetime.now().strftime('%Y%m%d')

        naming_rule = "{time}_{start}-{end}_{distance}"
        initial_name = generate_filename(fields, naming_rule, ext)

        # AI 自动修正（仅在有效数据存在时）
        ai_corrected = None
        correction_info = ""
        if self.ai_assistant:
            try:
                ai_corrected = self.ai_assistant.auto_correct_screenshot_fields(fields, initial_name)
                correction_info = "AI已自动修正字段"
                fields = ai_corrected
            except Exception as e:
                correction_info = f"AI修正失败，使用原始字段 ({e})"

        new_name = generate_filename(fields, naming_rule, ext)

        return {
            'fields': fields,
            'new_name': new_name,
            'correction_info': correction_info
        }
