# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Define environment variables
ENV MATTERMOST_URL="your-mattermost-url"
ENV MATTERMOST_TOKEN="your-mattermost-api-token"
ENV MATTERMOST_TEAM="your-team-name"

# Declare build arguments
ARG GITHUB_REPOSITORY
ARG GIT_COMMIT_SHA
ARG VERSION

# Set OCI-compliant labels with placeholders for dynamic values
LABEL org.opencontainers.image.title="Mattermost Python Bot"
LABEL org.opencontainers.image.description="A Mattermost bot written in Python using the Mattermost API."
LABEL org.opencontainers.image.url="https://github.com/${GITHUB_REPOSITORY}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.authors="Hakan Tandogan <hakan@tandogan.com>"
LABEL org.opencontainers.image.vendor="AvArc"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/${GITHUB_REPOSITORY}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT_SHA}"
LABEL org.opencontainers.image.documentation="https://github.com/${GITHUB_REPOSITORY}/wiki"

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
