import pandas as pd
import streamlit as st
from services.history import get_history
from services.return_service import get_return_history
from services.ui import load_or_stop
st.title("대여 현황 조회")
rows = load_or_stop(get_history)
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
    st.subheader("반납 처리 이력")
    lookup = {row["대여번호"]: row for row in filtered}
    rental_id = st.selectbox(
        "반납 이력을 볼 대여", list(lookup),
        format_func=lambda key: f'{lookup[key]["물품"]} / {lookup[key]["신청자"]} / {key}',
        key="history_return_rental",
    )
    events = load_or_stop(lambda: get_return_history(rental_id))
    if events:
        st.dataframe(events, hide_index=True, alt="선택한 대여의 반납 건별 수량과 처리 일시")
    else:
        st.info("기록된 반납 처리 이력이 없습니다.")
    untracked = lookup[rental_id]["반납 수량"] - sum(event["반납 수량"] for event in events)
    if untracked:
        st.caption(f"이력 기능 도입 전에 반납한 {untracked}개는 누적 수량만 보존됩니다. 처리 시각은 알 수 없습니다.")
    st.caption("처리 일시는 한국시간(UTC+09:00)입니다.")
else:
    st.info("조회 조건에 맞는 대여 내역이 없습니다.")
