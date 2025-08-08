import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import face_recognition
from typing import List, Tuple, Optional
from config import settings

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    """Enhanced face recognition service for HRMS"""
    
    def __init__(self):
        self.threshold = settings.FACE_THRESHOLD
    
    def detect_faces(self, image_data: bytes) -> Tuple[np.ndarray, List[Tuple]]:
        """Detect faces in image and return image array and face locations"""
        try:
            # Load image from bytes
            image = Image.open(BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            np_image = np.array(image)
            face_locations = face_recognition.face_locations(np_image, model="hog")
            
            logger.info(f"Detected {len(face_locations)} faces in image")
            return np_image, face_locations
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            raise
    
    def encode_face(self, np_image: np.ndarray, face_location: Tuple) -> np.ndarray:
        """Generate face encoding for a specific face location"""
        try:
            face_encodings = face_recognition.face_encodings(np_image, [face_location])
            if not face_encodings:
                raise ValueError("Could not encode face")
            
            return np.array(face_encodings[0], dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Error encoding face: {e}")
            raise
    
    def compare_faces(self, known_encoding: List[float], face_encoding: np.ndarray) -> Tuple[bool, float]:
        """Compare face encodings and return match status and distance"""
        try:
            known_array = np.array(known_encoding, dtype=np.float32)
            distance = face_recognition.face_distance([known_array], face_encoding)[0]
            is_match = distance < self.threshold
            
            return is_match, float(distance)
            
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return False, 1.0
    
    def draw_face_rectangles(self, np_image: np.ndarray, face_locations: List[Tuple], 
                           names: List[str], student_ids: List[str] = None) -> Image.Image:
        """Draw rectangles around faces with names"""
        try:
            pil_image = Image.fromarray(np_image)
            draw = ImageDraw.Draw(pil_image)
            
            # Try to load a font, fallback to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            student_ids = student_ids or [None] * len(face_locations)
            
            for (top, right, bottom, left), name, student_id in zip(face_locations, names, student_ids):
                # Choose color based on recognition status
                color = (0, 255, 0) if student_id else (255, 0, 0)  # Green if recognized, red if not
                
                # Draw rectangle
                draw.rectangle([(left, top), (right, bottom)], outline=color, width=3)
                
                # Draw name label
                text_bbox = draw.textbbox((0, 0), name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Background for text
                draw.rectangle(
                    [(left, bottom), (left + text_width + 10, bottom + text_height + 10)],
                    fill=color
                )
                
                # Text
                draw.text((left + 5, bottom + 5), name, fill=(255, 255, 255), font=font)
            
            return pil_image
            
        except Exception as e:
            logger.error(f"Error drawing face rectangles: {e}")
            return Image.fromarray(np_image)
    
    def crop_face(self, pil_image: Image.Image, face_location: Tuple) -> str:
        """Crop face from image and return base64 string"""
        try:
            top, right, bottom, left = face_location
            
            # Add padding around face
            padding = 20
            width, height = pil_image.size
            
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(width, right + padding)
            bottom = min(height, bottom + padding)
            
            face_img = pil_image.crop((left, top, right, bottom))
            
            # Convert to base64
            buffer = BytesIO()
            face_img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode('ascii')
            
        except Exception as e:
            logger.error(f"Error cropping face: {e}")
            return ""
    
    def image_to_base64(self, pil_image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        try:
            buffer = BytesIO()
            pil_image.save(buffer, format="JPEG", quality=90)
            return base64.b64encode(buffer.getvalue()).decode('ascii')
            
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""

# Global instance
face_service = FaceRecognitionService()