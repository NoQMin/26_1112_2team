"""Ollama 기반 재고 상담 화면."""
from datetime import date
import streamlit as st

st.title("AI 챗봇")
st.caption("실제 CSV 재고와 서비스 규칙을 바탕으로 대여 가능 수량을 안내합니다.")
try:
    from services.chatbot import ChatError, get_reply, MAX_QUESTION, MAX_HISTORY
except ModuleNotFoundError:
    st.error("챗봇 연동 패키지가 설치되지 않았습니다.")
    st.code("python -m pip install -r requirements.txt", language="bash")
    st.stop()

selected_day = st.date_input("조회 기준일", min_value=date.today(), key="chat_date")
st.caption("질문에 날짜가 있으면 그 날짜를 우선합니다. 여러 날 대여는 재고 조회 메뉴에서 전체 기간을 확인해 주세요.")
st.info('예: "내일 노트북 3개 대여 가능해?" / "오늘 빔프로젝터 몇 개 남았어?"')
if "rental_chat_messages" not in st.session_state:
    st.session_state.rental_chat_messages = []
if st.button("대화 초기화", key="clear_chat"):
    st.session_state.rental_chat_messages = []
    st.rerun()

for message in st.session_state.rental_chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("대여 가능 수량을 질문하세요", max_chars=MAX_QUESTION, key="rental_chat_input")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    try:
        with st.spinner("AI가 재고를 확인하고 있습니다..."):
            answer = get_reply(st.session_state.rental_chat_messages, question, selected_day)
    except (ChatError, ValueError, OSError) as exc:
        st.error(str(exc))
        st.info("AI 연결 상태와 관계없이 재고 조회·대여 신청·반납 기능은 이용할 수 있습니다.")
    else:
        st.session_state.rental_chat_messages.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        st.session_state.rental_chat_messages = st.session_state.rental_chat_messages[-MAX_HISTORY:]
        with st.chat_message("assistant"):
            st.markdown(answer)
