import pickle
import os

DATA_PATH = 'app/data/encodings.pkl'


def load_data():
    if not os.path.exists(DATA_PATH):
        return {"encodings": [], "names": []}
    with open(DATA_PATH, 'rb') as f:
        return pickle.load(f)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, 'wb') as f:
        pickle.dump(data, f)


def add_face(encoding, name):
    data = load_data()
    data['encodings'].append(encoding)
    data['names'].append(name)
    save_data(data)


def delete_face(name):
    data = load_data()
    indices = {i for i, n in enumerate(data['names']) if n == name}
    if not indices:
        return False
    data['encodings'] = [e for i, e in enumerate(data['encodings']) if i not in indices]
    data['names'] = [n for i, n in enumerate(data['names']) if i not in indices]
    save_data(data)
    return True


def list_names():
    data = load_data()
    return sorted(set(data['names']))


def get_enrolled_count():
    data = load_data()
    return len(set(data['names']))
