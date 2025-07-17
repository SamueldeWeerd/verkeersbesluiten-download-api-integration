# CLIP Image Classifier API

A FastAPI service that provides a REST endpoint for classifying images using OpenAI's CLIP model. Determines whether images are maps, aerial/satellite images, or miscellaneous content.

## 🚀 Quick Start with Docker

### Build and run with Docker Compose (recommended):
```bash
docker-compose up --build
```

### Or build and run manually:
```bash
# Build the image
docker build -t clip-classifier-api .

# Run the container
docker run -p 8000:8000 clip-classifier-api
```

The API will be available at: **http://localhost:8000**

## 🔍 API Endpoints

### Health Check
```http
GET /health
```
Returns the health status of the API and CLIP model.

### Classify Single Image
```http
POST /classify
Content-Type: multipart/form-data

file: <image_file>
```

**Response:**
```json
{
  "filename": "example.jpg",
  "file_size_bytes": 156789,
  "is_map_or_aerial": true,
  "confidence": 0.87,
  "classification": "maps",
  "probabilities": {
    "maps": 0.87,
    "aerial_satellite": 0.08,
    "miscellaneous": 0.05
  },
  "would_download": true,
  "timestamp": "now"
}
```

## 🧪 Testing the API

### Interactive API Documentation
Visit **http://localhost:8000/docs** for Swagger UI documentation where you can test endpoints directly.

### Command Line Testing
```bash
# Test with the provided script
python test_api.py path/to/your/image.jpg

# Test with curl
curl -X POST "http://localhost:8000/classify" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@path/to/your/image.jpg"
```

### Python Client Example
```python
import requests

# Single image classification
with open('image.jpg', 'rb') as f:
    files = {'file': ('image.jpg', f, 'image/jpeg')}
    response = requests.post('http://localhost:8000/classify', files=files)
    result = response.json()
    
print(f"Would download: {result['would_download']}")
print(f"Classification: {result['classification']}")
print(f"Confidence: {result['confidence']:.2f}")
```

## ⚙️ Configuration

### Environment Variables
- `PYTHONUNBUFFERED=1` - For real-time logging in Docker

### Resource Requirements
- **Memory**: ~2-4GB (depending on CLIP model and concurrent requests)
- **CPU**: Multi-core recommended for better performance
- **GPU**: Optional but significantly improves classification speed

### Docker Image Size
- **Base image**: ~1.5GB (includes PyTorch and CLIP model)
- **Model download**: ~400MB on first run (cached afterward)

## 🔧 Development

### Local Development (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### API Structure
- `api.py` - FastAPI application with endpoints
- `image_classifier.py` - CLIP classification logic
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container definition
- `docker-compose.yml` - Easy deployment configuration

## 📊 Performance

### Typical Response Times
- **Single image**: 0.5-2 seconds (depending on image size and hardware)
- **First request**: May take longer due to CLIP model loading

### Limitations
- **Maximum file size**: 50MB per image (configurable)
- **Supported formats**: JPG, PNG, GIF, BMP, TIFF

## 🛠️ Troubleshooting

### Common Issues

**API won't start:**
- Check if port 8000 is available
- Ensure Docker has sufficient memory allocated (>4GB recommended)

**Classification errors:**
- Verify image format is supported
- Check image file isn't corrupted
- Ensure sufficient disk space for CLIP model

**Slow performance:**
- Use GPU-enabled Docker image for better performance
- Reduce image resolution for faster processing
- Consider increasing Docker memory allocation

### Logs
View container logs:
```bash
docker-compose logs -f clip-classifier
```

## 🚀 Production Deployment

### Scaling
- Use multiple container instances behind a load balancer
- Consider GPU-enabled instances for better performance
- Implement request queuing for high-volume scenarios

### Security
- Add authentication middleware if needed
- Implement rate limiting
- Use HTTPS in production
- Validate and sanitize file uploads

### Monitoring
- Health check endpoint: `/health`
- Metrics can be added using Prometheus/Grafana
- Log aggregation recommended for production use

## Koop API Integration

The `koop_api_integratie.py` script includes the image classifier for filtering traffic decision images and attachments. It now uses a **daily request strategy** to handle large date ranges without hitting API limits.

### Daily Request Structure

Instead of making one large request for an entire date range, the system now:

1. **Splits date ranges into individual days**: Each day gets its own API request
2. **Processes daily batches**: Maximum 900 records per day (API limit per request)
3. **Unlimited date ranges**: Can now process entire years without hitting limits
4. **Progress tracking**: Shows progress through each day with detailed logging
5. **Error resilience**: If one day fails, other days continue processing

### Benefits

- **No more 900-record limit**: Process unlimited date ranges
- **Better error handling**: Isolated failures per day
- **Progress visibility**: Clear progress reporting per day
- **Optimal API usage**: Stays within API limits while maximizing throughput

### Example Output

```
🚀 Starting download with daily requests and adaptive rate limiting
📅 Processing 365 days from 2023-01-01 to 2023-12-31

📅 Processing day 1/365: 2023-01-01
📊 Found 23 records for 2023-01-01
✅ Day 2023-01-01 completed: 23 documents processed

📅 Processing day 2/365: 2023-01-02
📊 Found 15 records for 2023-01-02
✅ Day 2023-01-02 completed: 15 documents processed

...

🎉 Download completed!
📅 Processed 365 days from 2023-01-01 to 2023-12-31
📄 Total documents processed: 8,543
📊 Average documents per day: 23.4
``` 