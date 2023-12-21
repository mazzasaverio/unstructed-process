# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Uvicorn for running the application
RUN pip install --no-cache-dir uvicorn

# Make sure client.properties is included and accessible
COPY client.properties /app/client.properties

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV PORT=8080

# Run uvicorn when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
