"""考勤模块 — 数据模型"""
from sqlalchemy import Column, String, Integer, Integer, ForeignKey, Enum, Boolean, Date, Time, Float, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class CheckInType(str, enum.Enum):
    NORMAL = "normal"
    LATE = "late"
    EARLY = "early"
    ABSENT = "absent"


class AttendanceRule(BaseModel):
    """考勤规则"""
    __tablename__ = "attendance_rules"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(100), nullable=False)
    work_start = Column(Time, nullable=False, comment="上班时间")
    work_end = Column(Time, nullable=False, comment="下班时间")
    flexible_minutes = Column(Integer, default=0, comment="弹性分钟数")
    work_days = Column(String(20), default="1,2,3,4,5", comment="工作日 1=Mon...7=Sun")

    workspace = relationship("Workspace", foreign_keys=[workspace_id])


class AttendanceRecord(BaseModel):
    """打卡记录"""
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint('user_id', 'rule_id', 'date', name='uq_attendance_user_rule_date'),
        {'extend_existing': True},
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("attendance_rules.id"), nullable=False)
    date = Column(Date, nullable=False, comment="日期")
    check_in_time = Column(Time, nullable=True, comment="签到时间")
    check_out_time = Column(Time, nullable=True, comment="签退时间")
    check_in_type = Column(Enum(CheckInType), nullable=True, comment="签到判定")
    check_out_type = Column(Enum(CheckInType), nullable=True, comment="签退判定")
    remark = Column(String(255), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class AttendanceStats(BaseModel):
    """考勤统计（按人+月汇总）"""
    __tablename__ = "attendance_stats"
    __table_args__ = {'extend_existing': True}

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("attendance_rules.id"), nullable=False)
    period_start = Column(Date, nullable=False, comment="统计周期起始")
    period_end = Column(Date, nullable=False, comment="统计周期结束")
    work_days = Column(Integer, default=0, comment="应出勤天数")
    actual_days = Column(Integer, default=0, comment="实际出勤")
    late_count = Column(Integer, default=0, comment="迟到次数")
    early_count = Column(Integer, default=0, comment="早退次数")
    absent_count = Column(Integer, default=0, comment="缺勤天数")
    overtime_hours = Column(DECIMAL(5, 1), default=0, comment="加班时长(小时)")

    user = relationship("User", foreign_keys=[user_id])
