# -*- coding: utf-8 -*-
"""字段提取、文件名生成等公共函数（稳定版本，项目名称提取逻辑不变）"""

import json
import re
import time


def rule_display_map():
    return {
        "【发票】号码_日期": "{number}_{date}",
        "【发票】号码_金额": "{number}_{amount}",
        "【发票】日期_号码": "{date}_{number}",
        "【发票】项目_号码": "{item}_{number}",
        "【发票】项目_日期": "{item}_{date}",
        "【截图】起点_终点": "{start}_{end}",
        "【截图】时间_里程": "{time}_{distance}",
        "【截图】起点_终点_时间": "{start}_{end}_{time}",
    }


def generate_filename(fields, naming_rule, ext):
    if '{' not in naming_rule:
        chinese_map = {
            '日期': 'date', '类型': 'type', '金额': 'amount',
            '号码': 'number', '项目': 'item',
            '起点': 'start', '终点': 'end',
            '时间': 'time', '里程': 'distance'
        }
        for cn, en in sorted(chinese_map.items(), key=lambda x: -len(x[0])):
            naming_rule = naming_rule.replace(cn, '{' + en + '}')

    defaulted_fields = {}
    for key, value in fields.items():
        if value is None or value == '':
            defaulted_fields[key] = '未知'
        else:
            defaulted_fields[key] = value

    filename = naming_rule
    for key, value in defaulted_fields.items():
        placeholder = '{' + key + '}'
        if placeholder in filename:
            safe_value = re.sub(r'[\\/:*?"<>|]', '_', value)
            filename = filename.replace(placeholder, safe_value)

    filename = re.sub(r'\{.*?\}', '', filename)
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    if not filename:
        filename = '未命名'
    if not any(k in naming_rule for k in ['time', 'date', 'number']):
        filename = f"{filename}_{int(time.time())}"
    return filename + ext


def extract_invoice_fields(result):
    """
    从发票OCR结果中提取关键字段（项目名称提取逻辑稳定，不做修改）
    """
    data = result.get('Data', result)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass

    if not isinstance(data, dict):
        return {}

    # ---- 项目名称提取 ----
    item = None
    invoice_details = data.get('invoiceDetails') or data.get('InvoiceDetails')

    if invoice_details:
        if isinstance(invoice_details, list) and len(invoice_details) > 0:
            first = invoice_details[0]
            if isinstance(first, dict):
                item = first.get('itemName') or first.get('ItemName') or first.get('Name') or first.get('name')
        elif isinstance(invoice_details, str):
            try:
                details_list = json.loads(invoice_details)
                if isinstance(details_list, list) and len(details_list) > 0:
                    first = details_list[0]
                    if isinstance(first, dict):
                        item = first.get('itemName') or first.get('ItemName') or first.get('Name') or first.get('name')
            except:
                match = re.search(r'"itemName"\s*:\s*"([^"]+)"', invoice_details)
                if match:
                    item = match.group(1)

    if not item:
        kv_info = data.get('prism_keyValueInfo') or data.get('Prism_keyValueInfo')
        if isinstance(kv_info, list):
            for kv in kv_info:
                if isinstance(kv, dict):
                    key = kv.get('key') or kv.get('Key')
                    value = kv.get('value') or kv.get('Value')
                    if key and value is not None:
                        if key.lower() in ['invoicedetails', '货物或应税劳务名称', '项目名称', '服务名称', '商品名称']:
                            if isinstance(value, list) and len(value) > 0:
                                first = value[0]
                                if isinstance(first, dict):
                                    item = first.get('itemName') or first.get('ItemName') or first.get(
                                        'Name') or first.get('name')
                            else:
                                item = value
                            if item:
                                break

    if not item:
        merged = {}
        for k, v in data.items():
            if not isinstance(v, (dict, list)):
                merged[k] = v
        if 'data' in data and isinstance(data['data'], str):
            try:
                inner = json.loads(data['data'])
                if isinstance(inner, dict):
                    for k, v in inner.items():
                        if not isinstance(v, (dict, list)):
                            merged[k] = v
            except:
                pass
        kv_info = data.get('prism_keyValueInfo') or data.get('Prism_keyValueInfo')
        if isinstance(kv_info, list):
            for kv in kv_info:
                if isinstance(kv, dict):
                    key = kv.get('key') or kv.get('Key')
                    value = kv.get('value') or kv.get('Value')
                    if key and value is not None:
                        merged[key] = value

        def find_value(keys):
            for k in keys:
                if k in merged:
                    return merged[k]
                for mk, mv in merged.items():
                    if mk.lower() == k.lower():
                        return mv
            return None

        item = find_value(['货物或应税劳务名称', '项目名称', '服务名称', '商品名称', '项目'])
        if not item:
            item = find_value(['itemName', 'ItemName', 'item_name'])

    if item and isinstance(item, str):
        if item.strip().startswith('[{"itemName"'):
            try:
                details = json.loads(item)
                if isinstance(details, list) and len(details) > 0:
                    first = details[0]
                    if isinstance(first, dict):
                        item = first.get('itemName') or first.get('ItemName') or first.get('Name') or first.get('name')
            except:
                pass

    # ---- 其他字段提取 ----
    merged = {}
    for k, v in data.items():
        if not isinstance(v, (dict, list)):
            merged[k] = v
    if 'data' in data and isinstance(data['data'], str):
        try:
            inner = json.loads(data['data'])
            if isinstance(inner, dict):
                for k, v in inner.items():
                    if not isinstance(v, (dict, list)):
                        merged[k] = v
        except:
            pass
    kv_info = data.get('prism_keyValueInfo') or data.get('Prism_keyValueInfo')
    if isinstance(kv_info, list):
        for kv in kv_info:
            if isinstance(kv, dict):
                key = kv.get('key') or kv.get('Key')
                value = kv.get('value') or kv.get('Value')
                if key and value is not None:
                    merged[key] = value

    def find_value(keys):
        for k in keys:
            if k in merged:
                return merged[k]
            for mk, mv in merged.items():
                if mk.lower() == k.lower():
                    return mv
        return None

    number = find_value(['发票号码', 'InvoiceNumber', 'number'])
    code = find_value(['发票代码', 'InvoiceCode', 'code'])
    date = find_value(['开票日期', '发票日期', 'IssueDate', 'invoiceDate', '开票时间', '日期'])
    inv_type = find_value(['发票类型', 'InvoiceType', '票据类型', 'type'])
    amount = find_value(['合计金额', '合计金额（不含税）', 'invoiceAmountPreTax', 'TotalAmount', 'amount'])
    tax = find_value(['合计税额', 'invoiceTax', 'TotalTax', 'tax'])
    total = find_value(['价税合计', 'totalAmount', 'TotalAmountInFig', 'total_amount', 'TotalAmount', '小写金额'])
    if not total:
        total = merged.get('totalAmount') or merged.get('TotalAmount') or merged.get('total_amount')
    total_words = find_value(['大写金额', 'totalAmountInWords', 'AmountInWords', '价税合计（大写）'])

    buyer_name = find_value(['购买方名称', '购方名称', 'purchaserName', 'PurchaserName', 'buyerName'])
    buyer_tax = find_value(['购买方税号', '购方税号', 'purchaserTaxNumber', 'PurchaserTaxNumber', 'buyerTaxNumber'])
    seller_name = find_value(['销售方名称', '销方名称', 'sellerName', 'SellerName'])
    seller_tax = find_value(['销售方税号', '销方税号', 'sellerTaxNumber', 'SellerTaxNumber'])
    drawer = find_value(['开票人', 'drawer', 'Drawer'])
    checker = find_value(['复核人', 'Checker', 'checker'])
    payee = find_value(['收款人', 'Payee', 'payee'])
    remark = find_value(['备注', 'Remark', 'remarks', 'remark'])

    return {
        'number': number or '',
        'code': code or '',
        'date': date or '',
        'type': inv_type or '',
        'amount': amount or '',
        'tax': tax or '',
        'total': total or '',
        'total_words': total_words or '',
        'item': item or '',
        'buyer_name': buyer_name or '',
        'buyer_tax': buyer_tax or '',
        'seller_name': seller_name or '',
        'seller_tax': seller_tax or '',
        'drawer': drawer or '',
        'checker': checker or '',
        'payee': payee or '',
        'remark': remark or '',
    }


