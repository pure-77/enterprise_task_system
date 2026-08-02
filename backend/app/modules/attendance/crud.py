"""考勤模块 — CRUD"""
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.modules.attendance.models import (
    AttendanceRule, AttendanceRecord, AttendanceStats, CheckInType
)
from app.core.exceptions import ResourceNotFoundError, BusinessError
from app.db.base import get_beijing_time


def _add_minutes(t: time, minutes: int) -> time:
    """对 time 对象安全地加减分钟，自动处理跨日"""
    total = (t.hour * 60 + t.minute + minutes) % (24 * 60)
    return time(hour=total // 60, minute=total % 60)


def _judge_check_in(rule: AttendanceRule, actual_time: time) -> str:
    """判断签到类型 — 直接对 time 对象做分钟加减，避免跨日截断"""
    cutoff = _add_minutes(rule.work_start, rule.flexible_minutes)
    # 处理跨日情况：如果 cutoff < work_start 说明跨日了，按 work_start 当天判断
    if cutoff < rule.work_start:
        # 跨日，actual_time 在 work_start 之后即视为正常
        return CheckInType.NORMAL.value if actual_time >= rule.work_start else CheckInType.LATE.value
    return CheckInType.NORMAL.value if actual_time <= cutoff else CheckInType.LATE.value


def _judge_check_out(rule: AttendanceRule, actual_time: time) -> str:
    """判断签退类型"""
    return CheckInType.NORMAL.value if actual_time >= rule.work_end else CheckInType.EARLY.value


def _is_work_day(rule: AttendanceRule, d: date) -> bool:
    """判断某天是否为工作日"""
    work_days = [int(x) for x in (rule.work_days or "1,2,3,4,5").split(",") if x.strip()]
    return d.isoweekday() in work_days


class AttendanceCRUD:

    # ===== Rule =====

    def get_rules(self, db: Session, workspace_id: int) -> list[AttendanceRule]:
        return db.query(AttendanceRule).filter(
            AttendanceRule.workspace_id == workspace_id,
            AttendanceRule.is_active == True
        ).all()

    def get_rule(self, db: Session, rule_id: int) -> AttendanceRule:
        r = db.query(AttendanceRule).filter(
            AttendanceRule.id == rule_id, AttendanceRule.is_active == True
        ).first()
        if not r:
            raise ResourceNotFoundError(resource="考勤规则")
        return r

    def create_rule(self, db: Session, workspace_id: int, name: str,
                    work_start: time, work_end: time,
                    flexible_minutes: int = 0, work_days: str = "1,2,3,4,5") -> AttendanceRule:
        r = AttendanceRule(workspace_id=workspace_id, name=name,
                          work_start=work_start, work_end=work_end,
                          flexible_minutes=flexible_minutes, work_days=work_days)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    def delete_rule(self, db: Session, rule_id: int):
        r = self.get_rule(db, rule_id)
        r.is_active = False
        db.commit()

    # ===== Record =====

    def check_in(self, db: Session, user_id: int, rule_id: int,
                 remark: str = None) -> AttendanceRecord:
        rule = self.get_rule(db, rule_id)
        today = date.today()
        now = datetime.now().time()

        # 非工作日允许打卡（用于加班/测试场景），统计时仍按工作日计算缺勤

        # 使用行锁防止并发重复打卡 — SELECT ... FOR UPDATE
        existing = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.rule_id == rule_id,
            AttendanceRecord.date == today
        ).with_for_update().first()

        if existing and existing.check_in_time:
            raise BusinessError("今日已签到")

        check_type = _judge_check_in(rule, now)

        if existing:
            existing.check_in_time = now
            existing.check_in_type = check_type
            existing.remark = remark
            db.commit()
            db.refresh(existing)
            return existing

        try:
            rec = AttendanceRecord(
                user_id=user_id, rule_id=rule_id, date=today,
                check_in_time=now, check_in_type=check_type,
                remark=remark
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)
            return rec
        except Exception as e:
            db.rollback()
            # 唯一约束冲突时再次查询
            existing = db.query(AttendanceRecord).filter(
                AttendanceRecord.user_id == user_id,
                AttendanceRecord.rule_id == rule_id,
                AttendanceRecord.date == today
            ).first()
            if existing and existing.check_in_time:
                raise BusinessError("今日已签到")
            raise BusinessError(f"打卡失败: {str(e)}")

    def check_out(self, db: Session, user_id: int, rule_id: int,
                  remark: str = None) -> AttendanceRecord:
        rule = self.get_rule(db, rule_id)
        today = date.today()
        now = datetime.now().time()

        # 使用行锁防止并发
        rec = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.rule_id == rule_id,
            AttendanceRecord.date == today
        ).with_for_update().first()

        if not rec or not rec.check_in_time:
            raise BusinessError("请先签到")

        if rec.check_out_time:
            raise BusinessError("今日已签退")

        rec.check_out_time = now
        rec.check_out_type = _judge_check_out(rule, now)
        if remark:
            rec.remark = (rec.remark or "") + "; " + remark
        db.commit()
        db.refresh(rec)
        return rec

    def get_records(self, db: Session, user_id: int, rule_id: int,
                    start_date: date = None, end_date: date = None,
                    page: int = 1, page_size: int = 31) -> dict:
        q = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.rule_id == rule_id,
            AttendanceRecord.is_active == True
        )
        if start_date:
            q = q.filter(AttendanceRecord.date >= start_date)
        if end_date:
            q = q.filter(AttendanceRecord.date <= end_date)

        total = q.count()
        records = q.order_by(AttendanceRecord.date.desc()).offset(
            (page - 1) * page_size).limit(page_size).all()

        items = []
        for r in records:
            items.append({
                "id": r.id, "date": r.date.isoformat() if r.date else None,
                "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                "check_out_time": r.check_out_time.isoformat() if r.check_out_time else None,
                "check_in_type": r.check_in_type.value if r.check_in_type else None,
                "check_out_type": r.check_out_type.value if r.check_out_type else None,
                "remark": r.remark
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ===== Stats =====

    def get_my_stats(self, db: Session, user_id: int, rule_id: int,
                     period_start: date = None) -> dict:
        """获取某月考勤统计 — 基于工作日历计算缺勤"""
        if not period_start:
            period_start = date.today().replace(day=1)
        next_month = period_start.replace(day=28) + timedelta(days=4)
        period_end = next_month.replace(day=1) - timedelta(days=1)

        st = db.query(AttendanceStats).filter(
            AttendanceStats.user_id == user_id,
            AttendanceStats.rule_id == rule_id,
            AttendanceStats.period_start == period_start,
            AttendanceStats.is_active == True
        ).first()

        if st:
            return {
                "period_start": st.period_start.isoformat(),
                "period_end": st.period_end.isoformat(),
                "work_days": st.work_days, "actual_days": st.actual_days,
                "late_count": st.late_count, "early_count": st.early_count,
                "absent_count": st.absent_count,
                "overtime_hours": float(st.overtime_hours)
            }

        # 实时计算
        rule = self.get_rule(db, rule_id)
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.rule_id == rule_id,
            AttendanceRecord.date >= period_start,
            AttendanceRecord.date <= period_end,
            AttendanceRecord.is_active == True
        ).all()
        records_map = {r.date: r for r in records}

        # 基于工作日历统计应出勤天数
        work_days = 0
        actual_days = 0
        late_count = 0
        early_count = 0
        absent_count = 0
        overtime_hours = 0.0
        today = date.today()

        d = period_start
        while d <= period_end:
            # 只统计工作日；未来日期不统计缺勤
            if _is_work_day(rule, d) and d <= today:
                work_days += 1
                r = records_map.get(d)
                if r and r.check_in_time:
                    actual_days += 1
                    if r.check_in_type == CheckInType.LATE:
                        late_count += 1
                    if r.check_out_type == CheckInType.EARLY:
                        early_count += 1
                    # 加班：超过下班时间按小时计
                    if r.check_out_time and r.check_out_time > rule.work_end:
                        end_dt = datetime.combine(r.date, rule.work_end)
                        actual_dt = datetime.combine(r.date, r.check_out_time)
                        diff = (actual_dt - end_dt).total_seconds() / 3600
                        if diff > 0.5:  # 超过 30 分钟才计加班
                            overtime_hours += diff
                else:
                    # 工作日但无打卡记录 = 缺勤（仅统计过去日期）
                    if d < today:
                        absent_count += 1
            d += timedelta(days=1)

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "work_days": work_days,
            "actual_days": actual_days,
            "late_count": late_count,
            "early_count": early_count,
            "absent_count": absent_count,
            "overtime_hours": round(overtime_hours, 1)
        }


attendance_crud = AttendanceCRUD()
