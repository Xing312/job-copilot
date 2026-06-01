"""
Fine-tune spaCy NER for Job Copilot: JOB_TITLE + COMPANY entities.
Starts from en_core_web_sm (reuses its tok2vec + existing NER weights).

Run inside Docker:
  docker compose exec backend python /app/corpus/train.py

Output:
  /app/corpus/job_copilot_ner/  (best checkpoint by dev F-score)
"""

import json
import random
from pathlib import Path

import spacy
from spacy.training import Example
from spacy.util import compounding, minibatch

CORPUS_DIR = Path(__file__).parent
ANNOTATIONS_PATH = CORPUS_DIR / "annotations.json"
MODEL_OUTPUT = CORPUS_DIR / "job_copilot_ner"
SEED = 42
N_ITER = 50
PATIENCE = 10
DROPOUT = 0.3
LABELS = ["JOB_TITLE", "COMPANY"]


def load_split_data():
    data = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    random.seed(SEED)
    random.shuffle(data)
    split = int(len(data) * 0.8)
    return data[:split], data[split:]


def to_examples(nlp, data):
    examples = []
    skipped = 0
    for item in data:
        doc = nlp.make_doc(item["text"])
        entities = []
        for e in item["entities"]:
            span = doc.char_span(e["start"], e["end"], label=e["label"])
            if span is None:
                skipped += 1
                continue
            entities.append((e["start"], e["end"], e["label"]))
        examples.append(Example.from_dict(doc, {"entities": entities}))
    if skipped:
        print(f"  Warning: skipped {skipped} misaligned spans")
    return examples


def main():
    print("Loading en_core_web_sm (tok2vec + ner only)...")
    nlp = spacy.load(
        "en_core_web_sm",
        exclude=["tagger", "parser", "senter", "attribute_ruler", "lemmatizer"],
    )

    ner = nlp.get_pipe("ner")
    for label in LABELS:
        ner.add_label(label)

    train_raw, dev_raw = load_split_data()
    print(f"Train: {len(train_raw)} | Dev: {len(dev_raw)}")

    train_examples = to_examples(nlp, train_raw)
    dev_examples = to_examples(nlp, dev_raw)

    # Initialize: allocates weights for new labels, preserves existing tok2vec weights
    nlp.initialize(get_examples=lambda: train_examples)
    optimizer = nlp.resume_training()

    MODEL_OUTPUT.mkdir(parents=True, exist_ok=True)
    best_f = 0.0
    no_improve = 0

    print(f"\n{'Epoch':>5}  {'Loss':>8}  {'P':>6}  {'R':>6}  {'F':>6}")
    print("-" * 42)

    for epoch in range(1, N_ITER + 1):
        random.shuffle(train_examples)
        losses = {}
        for batch in minibatch(train_examples, size=compounding(4.0, 16.0, 1.001)):
            nlp.update(batch, drop=DROPOUT, losses=losses, sgd=optimizer)

        scores = nlp.evaluate(dev_examples)
        f = scores["ents_f"]
        p = scores["ents_p"]
        r = scores["ents_r"]
        loss = losses.get("ner", 0.0)

        flag = "  *" if f > best_f else ""
        print(f"{epoch:5d}  {loss:8.2f}  {p:.3f}  {r:.3f}  {f:.3f}{flag}")

        if f > best_f:
            best_f = f
            no_improve = 0
            nlp.to_disk(MODEL_OUTPUT)
        else:
            no_improve += 1
            if no_improve >= PATIENCE:
                print(f"Early stopping: no improvement for {PATIENCE} epochs.")
                break

    print(f"\nBest dev F: {best_f:.3f}  ->  {MODEL_OUTPUT}")

    # Per-label breakdown from best saved checkpoint
    best_nlp = spacy.load(str(MODEL_OUTPUT))
    best_examples = to_examples(best_nlp, dev_raw)
    final = best_nlp.evaluate(best_examples)
    print("\nPer-label (best checkpoint):")
    for label in LABELS:
        s = final.get("ents_per_type", {}).get(label, {})
        print(f"  {label:<12}  P={s.get('p', 0):.3f}  R={s.get('r', 0):.3f}  F={s.get('f', 0):.3f}")


if __name__ == "__main__":
    main()
