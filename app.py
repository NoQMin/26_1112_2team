from datetime import date

import pandas as pd
import streamlit as st

from llm import ChatError, get_reply, MAX_QUESTION
from rental_service import (
    RentalError,
    init_data,
    items,
    stock_on,
    create_rental,
    register_return,
    rental_status_rows,
)

st.set_page_config(
    page_title="바로대여 | 행사 물품 대여",
    page_icon="📦",
    layout="wide",
)

init_data()

st.title("📦 바로대여 | 행사 물품 대여 관리 시스템")
st.caption("날짜별 재고 조회 · 대여 신청 · 반납 관리 · AI 챗봇")

with st.sidebar:
    st.header("메뉴")
    menu = st.radio(
        "이용할 기능",
        [
            "대여 가능 수량 조회 + AI 챗봇",
            "대여 신청",
            "반납 수량 등록",
            "대여 현황 조회",
        ],
    )

    st.divider()
    st.caption("수업용 프로젝트입니다.")

try:
    item_list = items()
except (RentalError, ValueError, OSError) as exc:
    st.error(f"데이터 파일 오류: {exc}")
    st.stop()


# ==========================================
# F-01 날짜별 대여 가능 수량 조회 + AI 챗봇
# ==========================================

if menu == "대여 가능 수량 조회 + AI 챗봇":

    st.subheader("F-01 · 날짜별 대여 가능 수량 조회")

    selected_day = st.date_input(
        "조회 날짜",
        value=date.today(),
    )

    try:
        stock = stock_on(selected_day)

        st.dataframe(
            pd.DataFrame(stock),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "미반납 물품은 반납 예정일이 지나도 "
            "실제 반납되기 전까지 대여 중으로 계산합니다."
        )

    except (RentalError, ValueError, OSError) as exc:
        st.error(str(exc))
        st.stop()

    st.divider()

    # ======================================
    # F-05 AI 챗봇
    # ======================================

    st.subheader("🤖 AI 대여 수량 상담")

    st.caption(
        "CSV 파일의 실제 재고를 확인하고 "
        "Ollama AI 모델이 한국어로 답변합니다."
    )

    st.info(
        '질문 예시: "11월 20일 의자 몇 개 남았어?" '
        '/ "내일 천막 5개 대여 가능해?"'
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()

    # 기존 대화 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 새로운 질문 입력
    question = st.chat_input(
        "대여 가능 수량을 질문하세요",
        max_chars=MAX_QUESTION,
    )

    if question:

        with st.chat_message("user"):
            st.markdown(question)

        try:
            with st.spinner("AI가 재고를 확인하고 있습니다..."):
                answer = get_reply(
                    st.session_state.messages,
                    question,
                    selected_day,
                )

        except (ChatError, RentalError, ValueError, OSError) as exc:
            st.error(str(exc))
            st.info("AI 연결이 안 되더라도 위의 재고 조회는 사용할 수 있습니다.")

        else:
            st.session_state.messages.extend(
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
            )

            with st.chat_message("assistant"):
                st.markdown(answer)


# ==========================================
# F-02 대여 신청
# ==========================================

elif menu == "대여 신청":

    st.subheader("F-02 · 대여 신청")

    if not item_list:
        st.warning("등록된 물품이 없습니다.")
        st.stop()

    labels = {
        item["item_id"]: f"{item['name']} ({item['item_id']})"
        for item in item_list
    }

    with st.form("rental_form"):

        item_id = st.selectbox(
            "물품 선택",
            options=list(labels),
            format_func=lambda key: labels[key],
        )

        left, right = st.columns(2)

        start = left.date_input(
            "대여 시작일",
            value=date.today(),
        )

        end = right.date_input(
            "반납 예정일",
            value=date.today(),
        )

        qty = st.number_input(
            "신청 수량",
            min_value=1,
            step=1,
            value=1,
        )

        submitted = st.form_submit_button(
            "대여 신청",
            type="primary",
        )

    if submitted:
        try:
            number = create_rental(
                item_id,
                start,
                end,
                int(qty),
            )

            st.success(
                f"신청이 등록되었습니다. 신청번호: {number}"
            )

        except (RentalError, OSError, ValueError) as exc:
            st.error(str(exc))


# ==========================================
# F-03 반납 수량 등록
# ==========================================

elif menu == "반납 수량 등록":

    st.subheader("F-03 · 반납 수량 등록")

    rows = [
        row
        for row in rental_status_rows()
        if row["미반납 수량"] > 0
    ]

    if not rows:
        st.info("미반납 대여 신청이 없습니다.")

    else:
        by_id = {
            row["신청번호"]: row
            for row in rows
        }

        number = st.selectbox(
            "미반납 신청 선택",
            list(by_id),
            format_func=lambda n: (
                f"{n} · {by_id[n]['물품명']} · "
                f"미반납 {by_id[n]['미반납 수량']}개"
            ),
        )

        record = by_id[number]

        st.write(
            f"신청 수량: **{record['신청 수량']}개** / "
            f"누적 반납: **{record['누적 반납 수량']}개** / "
            f"미반납: **{record['미반납 수량']}개**"
        )

        with st.form("return_form"):

            qty = st.number_input(
                "이번 반납 수량",
                min_value=1,
                max_value=record["미반납 수량"],
                step=1,
                value=1,
            )

            submitted = st.form_submit_button(
                "반납 등록",
                type="primary",
            )

        if submitted:
            try:
                result = register_return(
                    number,
                    int(qty),
                )

                st.success(
                    f"반납 등록 완료 · "
                    f"누적 {result['누적 반납 수량']}개 / "
                    f"미반납 {result['미반납 수량']}개 / "
                    f"{result['상태']}"
                )

                st.rerun()

            except (RentalError, OSError, ValueError) as exc:
                st.error(str(exc))


# ==========================================
# F-04 대여 현황 조회
# ==========================================

elif menu == "대여 현황 조회":

    st.subheader("F-04 · 대여 현황 조회")

    rows = rental_status_rows()

    left, right = st.columns(2)

    status = left.selectbox(
        "반납 상태",
        [
            "전체",
            "대여중",
            "일부반납",
            "반납완료",
            "기한 초과",
        ],
    )

    names = {
        item["item_id"]: item["name"]
        for item in item_list
    }

    item_id = right.selectbox(
        "물품 ID",
        ["전체"] + list(names),
        format_func=lambda key: (
            "전체"
            if key == "전체"
            else f"{names[key]} ({key})"
        ),
    )

    if status != "전체":
        if status == "기한 초과":
            rows = [
                row
                for row in rows
                if row["기한"] == "기한 초과"
            ]
        else:
            rows = [
                row
                for row in rows
                if row["상태"] == status
            ]

    if item_id != "전체":
        rows = [
            row
            for row in rows
            if row["물품 ID"] == item_id
        ]

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("조회 결과가 없습니다.")
