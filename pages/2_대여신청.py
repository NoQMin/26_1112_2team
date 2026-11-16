from datetime import date
import streamlit as st
from services.inventory import get_items
from services.rental import create_rental
st.title("대여 신청")
st.caption("제출 시점에 선택한 기간의 재고를 다시 확인합니다.")
names = {r["item_id"]: r["name"] for r in get_items()}
if not names:
    st.info("등록된 물품이 없습니다.")
    st.stop()
with st.form("rental_form"):
    item = st.selectbox("대여 물품", list(names), format_func=names.get, key="rental_item")
    borrower = st.text_input("신청자 이름", max_chars=50, key="borrower")
    department = st.text_input("소속 (학과 / 동아리)", max_chars=100, key="department")
    start = st.date_input("대여 시작일", min_value=date.today(), key="rental_start")
    end = st.date_input("반납 예정일", min_value=date.today(), key="rental_end")
    quantity = st.number_input("대여 수량", min_value=1, step=1, key="rental_quantity")
    submitted = st.form_submit_button("대여 신청하기", type="primary", key="submit_rental")
if submitted:
    try:
        rental_id = create_rental(item, borrower, department, int(quantity), start, end)
        st.success(f"대여 신청 완료 · 대여번호: {rental_id}")
    except ValueError as exc:
        st.error(str(exc))
