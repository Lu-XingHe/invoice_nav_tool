# -*- coding: utf-8 -*-
"""企业地点查询（多层级：名称提取 → 关键词映射 → 免费API）"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import requests

# ===== 缓存文件路径（保存在项目根目录） =====
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'company_cache.json')

# ===== 关键词映射表（可自由扩充） =====
KEYWORD_MAPPING = {
    # 酒店类
    '悦家酒店': '晋城',
    '物贸大厦': '晋城',
    '晋城酒店': '晋城',
    '晋城宾馆': '晋城',
    '晋焦高速': '晋城',
    '晋焦公路': '晋城',
    # 可根据实际发票数据持续扩充
    '太原': '太原',
    '大同': '大同',
    '阳泉': '阳泉',
    '长治': '长治',
    '晋城': '晋城',
    '朔州': '朔州',
    '晋中': '晋中',
    '运城': '运城',
    '忻州': '忻州',
    '临汾': '临汾',
    '吕梁': '吕梁',
}

# ===== 免费API配置 =====
FREE_API_URL = "https://score.get-scala.com/api/search"


def extract_city_from_name(company_name: str) -> Optional[str]:
    """第一层：直接从公司名称中提取市县名"""
    if not company_name:
        return None
    match = re.search(r'([\u4e00-\u9fa5]{2,})(?:市|县|区)', company_name)
    if match:
        return match.group(1)
    # 省级简称备选
    match = re.search(
        r'(山西|陕西|河南|河北|山东|江苏|浙江|安徽|福建|江西|湖北|湖南|广东|广西|海南|四川|贵州|云南|西藏|青海|甘肃|宁夏|新疆|内蒙古|北京|上海|天津|重庆|香港|澳门)',
        company_name)
    if match:
        return match.group(1)
    return None


def map_keyword_to_city(company_name: str) -> Optional[str]:
    """第二层：根据关键词映射到城市"""
    if not company_name:
        return None
    # 按关键词长度降序，优先匹配长关键词
    sorted_keywords = sorted(KEYWORD_MAPPING.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in company_name:
            return KEYWORD_MAPPING[keyword]
    return None


def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass


def query_free_api(company_name: str) -> Optional[str]:
    """第三层：使用免费API查询（带24小时缓存）"""
    if not company_name:
        return None

    cache = _load_cache()
    cache_key = company_name.strip()
    if cache_key in cache:
        entry = cache[cache_key]
        if 'time' in entry:
            try:
                cache_time = datetime.fromisoformat(entry['time'])
                if datetime.now() - cache_time < timedelta(hours=24):
                    return entry.get('city')
            except:
                pass
        # 缓存过期，删除
        del cache[cache_key]

    try:
        params = {'q': company_name, 'limit': 1}
        response = requests.get(FREE_API_URL, params=params, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        results = data.get('results', [])
        if not results:
            return None

        first = results[0]
        address = first.get('address') or first.get('reg_address') or first.get('location') or ''
        city = None
        if address:
            match = re.search(r'([\u4e00-\u9fa5]{2,})(?:市|县|区)', address)
            if match:
                city = match.group(1)

        if not city:
            city = extract_city_from_name(company_name)

        if city:
            cache[cache_key] = {'city': city, 'time': datetime.now().isoformat()}
            _save_cache(cache)

        return city

    except Exception as e:
        print(f"免费API查询失败: {e}")
        return None


def get_city_from_company(company_name: str) -> Optional[str]:
    """综合查询：按层级顺序提取"""
    if not company_name:
        return None
    company_name = company_name.strip()

    # 层级1：直接提取
    city = extract_city_from_name(company_name)
    if city:
        return city

    # 层级2：关键词映射
    city = map_keyword_to_city(company_name)
    if city:
        return city

    # 层级3：免费API查询
    city = query_free_api(company_name)
    if city:
        return city

    return None


def get_city_from_fields(seller_name: str = None, buyer_name: str = None,
                         seller_tax: str = None, buyer_tax: str = None) -> Optional[str]:
    """从多个字段中提取城市名，优先使用销售方"""
    # 优先销售方名称
    if seller_name:
        city = get_city_from_company(seller_name)
        if city:
            return city
    # 其次购买方名称
    if buyer_name:
        city = get_city_from_company(buyer_name)
        if city:
            return city
    # 未来可扩展税号查询
    return None
