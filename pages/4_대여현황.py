import pandas as pd
import streamlit as st
from services.history import get_history
st.title("대여 현황 조회")
rows = get_history()
query = st.text_input("신청자 · 소속 · 물품 · 대여번호 검색", key="history_search").strip().casefold()
status = st.multiselect("상태", ["예약", "대여 중", "연체", "반납 완료"], key="history_status")
filtered = [r for r in rows if (not status or r["상태"] in status) and any(query in str(r[k]).casefold() for k in ["신청자", "소속", "물품", "대여번호"])]
with st.container(horizontal=True):
    st.metric("조회 건수", len(filtered))
    st.metric("미반납 수량", sum(r["미반납 수량"] for r in filtered))
    st.metric("연체 건수", sum(r["상태"] == "연체" for r in filtered))
if filtered:
    frame = pd.DataFrame(filtered)
    st.dataframe(frame, hide_index=True, alt="검색한 대여 현황")
    safe = frame.map(lambda v: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else v)
    st.download_button("조회 결과 CSV 다운로드", safe.to_csv(index=False).encode("utf-8-sig"), "rental_history.csv", "text/csv")
else:
    st.info("조회 조건에 맞는 대여 내역이 없습니다.")
