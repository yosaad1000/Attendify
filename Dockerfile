# Use the face recognition base image
FROM animcogn/face_recognition

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose the Flask port
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]