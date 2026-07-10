from __future__ import annotations

from haccp.graph.graph import run_workflow


def main() -> None:
    sample_payload = {
        "telegram_user_id": "123456789",
        "chat_id": "123456789",
        "input_kind": "text",
        "raw_text": "купихме стоки и фактура",
    }
    result = run_workflow(sample_payload)
    print(result)


if __name__ == "__main__":
    main()
