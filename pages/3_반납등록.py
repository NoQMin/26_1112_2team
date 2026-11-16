from datetime import date
import streamlit as st
from services.history import get_history
from services.return_service import register_return
from services.ui import load_or_stop
st.title("반납 수량 등록")
st.caption("부분 반납이 가능하며, 반납 수량은 누적됩니다.")
if "return_notice" in st.session_state:
    st.success(st.session_state.pop("return_notice"))
query = st.text_input("대여번호 또는 신청자 검색", key="return_search").strip().casefold()
rows = [r for r in load_or_stop(get_history) if r["미반납 수량"] > 0 and r["시작일"] <= date.today().isoformat() and (query in r["대여번호"].casefold() or query in r["신청자"].casefold())]
if not rows:
    st.info("반납 가능한 내역이 없습니다. 예약은 시작일부터 반납할 수 있습니다.")
    st.stop()
lookup = {r["대여번호"]: r for r in rows}
selected = st.selectbox("반납할 대여 내역", list(lookup), format_func=lambda k: f'{lookup[k]["물품"]} / {lookup[k]["신청자"]} / {k}', key="return_selected")
row = lookup[selected]
st.dataframe([row], hide_index=True, alt="선택한 대여 현황")
with st.form("return_form"):
    quantity = st.number_input("이번에 반납할 수량", min_value=1, max_value=row["미반납 수량"], step=1, key=f"return_quantity_{selected}")
    submitted = st.form_submit_button("반납 등록", type="primary", key="submit_return")
if submitted:
    try:
        remaining = register_return(selected, int(quantity))
        st.session_state["return_notice"] = f"{quantity}개 반납 완료 · 남은 수량 {remaining}개"
        st.rerun()
    except (ValueError, OSError) as exc:
        st.error(str(exc))
