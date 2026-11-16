from datetime import date
import streamlit as st
from services.inventory import get_items, available_quantity, validate_period
st.title("날짜별 대여 가능 수량 조회")
st.caption("시작일과 종료일을 모두 포함한 기간의 재고입니다. 연체 물품은 실제 반납 전까지 차감됩니다.")
start = st.date_input("대여 시작일", min_value=date.today(), key="inventory_start")
end = st.date_input("반납 예정일", min_value=date.today(), key="inventory_end")
try:
    validate_period(start, end)
    rows = [{"물품": r["name"], "분류": r["category"], "전체 수량": int(r["total"]), "대여 가능 수량": available_quantity(r["item_id"], start, end)} for r in get_items()]
    st.dataframe(rows, hide_index=True, alt="선택 기간 물품별 재고")
except ValueError as exc:
    st.error(str(exc))
