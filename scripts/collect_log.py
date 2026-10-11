"""Прогоняет обращения из demo/sample_tickets.txt через POST /triage и
сохраняет лог запрос/ответ — используется как доказательство работы
сервиса (п. "лог 60 откликов" в задании).

    python scripts/collect_log.py
    python scripts/collect_log.py --count 60 --url http://127.0.0.1:8000/triage
"""

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_FILE = ROOT / "demo" / "sample_tickets.txt"
LOG_FILE = ROOT / "demo" / "responses_log.txt"

CHANNELS = ["chat", "email", "form"]

STOP_SECTION = "ГРАНИЧНЫЕ СЛУЧАИ"


def load_tickets() -> list[str]:
    lines = SAMPLE_FILE.read_text(encoding="utf-8").splitlines()
    tickets = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("==="):
            if STOP_SECTION in line:
                break
            continue
        if line.startswith(("Примеры", "Копируйте", "Ожидаемая", "(совпадает")):
            continue  # instructional preamble, not a ticket
        tickets.append(line)
    return tickets


def send(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": json.loads(exc.read())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/triage")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()

    tickets = load_tickets()
    if not tickets:
        raise SystemExit("No tickets found in sample file")

    lines_out = [
        f"Лог прогона {args.count} обращений через POST {args.url}",
        f"Дата: {datetime.now(timezone.utc).isoformat()}",
        f"Источник текстов: {SAMPLE_FILE.relative_to(ROOT)}",
        "=" * 70,
        "",
    ]

    ok = 0
    escalated = 0
    for i in range(args.count):
        text = tickets[i % len(tickets)]
        channel = CHANNELS[i % len(CHANNELS)]
        client_id = f"log-client-{i + 1:03d}"
        payload = {"text": text, "channel": channel, "client_id": client_id}

        result = send(args.url, payload)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if result["status"] == 200:
            ok += 1
            b = result["body"]
            if b.get("escalate"):
                escalated += 1
            lines_out.append(
                f"[{i + 1:02d}] {ts} client={client_id} channel={channel}\n"
                f"     text: {text}\n"
                f"     -> category={b.get('category')} confidence={b.get('confidence')} "
                f"escalate={b.get('escalate')}\n"
                f"     draft_reply: {b.get('draft_reply')}\n"
            )
        else:
            lines_out.append(
                f"[{i + 1:02d}] {ts} client={client_id} channel={channel} "
                f"-> HTTP {result['status']}: {result['body']}\n"
            )

        print(f"[{i + 1}/{args.count}] status={result['status']}")
        time.sleep(args.delay)

    lines_out.append("=" * 70)
    lines_out.append(f"Итого: {args.count} запросов, {ok} успешных (200), эскалировано: {escalated}")

    LOG_FILE.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"\nЛог сохранён: {LOG_FILE}")
    print(f"Успешных: {ok}/{args.count}, эскалировано: {escalated}")


if __name__ == "__main__":
    main()
