# Configuration file for KOOP API integration

import os
from datetime import datetime, timedelta
from pathlib import Path

# === API URL SETTINGS ===
# Base URL for the API service, can be overridden with environment variables
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8001")
API_PROTOCOL = os.getenv("API_PROTOCOL", "http")

def get_api_base_url() -> str:
    """Returns the base URL for the API service based on configuration."""
    return f"{API_PROTOCOL}://{API_HOST}:{API_PORT}"

# === DATE RANGE SETTINGS ===
# Format: YYYY-MM-DD
API_DATE_START = "2022-01-01"
API_DATE_END = "2024-12-01"

# === DIRECTORY SETTINGS ===
# Base directories for storing downloaded files
VERKEERSBESLUITEN_DIR = Path(__file__).parent / "verkeersbesluiten"
AFBEELDINGEN_DIR = Path(__file__).parent / "afbeeldingen"

# === KEYWORD FILTERING ===
# Documents containing these keywords will be excluded
EXCLUDE_KEYWORDS = [
    "parkeerplaats", "laadpaal", "gehandicapt", "oplaadpunt",
    "parkeerverbod", "parkeervergunning", "parkeerregime",
    "parkeermogelijkheden", "parkeervoorzieningen",
    "parkeersituatie", "parkeersituaties", "parkeerplaatsen",
    "parkeerplaatsvoorzieningen"
]

# === FILE SIZE SETTINGS ===
# Minimum file size in bytes for downloaded images/PDFs
MIN_IMAGE_SIZE_BYTES = 50000  # 50KB
MIN_PDF_SIZE_BYTES = 50000    # 50KB

# === API SETTINGS ===
# SRU API configuration
SRU_BASE_URL = "https://repository.overheid.nl/sru"
SRU_VERSION = "2.0"
SRU_OPERATION = "searchRetrieve"
MAX_RECORDS_PER_REQUEST = 900

# Request timeout settings (in seconds)
REQUEST_TIMEOUT = 10

# === RATE LIMITING SETTINGS ===
# Delay between requests to prevent 429 errors (in seconds)
REQUEST_DELAY = 2.0
# Maximum number of retries for failed requests
MAX_RETRIES = 3
# Delay multiplier for exponential backoff on retries
RETRY_DELAY_MULTIPLIER = 2
# Number of successful requests needed to reset rate limiting
SUCCESSFUL_REQUESTS_TO_RESET = 5

# === PDF CONVERSION SETTINGS ===
# DPI setting for PDF to image conversion
PDF_CONVERSION_DPI = 300

# === SUPPORTED FILE EXTENSIONS ===
SUPPORTED_EXTENSIONS = [".pdf", ".jpg", ".png", ".jpeg"]

# === API QUERY TEMPLATE ===
# Base query template - dates will be inserted automatically
QUERY_TEMPLATE = """(c.product-area==officielepublicaties AND dt.modified>={date_start} AND dt.modified<={date_end} AND dt.type = "verkeersbesluit " AND cql.allRecords =1 NOT dt.title any "{exclude_keywords}" AND cql.allRecords=1 NOT dt.alternative any "{exclude_keywords}" )"""

# === LOGGING SETTINGS ===
LOG_LEVEL = "INFO"
LOG_FILE = "download.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# === EXTERNAL URLS ===
REPOSITORY_BASE_URL = "https://repository.officiele-overheidspublicaties.nl"
ZOEK_BASE_URL = "https://zoek.officielebekendmakingen.nl" 