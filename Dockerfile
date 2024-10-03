# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Define environment variables
ENV MATTERMOST_URL="your-mattermost-url"
ENV MATTERMOST_TOKEN="your-mattermost-api-token"
ENV MATTERMOST_TEAM="your-team-name"

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install any necessary dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Make port 8065 available to the world outside this container (optional)
EXPOSE 8065

# Run bot.py when the container launches
CMD ["python", "./bot.py"]
