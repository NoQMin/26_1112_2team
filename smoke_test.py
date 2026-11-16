"""Read-only smoke check for the integrated app and Ollama chatbot."""
from datetime import date
from services.inventory import get_items, available_quantity
from services.chatbot import ChatError, get_reply


def main():
    today = date.today()
    items = get_items()
    if not items:
        raise SystemExit("No items registered.")
    for item in items:
        available = available_quantity(item["item_id"], today, today)
        print(f"{item['name']}: {available}/{item['total']}")
    try:
        print(get_reply([], f"{items[0]['name']} 1개 대여 가능해?", today))
    except ChatError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()