"""RFC 5545 简单重复规则解析"""
from datetime import datetime, timedelta
from dateutil.rrule import rrulestr, rrule
from dateutil.parser import parse


def parse_recurrence(rule_string: str, start: datetime, until: datetime = None) -> list[datetime]:
    """解析 RFC 5545 重复规则，返回在 [start, until] 内的所有事件日期。
    复用 python-dateutil 的 rrulestr。
    """
    if not rule_string:
        return []

    try:
        rule = rrulestr(rule_string, dtstart=start)
        if until is None:
            until = start + timedelta(days=90)  # 默认展开 90 天
        return list(rule.between(start, until, inc=True))
    except Exception:
        return []


def build_rule_string(freq: str, interval: int = 1, count: int = None,
                      until_date: str = None, by_day: str = None,
                      by_month_day: int = None) -> str:
    """构建 RFC 5545 规则字符串。
    freq: DAILY/WEEKLY/MONTHLY/YEARLY
    interval: 间隔
    count: 重复次数
    until_date: YYYYMMDDTHHMMSS 格式结束日期
    by_day: MO/TU/WE/TH/FR/SA/SU
    """
    parts = [f"FREQ={freq}"]
    if interval > 1:
        parts.append(f"INTERVAL={interval}")
    if count:
        parts.append(f"COUNT={count}")
    if until_date:
        parts.append(f"UNTIL={until_date}")
    if by_day:
        parts.append(f"BYDAY={by_day}")
    if by_month_day:
        parts.append(f"BYMONTHDAY={by_month_day}")

    return ";".join(parts)