def extract_screenshot_fields(result):
    """提取导航截图字段"""
    data = result.get('Data', result)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    full_text = None
    if isinstance(data, dict):
        full_text = data.get('content') or data.get('Content')
    if not full_text:
        full_text = result.get('content') or result.get('Content')
    if not full_text:
        return {}

    time_str = None
    patterns = [
        r'(\d{4}[./-]\d{1,2}[./-]\d{1,2}\s*\d{1,2}[:：]\d{2}(?:[:：]\d{2})?)',
        r'(\d{1,2}[:：]\d{2}(?:[:：]\d{2})?)'
    ]
    for pat in patterns:
        match = re.search(pat, full_text)
        if match:
            time_str = match.group(1).replace('：', ':')
            if '.' in time_str or '/' in time_str:
                time_str = re.sub(r'[./]', '-', time_str)
            break

    distance = None
    match = re.search(r'(\d+(?:\.\d+)?)\s*(km|公里|千米|米|m)', full_text, re.IGNORECASE)
    if match:
        num = match.group(1)
        unit = match.group(2)
        if unit in ['公里', '千米']:
            unit = 'km'
        distance = f"{num}{unit}"

    temp = full_text
    if time_str:
        temp = temp.replace(time_str, '')
    if distance:
        temp = temp.replace(distance, '')
    temp = re.sub(r'\s+', ' ', temp).strip()
    temp = re.sub(r'\b车\b', '', temp)
    temp = re.sub(r'\s+', ' ', temp).strip()
    places = re.findall(r'[\u4e00-\u9fa5]+(?:市|县|区|路|街|道|镇|乡|村|大道|大街|广场|大厦|小区|路口)', temp)
    start = places[0] if len(places) > 0 else ''
    end = places[1] if len(places) > 1 else ''

    return {
        'time': time_str or '',
        'distance': distance or '',
        'start': start,
        'end': end,
    }
