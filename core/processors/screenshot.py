# -*- coding: utf-8 -*-
"""导航截图识别结果处理"""


def process_screenshot(fields):
    if not fields:
        return "识别结果为空"

    lines = []
    lines.append("📌 导航截图关键信息")
    lines.append("=" * 40)

    if fields.get('time'):
        lines.append(f"出行时间：{fields['time']}")
    if fields.get('start'):
        lines.append(f"起点：{fields['start']}")
    if fields.get('end'):
        lines.append(f"终点：{fields['end']}")
    if fields.get('distance'):
        lines.append(f"距离：{fields['distance']}")

    if len(lines) <= 2:
        lines.append("未提取到关键信息")

    return "\n".join(lines)
