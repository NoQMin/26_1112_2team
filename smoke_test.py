from datetime import date

from llm import ChatError, get_reply
from rental_service import (
    RentalError,
    init_data,
    items,
    stock_on,
)


def main():
    print("=" * 50)
    print("바로대여 시스템 테스트")
    print("=" * 50)

    # 1. CSV 데이터 확인
    print("\n[1] CSV 데이터 확인")

    try:
        init_data()

        item_list = items()

        print("CSV 데이터 연결 성공")

        for item in item_list:
            print(
                f"- {item['name']}: "
                f"{item['total_quantity']}개"
            )

    except (RentalError, ValueError, OSError) as exc:
        print(f"CSV 데이터 오류: {exc}")
        return

    # 2. 대여 가능 수량 확인
    print("\n[2] 대여 가능 수량 조회")

    try:
        today = date.today()

        stock_list = stock_on(today)

        print(f"조회 날짜: {today}")

        for stock in stock_list:
            print(
                f"- {stock['물품명']}: "
                f"보유 {stock['보유 수량']}개 / "
                f"대여 중 {stock['대여 중 수량']}개 / "
                f"대여 가능 {stock['대여 가능 수량']}개"
            )

        print("재고 조회 성공")

    except (RentalError, ValueError, OSError) as exc:
        print(f"재고 조회 오류: {exc}")
        return

    # 3. AI 챗봇 테스트
    print("\n[3] AI 챗봇 연결 테스트")

    question = "오늘 의자 30개 대여 가능해?"

    print(f"질문: {question}")

    try:
        answer = get_reply(
            history=[],
            question=question,
            selected_date=date.today(),
        )

        print("\nAI 답변:")
        print(answer)

        print("\nAI 챗봇 테스트 성공")

    except ChatError as exc:
        print(f"\nAI 연결 오류: {exc}")
        print(
            "Ollama가 실행 중인지, "
            "모델이 설치되어 있는지 확인하세요."
        )

    print("\n테스트 종료")


if __name__ == "__main__":
    main()
