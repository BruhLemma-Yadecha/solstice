# WebSocket Setup for Real-time Job Status Updates

This setup replaces periodic API polling with real-time WebSocket connections for job status updates.

## Architecture

- **Port 8000**: HTTP API (Gunicorn)
- **Port 8001**: WebSocket server (Daphne)
- **Redis**: Channel layer for WebSocket messaging

## Setup Instructions

### 1. Build and Run with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 2. Services Started

- `web`: HTTP API server (port 8000)
- `websocket`: WebSocket server (port 8001) 
- `redis`: Message broker
- `db`: PostgreSQL database
- `worker`: Celery worker for background tasks

### 3. Frontend Configuration

The frontend automatically connects to:
- HTTP API: `http://127.0.0.1:8000/jobs/`
- WebSocket: `ws://127.0.0.1:8001/ws/jobs/`

## WebSocket Endpoints

### Job List Updates
- **URL**: `ws://127.0.0.1:8001/ws/jobs/`
- **Purpose**: Real-time updates for all jobs
- **Messages**:
  - `job_list`: Complete list refresh
  - `job_update`: Single job status change

### Individual Job Updates  
- **URL**: `ws://127.0.0.1:8001/ws/jobs/{job_id}/`
- **Purpose**: Updates for a specific job
- **Messages**: 
  - `job_status_update`: Status change for the job

## Features

✅ **Real-time updates**: No more polling - instant job status changes
✅ **Live indicator**: Shows WebSocket connection status in UI
✅ **Automatic reconnection**: Handles network interruptions
✅ **Fallback support**: Initial data load via HTTP API

## Testing

1. **Start the services**:
   ```bash
   docker-compose up --build
   ```

2. **Open the frontend**: Navigate to job list page

3. **Watch for live indicator**: Should show "Live" with green dot

4. **Test updates**: Upload a video and watch status change in real-time

## Troubleshooting

### WebSocket shows "Offline"
- Check if port 8001 is accessible
- Verify Redis is running: `docker ps | grep redis`
- Check WebSocket server logs: `docker logs solstice_websocket`

### No real-time updates
- Check Django signals are working
- Verify Redis connection in Django settings
- Check browser console for WebSocket errors

### Development Mode
For local development without Docker:
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Django with ASGI
python manage.py runserver

# Terminal 3: Start Daphne for WebSockets  
daphne -p 8001 solstice.asgi:application
```
