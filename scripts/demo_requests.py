"""Прогоняет набор примеров обращений через POST /triage.

Используется для демо-видео и для сбора лога ответов (см. README).

    python scripts/demo_requests.py
    python scripts/demo_requests.py --url http://127.0.0.1:8000/triage --repeat 5
"""

import argparse
import json
import time
import urllib.error
import urllib.request

SAMPLE_TICKETS = [
    {"text": "Списали деньги два раза за один заказ, прошу вернуть лишний платёж.", "channel": "email", "client_id": "client-001"},
    {"text": "Не могу войти в личный кабинет, кнопка входа не реагирует.", "channel": "form", "client_id": "client-002"},
    {"text": "Это уже третий раз, когда курьер привозит товар с опозданием! Очень недовольна сервисом.", "channel": "chat", "client_id": "client-003"},
    {"text": "Подскажите, пожалуйста, работаете ли вы по выходным?", "channel": "chat", "client_id": "client-004"},
    {"text": "Хочу вернуть товар, но не знаю, как оформить возврат на сайте.", "channel": "form", "client_id": "client-005"},
    {"text": "Оплата прошла, а статус заказа до сих пор 'в обработке' уже 5 дней.", "channel": "email", "client_id": "client-006"},
]


def send(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": json.loads(exc.read())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/triage")
    parser.add_argument("--repeat", type=int, default=1, help="сколько раз прогнать весь набор")
    parser.add_argument("--delay", type=float, default=0.2, help="пауза между запросами, сек")
    args = parser.parse_args()

    for cycle in range(args.repeat):
        for ticket in SAMPLE_TICKETS:
            result = send(args.url, ticket)
            print(f"[{cycle + 1}] -> {ticket['text'][:50]!r}")
            print(f"    status={result['status']} body={result['body']}")
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
