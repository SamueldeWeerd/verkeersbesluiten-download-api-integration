from fastapi import FastAPI, File, UploadFile, HTTPException, Path as FastApiPath
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import io
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our image classifier
try:
    from CLIP_image_classifier import get_classifier
    from get_besluiten_for_date import get_besluiten_for_date, download_en_convert_pdf_bijlage
    logger.info("✅ Classifier and besluiten fetcher imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import modules: {e}")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="Verkeersbesluiten API",
    description="API for classifying images and retrieving traffic decisions (verkeersbesluiten).",
    version="1.1.0"
)

# Mount the static files directory
app.mount("/afbeeldingen", StaticFiles(directory="afbeeldingen"), name="afbeeldingen")

# Global classifier instance (lazy loaded)
classifier = None

def get_classifier_instance():
    """Get or create the classifier instance."""
    global classifier
    if classifier is None:
        classifier = get_classifier()
        logger.info("🤖 CLIP classifier initialized")
    return classifier

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "CLIP Image Classifier API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        # Test if classifier can be loaded
        get_classifier_instance()
        return {
            "status": "healthy",
            "classifier": "loaded",
            "message": "API is ready to classify images"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "classifier": "failed",
                "error": str(e)
            }
        )

@app.get("/besluiten/{date_str}", summary="Get traffic decisions for a specific date")
async def get_besluiten_by_date(
    date_str: str = FastApiPath(..., description="Date in YYYY-MM-DD format", regex=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Retrieves all traffic decisions for a given date.
    
    It fetches the data, processes it, downloads relevant images, and returns a JSON
    object containing the metadata, text, and URLs to the images.
    """
    try:
        # Validate date format (though regex in Path helps)
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use YYYY-MM-DD."
        )
    
    logger.info(f"🚀 Fetching traffic decisions for {date_str}")
    
    try:
        # Call the processing function from the other module
        besluiten_data = get_besluiten_for_date(date_str)
        
        if not besluiten_data:
            return JSONResponse(
                status_code=404,
                content={"message": f"No traffic decisions found for {date_str}"}
            )

        # Convert PDF to images and save them to the images directory
        # If url contains 'externebijlagen' then it is a PDF, so convert it to images and paste url to image converted from PDF in besluiten_data['images'][0]
        for besluit in besluiten_data:
            if besluit['images'] and 'externebijlagen' in besluit['images'][0]:
                # Extract exb_code from the PDF URL
                pdf_url = besluit['images'][0]
                import re
                match = re.search(r'exb-[^/]+', pdf_url)
                if match:
                    pdf_exb_code = match.group(0)
                    besluit_id = besluit['id']
                    image_url = download_en_convert_pdf_bijlage(pdf_exb_code, besluit_id)
                    if image_url:  # Only update if we got a valid URL back
                        besluit['images'][0] = image_url
                        logger.info(f"✅ PDF converted to image: {image_url}")
                    else:
                        # Remove the PDF URL since no image was created
                        besluit['images'] = []
                        logger.info(f"⏩ PDF skipped (not a map/aerial photo), removed from images: {besluit['id']}")

            
            
        logger.info(f"✅ Found {len(besluiten_data)} decisions for {date_str}")
        return besluiten_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching decisions for {date_str}: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@app.post("/classify")
async def classify_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Classify an uploaded image using CLIP.
    
    Returns:
        - is_map_or_aerial: boolean indicating if image should be downloaded
        - confidence: overall confidence score (0-1)
        - classification: best matching category
        - probabilities: detailed probabilities for each category
        - filename: original filename
    """
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Received: {file.content_type}"
        )
    
    try:
        # Read image file
        contents = await file.read()
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty file received")
        
        # Get classifier
        classifier_instance = get_classifier_instance()
        
        # Classify image
        logger.info(f"🔍 Classifying image: {file.filename} ({len(contents)} bytes)")
        result = classifier_instance.classify_image_from_bytes(contents)
        
        if result.get('error'):
            logger.error(f"Classification error: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Classification failed: {result['error']}")
        
        # Prepare response
        response = {
            "filename": file.filename,
            "file_size_bytes": len(contents),
            "is_map_or_aerial": result['is_map_or_aerial'],
            "confidence": result['confidence'],
            "classification": result['classification'],
            "probabilities": result['probabilities'],
            "would_download": result['is_map_or_aerial'],
            "timestamp": "now"
        }
        
        logger.info(f"✅ Classification complete: {file.filename} -> {result['classification']} (confidence: {result['confidence']:.2f})")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing image {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 