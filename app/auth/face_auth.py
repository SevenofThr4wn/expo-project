import face_recognition
import os
import numpy as np

AUTHORIZED_PATH = "app/data/authorized_faces"

class FaceAuth:
    def __init__(self):
        self.encodings = []
        self.names = []
        self.load_faces()

    def load_faces(self):
        for person in os.listdir(AUTHORIZED_PATH):
            person_path = os.path.join(AUTHORIZED_PATH, person)

            for file in os.listdir(person_path):
                img_path = os.path.join(person_path, file)

                image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    self.encodings.append(encodings[0])
                    self.names.append(person)

    def verify(self, frame):
        rgb = frame[:, :, ::-1]
        encodings = face_recognition.face_encodings(rgb)

        for encoding in encodings:
            distances = face_recognition.face_distance(self.encodings, encoding)

            if len(distances) == 0:
                return None

            best_idx = np.argmin(distances)

            if distances[best_idx] < 0.5:
                return self.names[best_idx]

        return None


face_auth = FaceAuth()