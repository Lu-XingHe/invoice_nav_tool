# -*- coding: utf-8 -*-
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pdfplumber


def parse_pdf(file_path):
    result = {}
    try:
        with pdfplumber.open(file_path) as pdf:
            full_text = ''
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + '\n'
        result['full_text'] = full_text
        code = re.search(r'发票代码[：:]\s*(\d{12})', full_text)
        if code:
            result['invoice_code'] = code.group(1)
        num = re.search(r'发票号码[：:]\s*(\d{20})', full_text)
        if num:
            result['invoice_number'] = num.group(1)
        amount = re.search(r'合计金额[：:]\s*([\d.]+)', full_text)
        if amount:
            result['amount'] = amount.group(1)
        date = re.search(r'开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)', full_text)
        if date:
            result['date'] = date.group(1)
        remark = re.search(r'备注[：:]\s*([^。]*?)', full_text)
        if remark:
            result['remark'] = remark.group(1)
        return result
    except Exception as e:
        return {'error': str(e)}


def parse_ofd(file_path):
    result = {}
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
            for xml_file in xml_files:
                if 'Document' in xml_file or 'Content' in xml_file:
                    content = zf.read(xml_file).decode('utf-8')
                    root = ET.fromstring(content)
                    ns = {'ofd': 'http://www.ofdspec.org/2016'}
                    code_elem = root.find('.//ofd:fpdm', ns)
                    if code_elem is not None:
                        result['invoice_code'] = code_elem.text
                    num_elem = root.find('.//ofd:fphm', ns)
                    if num_elem is not None:
                        result['invoice_number'] = num_elem.text
                    amount_elem = root.find('.//ofd:je', ns)
                    if amount_elem is not None:
                        result['amount'] = amount_elem.text
                    break
        return result
    except Exception as e:
        return {'error': str(e)}


def parse_xml(file_path):
    result = {}
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        code = root.find('.//fpdm') or root.find('.//InvoiceCode')
        if code is not None:
            result['invoice_code'] = code.text
        num = root.find('.//fphm') or root.find('.//InvoiceNumber')
        if num is not None:
            result['invoice_number'] = num.text
        amount = root.find('.//je') or root.find('.//TotalAmount')
        if amount is not None:
            result['amount'] = amount.text
        date = root.find('.//kprq') or root.find('.//IssueDate')
        if date is not None:
            result['date'] = date.text
        return result
    except Exception as e:
        return {'error': str(e)}


def parse_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = {}
        for key in ['invoiceCode', '发票代码', 'fpdm']:
            if key in data:
                result['invoice_code'] = data[key]
                break
        for key in ['invoiceNumber', '发票号码', 'fphm']:
            if key in data:
                result['invoice_number'] = data[key]
                break
        for key in ['totalAmount', '合计金额', 'je']:
            if key in data:
                result['amount'] = data[key]
                break
        return result
    except:
        return {}
