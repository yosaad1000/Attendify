import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
import face_recognition

from config import config

logger = logging.getLogger(__name__)

class FaceService:
    """
    Service for face recognition operations
    """
    
    @staticmethod
    def detect_faces(image_data):
        """
        Detect faces in the given image
        
        Args:
            image_data: Binary image data
        
        Returns:
            np_image: Numpy array of the image
            face_locations: List of face locations (top, right, bottom, left)
        """
        np_image = face_recognition.load_image_file(BytesIO(image_data))
        face_locations = face_recognition.face_locations(np_image)
        return np_image, face_locations
    
    @staticmethod
    def encode_face(np_image, face_location):
        """
        Generate face encoding for a face
        
        Args:
            np_image: Numpy array of the image
            face_location: Face location (top, right, bottom, left)
        
        Returns:
            Face encoding as a numpy array
        """
        face_encodings = face_recognition.face_encodings(np_image, [face_location])
        if not face_encodings:
            raise ValueError("Could not encode face")
        
        return np.array(face_encodings[0], dtype=np.float32)
    
    @staticmethod
    def draw_face_rectangles(np_image, face_locations, names, student_ids=None):
        """
        Draw rectangles around faces with names
        
        Args:
            np_image: Numpy array of the image
            face_locations: List of face locations
            names: List of names corresponding to face_locations
            student_ids: List of student IDs (optional)
        
        Returns:
            PIL Image with rectangles drawn
        """
        pil_image = Image.fromarray(np_image)
        draw = ImageDraw.Draw(pil_image)
        
        student_ids = student_ids or [None] * len(face_locations)
        
        for (top, right, bottom, left), name, student_id in zip(face_locations, names, student_ids):
            # Draw rectangle around the face
            color = (0, 255, 0) if student_id else (255, 0, 0)  # Green if recognized, red if not
            draw.rectangle(((left, top), (right, bottom)), outline=color, width=5)
            
            # Draw label below the face
            text_width, text_height = draw.textsize(name)
            draw.rectangle(((left, bottom), (right, bottom + text_height + 10)), fill=color)
            draw.text((left + 6, bottom + 6), name, fill=(0, 0, 0))
        
        return pil_image
    
    @staticmethod
    def crop_face(pil_image, face_location):
        """
        Crop a face from the image
        
        Args:
            pil_image: PIL Image
            face_location: Face location (top, right, bottom, left)
        
        Returns:
            Base64 encoded string of the cropped face
        """
        top, right, bottom, left = face_location
        face_img = pil_image.crop((left, top, right, bottom))
        
        # Convert to base64
        face_img_io = BytesIO()
        face_img.save(face_img_io, 'JPEG')
        face_img_io.seek(0)
        
        return base64.b64encode(face_img_io.getvalue()).decode('ascii')
    
    @staticmethod
    def image_to_base64(pil_image):
        """
        Convert PIL Image to base64 string
        
        Args:
            pil_image: PIL Image
        
        Returns:
            Base64 encoded string of the image
        """
        buffer = BytesIO()
        pil_image.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode('ascii')