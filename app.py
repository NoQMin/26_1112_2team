"""바로대여 Streamlit 실행 진입점과 공통 메뉴."""

import streamlit as st


st.set_page_config(page_title="바로대여", layout="centered")


def home():
    """서비스 소개 화면을 표시한다."""
    st.title("바로대여 물품 대여 관리 시스템")
    st.write("대학교 물품의 대여와 반납을 편리하게 관리하기 위한 서비스입니다.")
    st.info("재고 조회부터 대여 신청, 부분 반납, 현황 확인까지 관리할 수 있습니다.")
    from services.history import get_history
    from services.inventory import get_items
    from services.ui import load_or_stop
    rows = load_or_stop(get_history)
    with st.container(horizontal=True):
        st.metric("물품 종류", len(load_or_stop(get_items)))
        st.metric("미반납 수량", sum(r["미반납 수량"] for r in rows))
        st.metric("연체 건수", sum(r["상태"] == "연체" for r in rows))
    st.caption("초기 물품은 시연용 예시입니다. 실제 운영 전 data/items.csv를 수정해 주세요.")


page = st.navigation(
    [
        st.Page(home, title="홈", icon=":material/home:", default=True),
        st.Page("pages/1_재고조회.py", title="날짜별 대여 가능 수량 조회", url_path="inventory"),
        st.Page("pages/2_대여신청.py", title="대여 신청", url_path="rental"),
        st.Page("pages/3_반납등록.py", title="반납 수량 등록", url_path="returns"),
        st.Page("pages/4_대여현황.py", title="대여 현황 조회", url_path="history"),
        st.Page("pages/5_AI챗봇.py", title="AI 챗봇", url_path="chatbot"),
    ],
    position="sidebar",
)
page.run()
