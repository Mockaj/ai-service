# Use an official lightweight Python image.
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /www

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Make the startup script executable
RUN chmod +x ./startup.sh

RUN echo "Starting the FastAPI app..."

# Assuming your startup.sh script is now simplified for just running the FastAPI app.
CMD [ "./startup.sh" ]
