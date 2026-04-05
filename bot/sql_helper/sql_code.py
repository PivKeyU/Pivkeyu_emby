import math
from datetime import datetime

from bot.sql_helper import Base, Session
from cacheout import Cache
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func

cache = Cache()


def _normalized_limit_expr():
    return func.coalesce(Code.use_limit, 1)


def _normalized_count_expr():
    return func.coalesce(Code.use_count, 0)


def _available_filter():
    return _normalized_count_expr() < _normalized_limit_expr()


def _exhausted_filter():
    return _normalized_count_expr() >= _normalized_limit_expr()


class Code(Base):
    """
    Register / renew code records.

    `used` and `usedtime` are kept for backward compatibility and now represent
    the latest user / latest usage time.
    """

    __tablename__ = "Rcode"

    code = Column(String(50), primary_key=True, autoincrement=False)
    tg = Column(BigInteger)
    us = Column(Integer)
    used = Column(BigInteger, nullable=True)
    usedtime = Column(DateTime, nullable=True)
    use_limit = Column(Integer, nullable=False, default=1, server_default="1")
    use_count = Column(Integer, nullable=False, default=0, server_default="0")


class CodeRedeem(Base):
    """Per-user redeem history for codes."""

    __tablename__ = "RcodeRedeem"
    __table_args__ = (
        UniqueConstraint("code", "user_id", name="uq_rcode_redeem_code_user"),
        Index("ix_rcode_redeem_user_id", "user_id"),
        Index("ix_rcode_redeem_redeemed_at", "redeemed_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), ForeignKey("Rcode.code", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    owner_tg = Column(BigInteger, nullable=True)
    code_days = Column(Integer, nullable=True)
    use_index = Column(Integer, nullable=False, default=1)
    redeemed_at = Column(DateTime, nullable=False, default=datetime.now)


def sql_add_code(code_list: list, tg: int, us: int, use_limit: int = 1):
    """Bulk insert codes.

    `code_list` supports either:
    - `["CODE-1", "CODE-2"]`
    - `[{"code": "CODE-1", "use_limit": 3}, ...]`
    """

    normalized_limit = max(int(use_limit or 1), 1)

    with Session() as session:
        try:
            rows = []
            for item in code_list:
                if isinstance(item, dict):
                    code = item["code"]
                    item_limit = max(int(item.get("use_limit", normalized_limit) or 1), 1)
                else:
                    code = str(item)
                    item_limit = normalized_limit

                rows.append(
                    Code(
                        code=code,
                        tg=tg,
                        us=us,
                        use_limit=item_limit,
                        use_count=0,
                    )
                )

            session.add_all(rows)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False


def sql_update_code(code, used: int, usedtime: datetime):
    with Session() as session:
        try:
            data = {"used": used, "usedtime": usedtime}
            changed = session.query(Code).filter(Code.code == code).update(data)
            if changed == 0:
                return False
            session.commit()
            return True
        except Exception as exc:
            print(exc)
            session.rollback()
            return False


def sql_get_code(code):
    with Session() as session:
        try:
            return session.query(Code).filter(Code.code == code).first()
        except Exception:
            return None


def sql_has_code_redeemed_by_user(code: str, user_id: int) -> bool:
    with Session() as session:
        try:
            return (
                session.query(CodeRedeem.id)
                .filter(CodeRedeem.code == code, CodeRedeem.user_id == user_id)
                .first()
                is not None
            )
        except Exception:
            return False


def sql_get_code_redeem_history(code: str = None, user_id: int = None, limit: int = 100):
    with Session() as session:
        try:
            query = session.query(CodeRedeem)
            if code is not None:
                query = query.filter(CodeRedeem.code == code)
            if user_id is not None:
                query = query.filter(CodeRedeem.user_id == user_id)

            query = query.order_by(CodeRedeem.redeemed_at.desc(), CodeRedeem.id.desc())
            if limit:
                query = query.limit(int(limit))
            return query.all()
        except Exception as exc:
            print(exc)
            return []


def sql_count_code(tg: int = None):
    with Session() as session:
        try:
            base_query = session.query(Code)
            if tg is not None:
                base_query = base_query.filter(Code.tg == tg)

            exhausted_count = base_query.filter(_exhausted_filter()).count()
            available_count = base_query.filter(_available_filter()).count()

            us_list = [30, 90, 180, 365]
            tg_mon, tg_sea, tg_half, tg_year = [
                base_query.filter(_available_filter()).filter(Code.us == us).count() for us in us_list
            ]
            return exhausted_count, tg_mon, tg_sea, tg_half, tg_year, available_count
        except Exception as exc:
            print(exc)
            return None


def _paginate_query(query, page_size: int, render):
    total = query.count()
    if total == 0:
        return None, 1

    total_pages = math.ceil(total / page_size)
    pages = []

    for page in range(total_pages):
        rows = query.limit(page_size).offset(page * page_size).all()
        start_index = page * page_size + 1
        pages.append(render(rows, start_index))

    return pages, total_pages


def _render_code_rows(rows, start_index: int, include_usage_owner: bool = False):
    lines = []
    index = start_index
    for row in rows:
        usage = f"{row.use_count}/{row.use_limit}"
        line = f"{index}. `{row.code}`\n天数 {row.us}d | 已用 {usage} 次"
        if include_usage_owner and row.used:
            line += f" | 最近 @[{row.used}](tg://user?id={row.used})"
        if include_usage_owner and row.usedtime:
            line += f" ({row.usedtime})"
        line += "\n"
        lines.append(line)
        index += 1
    return "".join(lines)


def sql_count_p_code(tg_id, us):
    with Session() as session:
        try:
            query = session.query(Code).filter(Code.tg == tg_id)

            if us == 0:
                query = query.filter(_exhausted_filter()).order_by(Code.usedtime.desc(), Code.code.asc())
                return _paginate_query(
                    query,
                    30,
                    lambda rows, start: _render_code_rows(rows, start, include_usage_owner=True),
                )

            if us == -1:
                query = query.filter(_available_filter()).order_by(Code.us.asc(), Code.code.asc())
                return _paginate_query(query, 30, _render_code_rows)

            query = (
                query.filter(Code.us == us)
                .filter(_available_filter())
                .order_by(Code.usedtime.desc(), Code.code.asc())
            )
            return _paginate_query(query, 30, _render_code_rows)
        except Exception as exc:
            print(exc)
            return None, 1


def sql_count_c_code(tg_id):
    with Session() as session:
        try:
            query = session.query(Code).filter(Code.tg == tg_id).order_by(Code.usedtime.desc(), Code.code.asc())
            return _paginate_query(
                query,
                5,
                lambda rows, start: _render_code_rows(rows, start, include_usage_owner=True),
            )
        except Exception as exc:
            print(exc)
            return None, 1


def sql_delete_unused_by_days(days: list[int], user_id: int = None) -> int:
    with Session() as session:
        try:
            query = session.query(Code).filter(_available_filter())
            if user_id is not None:
                query = query.filter(Code.tg == user_id)
            query = query.filter(Code.us.in_(days))
            result = query.delete(synchronize_session=False)
            session.commit()
            return result
        except Exception as exc:
            session.rollback()
            print(f"删除注册码失败: {exc}")
            return 0


def sql_delete_all_unused(user_id: int = None) -> int:
    with Session() as session:
        try:
            query = session.query(Code).filter(_available_filter())
            if user_id is not None:
                query = query.filter(Code.tg == user_id)
            result = query.delete(synchronize_session=False)
            session.commit()
            return result
        except Exception as exc:
            session.rollback()
            print(f"删除所有可用注册码失败: {exc}")
            return 0
