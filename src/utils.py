import json
from pathlib import Path

def load_json_list(path: Path, key: str) -> list[str]:
    if not path.exists():
        save_json_list([], path, key)
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get(key, [])


def save_json_list(items: list[str], path: Path, key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({key: items}, f, indent=2, ensure_ascii=False)