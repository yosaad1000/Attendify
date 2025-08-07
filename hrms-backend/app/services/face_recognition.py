import face_recognition
import numpy as np
import cv2
from PIL import Image
import io
import json
import os
from typing import List, Tuple, Optional
from ..core.config import settings

class FaceRecognitionService:
    def __init__(self):
        self.encodings_path = settings.FACE_ENCODINGS_PATH
        self.threshold = settings.FACE_RECOGNITION_THRESHOLD
        os.makedirs(self.encodings_path, exist_ok=True)
    
    def extract_face_encoding(self, image_data: bytes) -> Optional[List[float]]:
        """Extract face encoding from image data"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image_array)
            
            if not face_locations:
                return None
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            if not face_encodings:
                return None
            
            # Return the first face encoding
            return face_encodings[0].tolist()
            
        except Exception as e:
            print(f"Error extracting face encoding: {e}")
            return None
    
    def save_face_encoding(self, student_id: str, encoding: List[float]) -> bool:
        """Save face encoding to file"""
        try:
            encoding_file = os.path.join(self.encodings_path, f"{student_id}.json")
            with open(encoding_file, 'w') as f:
                json.dump(encoding, f)
            return True
        except Exception as e:
            print(f"Error saving face encoding: {e}")
            return False
    
    def load_face_encoding(self, student_id: str) -> Optional[List[float]]:
        """Load face encoding from file"""
        try:
            encoding_file = os.path.join(self.encodings_path, f"{student_id}.json")
            if os.path.exists(encoding_file):
                with open(encoding_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error loading face encoding: {e}")
            return None
    
    def recognize_faces_in_image(self, image_data: bytes, known_encodings: dict) -> List[dict]:
        """
        Recognize faces in an image and return matches
        
        Args:
            image_data: Image bytes
            known_encodings: Dict of {student_id: encoding}
        
        Returns:
            List of recognized faces with student_id and confidence
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(image_array)
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            recognized_faces = []
            
            for i, face_encoding in enumerate(face_encodings):
                best_match = None
                best_distance = float('inf')
                
                # Compare with known encodings
                for student_id, known_encoding in known_encodings.items():
                    if known_encoding:
                        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                        
                        if distance < self.threshold and distance < best_distance:
                            best_distance = distance
                            best_match = student_id
                
                # Get face location
                top, right, bottom, left = face_locations[i]
                
                recognized_faces.append({
                    'student_id': best_match,
                    'confidence': 1 - best_distance if best_match else 0,
                    'face_location': {
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left
                    }
                })
            
            return recognized_faces
            
        except Exception as e:
            print(f"Error recognizing faces: {e}")
            return []
    
    def draw_face_rectangles(self, image_data: bytes, recognized_faces: List[dict]) -> bytes:
        """Draw rectangles around recognized faces"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Draw rectangles
            for face in recognized_faces:
                loc = face['face_location']
                top, right, bottom, left = loc['top'], loc['right'], loc['bottom'], loc['left']
                
                # Choose color based on recognition
                color = (0, 255, 0) if face['student_id'] else (0, 0, 255)  # Green if recognized, red if not
                
                # Draw rectangle
                cv2.rectangle(cv_image, (left, top), (right, bottom), color, 2)
                
                # Add label
                label = face['student_id'] if face['student_id'] else 'Unknown'
                cv2.putText(cv_image, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Convert back to PIL Image
            pil_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            return img_byte_arr.getvalue()
            
        except Exception as e:
            print(f"Error drawing face rectangles: {e}")
            return image_data

# Global instance
face_recognition_service = FaceRecognitionService()