import json
import uuid
from pathlib import Path
from datetime import datetime

CORRECTIONS_DIR = Path(__file__).resolve().parents[2] / "data" / "corrections"


def save_correction(image_id: str, original_text: str,
                    corrected_text: str, word_corrections: list[dict]) -> str:
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    correction_id = str(uuid.uuid4())
    record = {
        "id": correction_id,
        "image_id": image_id,
        "original_text": original_text,
        "corrected_text": corrected_text,
        "word_corrections": word_corrections,
        "timestamp": datetime.utcnow().isoformat(),
    }

    filepath = CORRECTIONS_DIR / f"{correction_id}.json"
    filepath.write_text(json.dumps(record, indent=2))

    return correction_id


def list_corrections() -> list[dict]:
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in sorted(CORRECTIONS_DIR.glob("*.json")):
        results.append(json.loads(f.read_text()))
    return results
