from PIL import Image
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
from datetime import datetime
from pathlib import Path
import json
import re
import time
from pdf2image import convert_from_bytes
import logging
from typing import List, Dict, Any
import tempfile
from pdf2image import convert_from_path

from api_config import (
    VERKEERSBESLUITEN_DIR, AFBEELDINGEN_DIR, EXCLUDE_KEYWORDS,
    MIN_IMAGE_SIZE_BYTES, MIN_PDF_SIZE_BYTES, SRU_BASE_URL,
    SRU_VERSION, SRU_OPERATION, MAX_RECORDS_PER_REQUEST,
    REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES,
    RETRY_DELAY_MULTIPLIER, SUCCESSFUL_REQUESTS_TO_RESET,
    PDF_CONVERSION_DPI, SUPPORTED_EXTENSIONS, QUERY_TEMPLATE,
    REPOSITORY_BASE_URL, ZOEK_BASE_URL, get_api_base_url
)
from CLIP_image_classifier import get_classifier, should_download_image

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def make_rate_limited_request(url, timeout=REQUEST_TIMEOUT, **kwargs):
    """
    Make a HTTP request with adaptive rate limiting.
    - Activates rate limiting after 429 type errors
    - Resets rate limiting after consecutive successful requests
    """
    if not hasattr(make_rate_limited_request, '_rate_limited'):
        make_rate_limited_request._rate_limited = False
        make_rate_limited_request._last_request_time = 0
        make_rate_limited_request._successful_requests = 0
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                delay = REQUEST_DELAY * (RETRY_DELAY_MULTIPLIER ** (attempt - 1))
                logging.info(f"⏳ Retry attempt {attempt}: waiting {delay:.1f} seconds...")
                time.sleep(delay)
            elif make_rate_limited_request._rate_limited and attempt == 0:
                time_since_last = time.time() - make_rate_limited_request._last_request_time
                if time_since_last < REQUEST_DELAY:
                    sleep_time = REQUEST_DELAY - time_since_last
                    logging.info(f"⏳ Rate limiting active: waiting {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
            
            logging.info(f"🌐 Requesting: {url}")
            response = requests.get(url, timeout=timeout, **kwargs)
            make_rate_limited_request._last_request_time = time.time()
            
            if response.status_code == 429:
                if not make_rate_limited_request._rate_limited:
                    logging.warning(f"⚠️ First 429 error detected - rate limiting now active")
                    make_rate_limited_request._rate_limited = True
                make_rate_limited_request._successful_requests = 0
                
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                    logging.warning(f"⚠️ Rate limited (429). Waiting {wait_time} seconds as per Retry-After header...")
                    time.sleep(wait_time)
                else:
                    logging.warning(f"⚠️ Rate limited (429). Using exponential backoff...")
                continue
            
            if response.ok:
                logging.info(f"✅ Request successful: {response.status_code}")
                make_rate_limited_request._successful_requests += 1
                if (make_rate_limited_request._rate_limited and 
                    make_rate_limited_request._successful_requests >= SUCCESSFUL_REQUESTS_TO_RESET):
                    logging.info(f"🚀 Rate limiting disabled after {SUCCESSFUL_REQUESTS_TO_RESET} successful requests")
                    make_rate_limited_request._rate_limited = False
                    make_rate_limited_request._successful_requests = 0
            else:
                logging.warning(f"⚠️ Request failed: {response.status_code}")
                make_rate_limited_request._successful_requests = 0
            
            return response
            
        except requests.RequestException as e:
            logging.error(f"❌ Request error (attempt {attempt + 1}): {e}")
            make_rate_limited_request._successful_requests = 0
            if attempt == MAX_RETRIES:
                logging.error(f"❌ All {MAX_RETRIES + 1} retries failed for {url}")
                return None
    return None

def extract_plain_text_from_xml(xml_string: str) -> str:
    """Extracts plain text content from an XML string."""
    try:
        root = ET.fromstring(xml_string)
        return " ".join(root.itertext()).strip()
    except ET.ParseError as e:
        logging.error(f"❌ XML Parse error: {e}")
        return ""

def parse_metadata_block(meta_root: ET.Element) -> Dict[str, Any]:
    """Parses a metadata block from XML into a dictionary."""
    metadata = {}
    gebiedsmarkeringen = []
    for m in meta_root.findall("metadata"):
        name = m.attrib.get("name")
        content = m.attrib.get("content")
        if name == "OVERHEIDop.gebiedsmarkering":
            gebied = {"type": content}
            for sub in m.findall("metadata"):
                sub_name = sub.attrib.get("name")
                sub_content = sub.attrib.get("content")
                if sub_name == "OVERHEIDop.geometrie":
                    gebied["geometrie"] = sub_content
                elif sub_name == "OVERHEIDop.geometrieLabel":
                    gebied["label"] = sub_content
            gebiedsmarkeringen.append(gebied)
        elif name and content:
            metadata[name] = content.strip()
    if gebiedsmarkeringen:
        metadata["OVERHEIDop.gebiedsmarkering"] = gebiedsmarkeringen
    return metadata

def get_pdf_attachment_image_urls(exb_code: str) -> List[str]:
    """
    For a PDF attachment, returns direct URLs to a service that can convert its pages to images.
    This does NOT download the PDF.
    """
    # This URL points to the PDF itself. A separate process/service would be needed
    # to render a specific page from this PDF. For now, we return the PDF URL
    # and an indication of how to potentially access pages if a service supported it.
    # A real-world implementation might point to a pre-processing service.
    pdf_url = f"{REPOSITORY_BASE_URL}/externebijlagen/{exb_code}/1/bijlage/{exb_code}.pdf"
    logging.info(f"📃 Found PDF attachment URL: {pdf_url}")
    # Since we can't know the number of pages without downloading, we'll just return the main PDF url.
    # A client-side application or another service would be responsible for fetching and rendering pages.
    return [pdf_url]

def get_embedded_image_urls_from_xml(xml_string: str) -> List[str]:
    """
    Extracts direct URLs for embedded images from XML content without downloading them.
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        logging.error(f"❌ XML parsing error: {e}")
        return []
    
    image_urls = []
    for ill in root.findall(".//illustratie"):
        naam = ill.attrib.get("naam")
        if not naam:
            continue
        image_url = f"{ZOEK_BASE_URL}/{naam}"
        logging.info(f"🖼️ Found embedded image URL: {image_url}")
        image_urls.append(image_url)
    return image_urls

def get_besluiten_for_date(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetches all traffic decisions for a specific date, processes them,
    and returns a list of dictionaries containing the data.
    """
    logging.info(f"📅 Processing date: {date_str}")
    AFBEELDINGEN_DIR.mkdir(exist_ok=True)
    Image.MAX_IMAGE_PIXELS = None
    
    query = QUERY_TEMPLATE.format(
        date_start=date_str,
        date_end=date_str,
        exclude_keywords=" ".join(EXCLUDE_KEYWORDS)
    )
    params = {
        "version": SRU_VERSION,
        "operation": SRU_OPERATION,
        "query": query,
        "maximumRecords": str(MAX_RECORDS_PER_REQUEST)
    }
    ns = {"sru": "http://docs.oasis-open.org/ns/search-ws/sruResponse", "gzd": "http://standaarden.overheid.nl/sru"}
    
    response = make_rate_limited_request(SRU_BASE_URL, params=params)
    if not response or not response.ok:
        logging.warning(f"⚠️ Failed to get SRU data for {date_str}")
        return []
        
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        logging.error(f"❌ XML parsing error for {date_str}: {e}")
        return []

    records = root.findall(".//sru:recordData", ns)
    logging.info(f"📊 Found {len(records)} records for {date_str}")
    if not records:
        return []

    all_day_data = []
    for record in records:
        item_urls = {item.attrib.get("manifestation"): item.text for item in record.findall(".//gzd:itemUrl", ns)}
        content_url = item_urls.get("xml")
        metadata_url = item_urls.get("metadata")
        
        if not content_url:
            continue

        logging.info(f"📄 Processing document: {content_url}")
        xml_resp = make_rate_limited_request(content_url)
        if not xml_resp or not xml_resp.ok:
            continue
        
        content = xml_resp.content.decode("utf-8", errors="ignore")
        if any(k in content.lower() for k in EXCLUDE_KEYWORDS):
            logging.info("❌ Document excluded based on keywords.")
            continue

        filename = content_url.split("/")[-1]
        metadata = {}
        if metadata_url:
            meta_resp = make_rate_limited_request(metadata_url)
            if meta_resp and meta_resp.ok:
                meta_root = ET.fromstring(meta_resp.content)
                metadata = parse_metadata_block(meta_root)

        image_urls = []
        if metadata.get("OVERHEIDop.externeBijlage"):
            match = re.search(r"exb-[^/]+", metadata["OVERHEIDop.externeBijlage"])
            if match:
                image_urls.extend(get_pdf_attachment_image_urls(match.group(0)))
        
        image_urls.extend(get_embedded_image_urls_from_xml(content))

        combined_data = {
            "id": filename.replace(".xml", ""),
            "text": extract_plain_text_from_xml(content),
            "metadata": metadata,
            "images": image_urls
        }
        all_day_data.append(combined_data)

    logging.info(f"✅ Process for {date_str} complete. Found {len(all_day_data)} items.")
    return all_day_data 

def download_en_convert_pdf_bijlage(pdf_exb_code: str, besluit_id: str) -> str:
    """
    Downloads a PDF attachment and converts its first page to an image using BytesIO.
    Uses the PDF's exb_code for downloading but saves with the verkeersbesluit's ID.
    Returns the URL to access the saved image, or empty string if no image was saved.
    """
    url = f"{REPOSITORY_BASE_URL}/externebijlagen/{pdf_exb_code}/1/bijlage/{pdf_exb_code}.pdf"
    logging.info(f"⬇️ Downloading and converting: {url}")
    
    try:
        resp = make_rate_limited_request(url)
        if resp and resp.status_code == 200 and len(resp.content) > MIN_PDF_SIZE_BYTES:
            # Convert PDF bytes directly to images
            images = convert_from_bytes(resp.content, dpi=PDF_CONVERSION_DPI)
            
            if not images:
                logging.warning(f"❌ No pages found in PDF for {pdf_exb_code}")
                return ""
            
            # Only process the first page
            page = images[0]
            try:
                img_buffer = BytesIO()
                page.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()
                
                # Use the verkeersbesluit ID for the filename, not the PDF's exb_code
                output_path = AFBEELDINGEN_DIR / f"{besluit_id}_page_1_bijlage.png"
                if should_download_image(img_bytes):
                    page.save(output_path, "PNG")
                    relative_path = f"afbeeldingen/{besluit_id}_page_1_bijlage.png"
                    # image_url = f"{get_api_base_url()}/{relative_path}"
                    image_url = f"/{relative_path}"
                    logging.info(f"✅ Saved first page (map/aerial photo): {image_url}")
                    return image_url
                else:
                    logging.info(f"⏩ Skipped first page (not a map/aerial photo)")
                    return ""
                
            except Exception as e:
                logging.warning(f"⚠️ Error processing first page: {e}")
                
        else:
            logging.warning(f"❌ No valid PDF received for {pdf_exb_code}")
    except Exception as e:
        logging.error(f"⚠️ Error processing PDF: {e}")
    
    return ""