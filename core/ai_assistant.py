# -*- coding: utf-8 -*-
"""智谱 GLM-4.7-Flash 大模型封装（含规则加载和自动修正）"""

import json
import os

from zai import ZhipuAiClient

from utils.settings import load_config


class AIAssistant:
    def __init__(self, api_key=None):
        if api_key is None:
            config = load_config()
            api_key = config.get('zai_api_key', '')
            if not api_key:
                api_key = os.getenv("ZAI_API_KEY", "")
        if not api_key:
            raise ValueError("请先在系统设置中配置智谱 API Key，或设置环境变量 ZAI_API_KEY")
        self.client = ZhipuAiClient(api_key=api_key)
        self.model = "glm-4.7-flash"
        self._rules_context = None

    def load_rules_context(self):
        """加载所有自定义规则作为AI上下文"""
        config = load_config()
        rules = {
            "category_mapping": config.get('category_mapping', {}),
            "archive_rules": config.get('archive_rules', []),
            "field_mapping": config.get('field_mapping', {}),
            "naming_rules": {
                "invoice": "发票命名格式：项目名称_地点_金额_日期.pdf（住宿类）或 项目名称_起止点_金额_日期.pdf（交通类）",
                "screenshot": "截图命名格式：日期_起点-终点_距离km.png"
            },
            "company_info": {
                "name": "山西云农晋科信息技术有限公司",
                "tax_id": "91140105MA0LXC7P8E"
            }
        }
        self._rules_context = json.dumps(rules, ensure_ascii=False, indent=2)
        return self._rules_context

    def get_rules_prompt(self):
        """返回规则提示词，供其他方法调用"""
        if self._rules_context is None:
            self.load_rules_context()
        return f"以下是用户自定义的规则和公司信息，请严格遵守：\n{self._rules_context}\n"

    def chat(self, user_message, system_prompt="你是一个有用的AI助手，请用中文回答。",
             temperature=0.3, max_tokens=2048, response_format=None):
        """发送对话请求，自动注入规则上下文"""
        rules = self.get_rules_prompt()
        full_system = f"{rules}\n{system_prompt}"
        try:
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": user_message}
                ],
                "thinking": {"type": "enabled"},
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if response_format == 'json_object':
                params["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ 调用AI出错: {e}"

    def auto_correct_invoice_fields(self, fields, category, generated_name):
        """自动修正发票字段"""
        system = """你是一个发票信息修正专家。请根据规则自动修正提取的字段，并以JSON格式返回修正后的完整字段字典。

修正规则：
1. 项目名称（item）：如果包含 "*"，保留完整内容；如果缺少服务类型，尝试推断。
2. 金额（total）：应为价税合计金额，若提取到不含税金额但无价税合计，则使用不含税金额。
3. 日期（date）：住宿类应使用备注中的入住日期；其他使用开票日期。日期格式统一为 YYYYMMDD。
4. 地点（location）：从销售方或购买方名称中提取市县名，若提取不到则保留原值。
5. 分类（category）：根据项目名称和规则自动判断费用类型（住宿费、交通费、餐饮费等）。

输出格式必须是严格的JSON，键名与输入字段一致，包含所有原始字段（即使未修正也原样返回）。
"""
        user = f"""
当前分类：{category}
原始提取字段：{json.dumps(fields, ensure_ascii=False, indent=2)}
生成的文件名：{generated_name}

请修正字段并返回完整JSON。
"""
        result = self.chat(user, system_prompt=system, temperature=0.3, max_tokens=4096, response_format='json_object')
        try:
            corrected = json.loads(result)
            for key in fields:
                if key not in corrected:
                    corrected[key] = fields[key]
            return corrected
        except:
            return fields

    def auto_correct_screenshot_fields(self, fields, generated_name):
        """自动修正截图字段"""
        system = """你是一个导航截图信息修正专家。请根据规则自动修正提取的字段，并以JSON格式返回修正后的完整字段字典。

修正规则：
1. 时间（time）：应为日期格式 YYYYMMDD，不含时分秒。如果有日期则提取，否则使用当前日期。
2. 起点（start）：应为实际地名，去除多余符号。
3. 终点（end）：应为实际地名，去除多余符号。
4. 距离（distance）：应为数字+km，保留一位小数。

输出格式必须是严格的JSON，键名与输入字段一致（time, start, end, distance）。
"""
        user = f"""
原始提取字段：{json.dumps(fields, ensure_ascii=False, indent=2)}
生成的文件名：{generated_name}

请修正字段并返回完整JSON。
"""
        result = self.chat(user, system_prompt=system, temperature=0.3, max_tokens=4096, response_format='json_object')
        try:
            corrected = json.loads(result)
            for key in fields:
                if key not in corrected:
                    corrected[key] = fields[key]
            return corrected
        except:
            return fields
