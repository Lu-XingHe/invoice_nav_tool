# -*- coding: utf-8 -*-
import os
import shutil

from core.deduplicator import Deduplicator
from core.excel_generator import generate_reimbursement_excel, generate_travel_detail_excel
from core.field_utils import extract_invoice_fields
from core.invoice_classifier import classify_invoice, generate_invoice_filename
from core.ocr_client import OCRClient
from core.pdf_parser import parse_pdf, parse_ofd, parse_xml, parse_json
from core.qr_decoder import decode_qr_from_image, download_pdf_from_url


class InvoicePipeline:
    def __init__(self, output_dir, company_info=None):
        self.output_dir = output_dir
        self.company_info = company_info or {
            'name': '山西云农晋科信息技术有限公司',
            'tax_id': '91140105MA0LXC7P8E'
        }
        self.dedup = Deduplicator()
        self.invoice_files = []
        self.travel_records = []

    def process_qr_image(self, qr_image_path):
        url = decode_qr_from_image(qr_image_path)
        if not url:
            return None
        pdf_name = os.path.basename(url).split('?')[0]
        if not pdf_name.endswith('.pdf'):
            pdf_name += '.pdf'
        save_path = os.path.join(self.output_dir, pdf_name)
        if download_pdf_from_url(url, save_path):
            return save_path
        return None

    def parse_invoice_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            result = parse_pdf(file_path)
            if not result.get('invoice_number'):
                # 尝试OCR
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                ocr = OCRClient()
                ocr_result = ocr.recognize_invoice(image_bytes)
                if ocr_result:
                    ocr_fields = extract_invoice_fields(ocr_result)
                    result.update(ocr_fields)
            return result
        elif ext == '.ofd':
            return parse_ofd(file_path)
        elif ext == '.xml':
            return parse_xml(file_path)
        elif ext == '.json':
            return parse_json(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            ocr = OCRClient()
            result = ocr.recognize_invoice(image_bytes)
            if result:
                return extract_invoice_fields(result)
            else:
                return {}
        else:
            return {}

    def process_invoice(self, file_path):
        parsed = self.parse_invoice_file(file_path)
        if not parsed or not parsed.get('invoice_number'):
            return None
        inv_num = parsed['invoice_number']
        if self.dedup.is_duplicate(inv_num):
            return {'duplicate': True, 'number': inv_num}
        category = classify_invoice(parsed)
        new_name = generate_invoice_filename(parsed, category)
        new_path = os.path.join(self.output_dir, new_name)

        if os.path.exists(new_path):
            base, ext = os.path.splitext(new_name)
            counter = 1
            while os.path.exists(
                    os.path.join(self.output_dir, f"{base}_重复文件{counter if counter > 1 else ''}{ext}")):
                counter += 1
            if counter == 1:
                new_name = f"{base}_重复文件{ext}"
            else:
                new_name = f"{base}_重复文件{counter}{ext}"
            new_path = os.path.join(self.output_dir, new_name)

        shutil.copy2(file_path, new_path)
        self.dedup.add_record(inv_num, new_path)
        self.invoice_files.append({
            'date': parsed.get('date', ''),
            'category': category,
            'amount': parsed.get('amount', '0'),
            'invoice_path': new_path,
            'remark': parsed.get('remark', '')
        })
        return {'success': True, 'new_name': new_name}

    def process_screenshot(self, file_path):
        basename = os.path.basename(file_path)
        parts = basename.split('_')
        if len(parts) >= 3:
            date = parts[0]
            route = parts[1].split('-')
            start = route[0] if len(route) > 0 else ''
            end = route[1] if len(route) > 1 else ''
            dist = parts[2].replace('km.png', '').replace('.png', '')
        else:
            # 使用OCR提取
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            ocr = OCRClient()
            result = ocr.recognize_advanced(image_bytes)
            if result:
                from core.field_utils import extract_screenshot_fields
                fields = extract_screenshot_fields(result)
                date = fields.get('time', '').replace('-', '').replace(':', '').strip()
                if len(date) >= 8:
                    date = date[:8]
                else:
                    date = '00000000'
                start = fields.get('start', '')
                end = fields.get('end', '')
                dist = fields.get('distance', '').replace('km', '').strip()
            else:
                return None
        new_name = f"{date}_{start}-{end}_{dist}km.png"
        new_path = os.path.join(self.output_dir, new_name)
        shutil.copy2(file_path, new_path)
        self.travel_records.append({
            'date': date,
            'start': start,
            'end': end,
            'distance': dist,
            'screenshot_path': new_path
        })
        return new_path

    def finalize(self):
        if self.invoice_files:
            generate_reimbursement_excel(self.invoice_files,
                                         os.path.join(self.output_dir, '报销单.xlsx'))
        if self.travel_records:
            generate_travel_detail_excel(self.travel_records,
                                         os.path.join(self.output_dir, '交通出行明细.xlsx'))
