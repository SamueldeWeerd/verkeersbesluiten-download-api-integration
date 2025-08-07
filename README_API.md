# Verkeersbesluiten API Integration

A FastAPI service that provides REST endpoints for retrieving and filtering traffic decisions (verkeersbesluiten) from the Dutch government's KOOP API. The service includes optional CLIP-based image classification to prevent downloading non-relevant images.

## 🚀 Quick Start with Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

The API will be available at: **http://localhost:8001**

## 🔍 API Endpoints

### Health Check
```http
GET /health
```
Returns the health status of the API.

### Get Traffic Decisions
```http
GET /besluiten/{start_date_str}/{end_date_str}
```

Retrieves traffic decisions for a given date range with optional filtering.

**Parameters:**
- `start_date_str`: Start date in YYYY-MM-DD format
- `end_date_str`: End date in YYYY-MM-DD format
- `bordcode_categories` (optional): Filter by traffic sign categories (A, C, D, F, G)
- `provinces` (optional): Filter by Dutch provinces (case-insensitive)
- `gemeenten` (optional): Filter by municipalities (case-insensitive)

**Example Requests:**
```bash
# Get all decisions for a date range
curl "http://localhost:8001/besluiten/2024-01-01/2024-01-02"

# Filter by bordcode categories
curl "http://localhost:8001/besluiten/2024-01-01/2024-01-02?bordcode_categories=A&bordcode_categories=C"

# Filter by provinces
curl "http://localhost:8001/besluiten/2024-01-01/2024-01-02?provinces=utrecht&provinces=gelderland"

# Filter by municipalities
curl "http://localhost:8001/besluiten/2024-01-01/2024-01-02?gemeenten=amsterdam&gemeenten=rotterdam"

# Combine multiple filters
curl "http://localhost:8001/besluiten/2024-01-01/2024-01-02?bordcode_categories=A&provinces=utrecht&gemeenten=amsterdam"
```

**Response:**
```json
[
  {
    "id": "gmb-2024-12345",
    "text": "De burgemeester en wethouders van gemeente...",
    "metadata": {
      "OVERHEIDop.verkeersbordcode": "C1",
      "OVERHEID.authority": "Amsterdam",
      "DC.creator": "Noord-Holland",
      "OVERHEIDop.gebiedsmarkering": [
        {
          "type": "Lijn",
          "geometrie": "POINT(4.8896 52.3740)",
          "label": "Hoofdweg 123"
        }
      ],
      "OVERHEIDop.externeBijlage": "exb-2024-67890",
      "exb_code": "exb-2024-67890"
    },
    "images": [
      "http://localhost:8001/afbeeldingen/exb-2024-67890_page_1_bijlage.png"
    ]
  }
]
```

## ⚙️ Configuration

### Environment Variables
```yaml
# API Settings
VERKEERSBESLUIT_API__HOST=0.0.0.0
VERKEERSBESLUIT_API__PORT=8000
VERKEERSBESLUIT_API__PROTOCOL=http

# Rate Limiting
VERKEERSBESLUIT_RATE_LIMIT__REQUEST_TIMEOUT=30
VERKEERSBESLUIT_RATE_LIMIT__CONNECT_TIMEOUT=10
VERKEERSBESLUIT_RATE_LIMIT__MAX_RETRIES=3
VERKEERSBESLUIT_RATE_LIMIT__MAX_RETRY_DELAY=10.0

# Logging
VERKEERSBESLUIT_LOGGING__LEVEL=INFO
```

### Docker Network
The service is configured to run on the `n8n-network` network, making it accessible to other containers as `koop-api-service:8001`.

## 📊 Performance & Features

### Rate Limiting & Resilience
- Adaptive rate limiting with exponential backoff
- Automatic retries for failed requests
- Configurable timeouts and retry limits

### Filtering Capabilities
- **Bordcode Categories**: Filter by traffic sign types (A, C, D, F, G)
- **Provinces**: Filter by Dutch provinces (case-insensitive)
- **Municipalities**: Filter by gemeente names (case-insensitive)
- Early filtering before image processing for better performance

### Image Processing
- Automatic conversion of PDF attachments to images
- CLIP model classification to identify maps and aerial photos
  - Note: While another AI later in the workflow can also classify images, using CLIP here saves bandwidth and storage by preventing downloads of non-relevant images
- Local storage of relevant images in `afbeeldingen/` directory

### Logging
- Detailed logging of processing steps
- Filter application logging
- Image classification decisions
- Error and retry information

## 🏗️ Project Structure

```
src/
├── api/
│   ├── main.py           # FastAPI application setup
│   ├── models/           # Pydantic models
│   └── routes/           # API endpoints
├── services/
│   └── besluit_download_service.py  # Core business logic
├── utils/
│   ├── filters.py        # Filter implementations
│   ├── http_client.py    # Rate-limited HTTP client
│   └── xml_parser.py     # XML processing utilities
├── ml/
│   └── clip_classifier.py # Image classification
└── config/
    └── settings.py       # Configuration management
```

## 🛠️ Development

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
```

### Docker Setup
```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f koop-api-service
```

## 📝 Notes

### CLIP Model Usage
The service uses OpenAI's CLIP model to classify images as maps or aerial photos. While this classification could be done later in the workflow, performing it here offers several advantages:

1. **Storage Efficiency**: Only relevant images (maps/aerial photos) are saved
2. **Bandwidth Optimization**: Prevents unnecessary downloads
3. **Early Filtering**: Reduces downstream processing load

However, if your workflow already includes reliable image classification, you could consider removing the CLIP component to simplify the service.

### Rate Limiting Strategy
The service implements an adaptive rate-limiting strategy to respect API limits while maintaining good performance:

1. Base delay between requests (2 seconds)
2. Exponential backoff on failures
3. Success counter to gradually reduce delays
4. Maximum retry and delay caps

This ensures reliable operation even with large date ranges or high request volumes.