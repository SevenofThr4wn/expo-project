import face_recognition
import numpy as np

def detect_faces(frame):
    rgb = frame[:, :, ::-1]  # BGR to RGB
    boxes = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, boxes)
    return boxes, encodings

def match_face(encoding, known_encodings, known_names, tolerance=0.5):
    if len(known_encodings) == 0:
        return "unknown", 0
    
    distances = face_recognition.face_distance(known_encodings, encoding)
    best_idx = np.argmin(distances)

    if distances[best_idx] < tolerance:
        confidence = int((1 - distances[best_idx]) * 100) # Convert to percentage
        return known_names[best_idx], confidence
    return "unknown", int((1 - distances[best_idx]) * 100)
