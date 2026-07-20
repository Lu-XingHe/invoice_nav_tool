# -*- coding: utf-8 -*-
"""发票自动分类与生成符合规范的文件名（集成地点提取）"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from core.company_lookup import get_city_from_fields

CATEGORY_KEYWORDS = {
    '餐饮费': ['餐饮', '餐费', '饮食', '餐厅', '快餐', '咖啡', '茶歇'],
    '交通费(高速费)': ['通行费', '高速', '过路', 'ETC', '收费', '公路', '高速公路'],
    '交通费(汽油费)': ['汽油', '加油', '燃油', '柴油', '石油'],
    '交通费(其他)': ['高铁', '火车', '动车', '地铁', '公交', '出租车', '打车', '网约车', '滴滴', '航空', '飞机'],
    '住宿费': ['住宿', '酒店', '宾馆', '旅店', '民宿', '度假'],
    '邮电通讯费': ['通信', '话费', '充值', '宽带', '电话费', '流量'],
    '会议费': ['会议', '论坛', '研讨'],
    '培训费': ['培训', '教育', '学习', '课程'],
    '办公费': ['办公用品', '文具', '打印', '耗材'],
    '广告费': ['广告', '宣传', '推广'],
    '咨询费': ['咨询', '顾问', '服务费'],
    '租赁费': ['租赁', '租车', '租房'],
    '维修费': ['维修', '保养', '修理'],
    '物料费': ['物料', '材料', '配件'],
    '劳务费': ['劳务', '人工', '工资'],
    '医疗费': ['医疗', '医院', '药店', '体检'],
    '福利费': ['福利', '礼品', '员工', '团建'],
    '保险费': ['保险', '社保', '公积金'],
    '税费': ['税', '增值税', '所得税'],
    '其他费用': []
}

TRAVEL_CATEGORIES = ['交通费(高速费)', '交通费(汽油费)', '交通费(其他)']


def classify_invoice(fields: Dict) -> str:
    item = fields.get('item', '')
    inv_type = fields.get('type', '')
    combined = f"{item} {inv_type}"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return cat
    return '其他费用'


def extract_route_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r'([\u4e00-\u9fa5]+?)站?入([\u4e00-\u9fa5]+?)站?出', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r'从([^到]+)到([^，。,\n]+)', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r'([\u4e00-\u9fa5a-zA-Z0-9]+)\s*[-→]\s*([\u4e00-\u9fa5a-zA-Z0-9]+)', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    places = re.findall(r'([\u4e00-\u9fa5]{2,}(?:站|路|街|大道|镇|县|区|市))', text)
    if len(places) >= 2:
        return f"{places[0]}-{places[1]}"
    return None


def extract_date_from_remark(remark: str) -> Optional[str]:
    if not remark:
        return None
    patterns = [
        r'入住日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'入住日期[：:]\s*(\d{4})[./-](\d{1,2})[./-](\d{1,2})',
        r'入住日期[：:]\s*(\d{1,2})[./-](\d{1,2})',
        r'日期[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',
        r'(\d{1,2})[./-](\d{1,2})',
    ]
    for pat in patterns:
        match = re.search(pat, remark)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                year = int(groups[0]) if int(groups[0]) > 1000 else 2000 + int(groups[0])
                month = int(groups[1])
                day = int(groups[2])
                try:
                    dt = datetime(year, month, day)
                    return dt.strftime('%Y%m%d')
                except ValueError:
                    continue
            elif len(groups) == 2:
                now = datetime.now()
                month = int(groups[0])
                day = int(groups[1])
                try:
                    dt = datetime(now.year, month, day)
                    if dt > now + timedelta(days=1):
                        dt = datetime(now.year - 1, month, day)
                    return dt.strftime('%Y%m%d')
                except ValueError:
                    continue
    return None


def get_phone_number(text: str) -> Optional[str]:
    match = re.search(r'1[3-9]\d{9}', text)
    return match.group(0) if match else None


def generate_invoice_filename(fields: Dict, category: str) -> str:
    # ---- 项目名称 ----
    item = fields.get('item', '')
    if not item or item == '未知':
        item = '未知项目'
    safe_item = re.sub(r'[\\/:*?"<>|]', '_', item).strip('_')

    # ---- 金额 ----
    total_amount = fields.get('total', '')
    if not total_amount or total_amount == '0.00' or total_amount == '':
        total_amount = fields.get('amount', '0.00')
    try:
        amount_float = float(total_amount)
        amount_str = f"{amount_float:.2f}"
    except:
        amount_str = total_amount or '0.00'

    # ---- 判断是否为交通类 ----
    is_travel = any(cat in category for cat in ['交通费', '通行费', '高铁', '火车', '动车'])

    # ---- 起止点（仅交通类） ----
    route_part = ''
    if is_travel:
        remark = fields.get('remark', '')
        route = extract_route_from_text(remark) or extract_route_from_text(item)
        if route:
            route_part = f"_{route}"

    # ---- 住宿地点（仅住宿费） ----
    location_part = ''
    if '住宿费' in category:
        seller = fields.get('seller_name', '')
        buyer = fields.get('buyer_name', '')
        seller_tax = fields.get('seller_tax', '')
        buyer_tax = fields.get('buyer_tax', '')

        location = get_city_from_fields(
            seller_name=seller,
            buyer_name=buyer,
            seller_tax=seller_tax,
            buyer_tax=buyer_tax
        )

        if location:
            location_part = f"_{location}"
        else:
            location_part = '_未知地点'

    # ---- 日期处理 ----
    date_part = ''
    if '住宿费' in category:
        remark = fields.get('remark', '')
        extracted_date = extract_date_from_remark(remark)
        if extracted_date:
            date_part = f"_{extracted_date}"
        else:
            date_str = fields.get('date', '')
            if date_str:
                match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    try:
                        dt = datetime(year, month, day)
                        dt = dt - timedelta(days=1)
                        date_part = f"_{dt.strftime('%Y%m%d')}"
                    except:
                        pass
            if not date_part:
                date_part = f"_{datetime.now().strftime('%Y%m%d')}"

    elif '高速费' in category or '通行费' in category:
        remark = fields.get('remark', '')
        extracted_date = extract_date_from_remark(remark)
        if extracted_date:
            date_part = f"_{extracted_date}"
        else:
            date_part = f"_{datetime.now().strftime('%Y%m%d')}"

    elif '汽油费' in category or '燃油' in category:
        date_part = ''

    elif '邮电通讯费' in category or '通信' in category:
        remark = fields.get('remark', '') or fields.get('item', '')
        phone = get_phone_number(remark)
        if phone:
            date_part = f"_{phone}"
        else:
            date_part = '_未知号码'

    else:
        date_str = fields.get('date', '')
        if date_str:
            date_clean = re.sub(r'[^\d]', '', date_str)
            if len(date_clean) >= 8:
                date_part = f"_{date_clean[:8]}"
            else:
                date_part = f"_{datetime.now().strftime('%Y%m%d')}"
        else:
            date_part = f"_{datetime.now().strftime('%Y%m%d')}"

    # ---- 组装文件名 ----
    if '住宿费' in category:
        filename = f"{safe_item}{location_part}_{amount_str}{date_part}.pdf"
    elif is_travel:
        if route_part:
            filename = f"{safe_item}{route_part}_{amount_str}{date_part}.pdf"
        else:
            filename = f"{safe_item}_{amount_str}{date_part}.pdf"
    else:
        filename = f"{safe_item}_{amount_str}{date_part}.pdf"

    filename = re.sub(r'_+', '_', filename)
    filename = filename.replace('_.pdf', '.pdf')
    return filename
