# -*- coding: utf-8 -*-
"""发票识别结果处理（显示完整字段，直接接收 fields）"""


def process_invoice(fields):
    if not fields:
        return "识别结果为空"

    lines = []
    lines.append("📋 发票关键信息")
    lines.append("=" * 40)

    # 基础信息
    if fields.get('number'):
        lines.append(f"发票号码：{fields['number']}")
    if fields.get('code'):
        lines.append(f"发票代码：{fields['code']}")
    if fields.get('date'):
        lines.append(f"开票日期：{fields['date']}")
    if fields.get('type'):
        lines.append(f"发票类型：{fields['type']}")

    # 金额
    if fields.get('amount'):
        lines.append(f"合计金额（不含税）：{fields['amount']}")
    if fields.get('total'):
        lines.append(f"价税合计（小写）：{fields['total']}")
    if fields.get('total_words'):
        lines.append(f"价税合计（大写）：{fields['total_words']}")

    # 项目名称
    if fields.get('item'):
        lines.append(f"项目名称：{fields['item']}")

    # 购买方
    if fields.get('buyer_name'):
        lines.append(f"购买方名称：{fields['buyer_name']}")
    if fields.get('buyer_tax'):
        lines.append(f"购买方税号：{fields['buyer_tax']}")

    # 销售方
    if fields.get('seller_name'):
        lines.append(f"销售方名称：{fields['seller_name']}")
    if fields.get('seller_tax'):
        lines.append(f"销售方税号：{fields['seller_tax']}")

    # 人员
    if fields.get('drawer'):
        lines.append(f"开票人：{fields['drawer']}")
    if fields.get('checker'):
        lines.append(f"复核人：{fields['checker']}")
    if fields.get('payee'):
        lines.append(f"收款人：{fields['payee']}")

    # 备注
    if fields.get('remark'):
        lines.append(f"备注：{fields['remark']}")

    if len(lines) <= 2:
        lines.append("未提取到关键信息，请查看完整JSON")

    return "\n".join(lines)
