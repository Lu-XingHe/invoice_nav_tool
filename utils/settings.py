# -*- coding: utf-8 -*-
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'history.json')

DEFAULT_CONFIG = {
    'accounts': [
        {'name': '默认账号', 'access_key_id': '', 'access_key_secret': '', 'region': 'cn-hangzhou'}
    ],
    'current_account': 0,
    'category_mapping': {},
    'archive_rules': [],
    'field_mapping': {
        'number': '发票号码',
        'date': '开票日期',
        'type': '发票类型',
        'amount': '合计金额',
        'item': '项目名称'
    },
    'theme': 'light',
    'concurrency': 3,
    'history_enabled': True,
    'auto_archive': False,
    'preview_enabled': True,
    # ===== 新增：智谱 API Key =====
    'zai_api_key': ''
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 确保所有默认字段存在
        for key in DEFAULT_CONFIG:
            if key not in data:
                data[key] = DEFAULT_CONFIG[key]
        return data
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_history_record(record):
    history = load_history()
    history.append(record)
    if len(history) > 100:
        history = history[-100:]
    save_history(history)
