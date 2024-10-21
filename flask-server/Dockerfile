FROM python:3.12.2-slim

# Set the working directory
WORKDIR /flask-backend

# Copy the necessary files
COPY .env app.py ai_search_helper.py blob_storage_helper.py common_helper.py mongo_helper.py course_share_helper.py requirements.txt /flask-backend/

# Install necessary libraries (libmagic, libGL, libgthread, and others)
RUN apt-get update && apt-get install -y libmagic1 libgl1-mesa-glx libglib2.0-0 && apt-get clean

# Install Python dependencies
RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Start the app using gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "-w", "4", "--timeout", "600"]




# FROM python:3.12.2-slim

# WORKDIR /backend-deployment
# COPY .env app.py ai_search_helper.py blob_storage_helper.py common_helper.py mongo_helper.py course_share_helper.py requirements.txt /backend-deployment/

# RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# EXPOSE 5000

# CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "-w", "4", "--timeout", "600"]