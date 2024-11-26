# Use an official Python base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the backend files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the server port
EXPOSE 8000

# Command to run the FastAPI server
CMD ["uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
