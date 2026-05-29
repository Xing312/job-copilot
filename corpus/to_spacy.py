"""
Convert corpus/annotations.json to spaCy .spacy training files.
Run this inside the Docker backend container:

  docker compose exec backend python /app/corpus/to_spacy.py

Outputs:
  corpus/train.spacy  (80%)
  corpus/dev.spacy    (20%)
"""

import json
import random
from pathlib import Path

import spacy
from spacy.tokens import DocBin

ANNOTATIONS_PATH = Path(__file__).parent / "annotations.json"
TRAIN_PATH = Path(__file__).parent / "train.spacy"
DEV_PATH = Path(__file__).parent / "dev.spacy"
SEED = 42


def main():
    nlp = spacy.blank("en")
    examples = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))

    random.seed(SEED)
    random.shuffle(examples)
    split = int(len(examples) * 0.8)
    train_data, dev_data = examples[:split], examples[split:]

    def to_docbin(data: list) -> DocBin:
        db = DocBin()
        skipped = 0
        for ex in data:
            doc = nlp.make_doc(ex["text"])
            ents = []
            for e in ex["entities"]:
                span = doc.char_span(e["start"], e["end"], label=e["label"])
                if span is None:
                    skipped += 1
                    continue
                ents.append(span)
            doc.ents = ents
            db.add(doc)
        if skipped:
            print(f"  Skipped {skipped} misaligned spans")
        return db

    print(f"Train: {len(train_data)} examples")
    to_docbin(train_data).to_disk(TRAIN_PATH)

    print(f"Dev:   {len(dev_data)} examples")
    to_docbin(dev_data).to_disk(DEV_PATH)

    print(f"Saved → {TRAIN_PATH}, {DEV_PATH}")


if __name__ == "__main__":
    main()
