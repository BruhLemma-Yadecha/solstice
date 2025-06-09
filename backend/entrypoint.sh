#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Change the ownership of the media and static volumes to the 'app' user.
# This ensures that the application has the necessary permissions to write to these directories.
# We use 'chown' on the specific directories mounted as volumes.
if [ -d "/app/media" ]; then
    echo "Updating media volume ownership..."
    chown -R app:app /app/media
else
    echo "Media directory not found, skipping ownership update..."
fi

# Execute the main command provided to the container (e.g., gunicorn, celery, etc.)
# "$@" passes all arguments from the docker-compose 'command' to this script.
# 'exec' replaces the shell process with the command's process, which is important
# for proper signal handling (e.g., for graceful shutdowns).
exec "$@"