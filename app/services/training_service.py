import face_recognition
from app.stores.face_store import load_data, add_face


def train_from_images(name, image_files):
    added = 0
    skipped = 0
    for f in image_files:
        try:
            img = face_recognition.load_image_file(f)
            encodings = face_recognition.face_encodings(img)
            if not encodings:
                skipped += 1
                continue
            add_face(encodings[0], name)
            added += 1
        except Exception:
            skipped += 1
    return {"added": added, "skipped": skipped}


def get_training_stats():
    data = load_data()
    counts = {}
    for name in data["names"]:
        counts[name] = counts.get(name, 0) + 1
    return sorted(
        [{"name": n, "count": c} for n, c in counts.items()],
        key=lambda x: x["name"],
    )
