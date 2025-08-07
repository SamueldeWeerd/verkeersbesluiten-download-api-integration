# CLIP Image Classification for Traffic Decisions

This project now includes intelligent image filtering using OpenAI's CLIP model to automatically identify and download only relevant traffic-related images (maps, satellite images, and aerial photos) while filtering out text documents, road signs without maps, and other irrelevant content.

## 🧠 How It Works

The system uses a CLIP (Contrastive Language-Image Pre-training) model to classify images into three categories:
1. **Maps/Schematic maps** - Street maps, city maps, road maps, topographic maps
2. **Satellite/Aerial images** - Satellite images, aerial photographs, bird's eye views  
3. **Text/Signs** - Text documents, road signs, traffic signs, forms

Only images classified as maps or aerial/satellite images are downloaded to save storage space and processing time.

## 📁 New Files

### `image_classifier.py`
Contains the core CLIP classification logic:
- `ImageClassifier` class with methods for classifying images from bytes, files, or PIL objects
- Configurable confidence thresholds
- Convenience functions for easy integration

### `test_image_classifier.py`  
Test script to verify the classifier works correctly with sample images from your `afbeeldingen/` folder.

## 🔧 Setup & Dependencies

### Required Dependencies
Make sure you have these Python packages installed:

```bash
# Core ML dependencies
pip install torch torchvision

# CLIP model
pip install clip-by-openai

# Image processing (likely already installed)
pip install Pillow

# PDF processing (likely already installed)  
pip install pdf2image
```

### GPU Support (Optional but Recommended)
For faster processing, install CUDA-enabled PyTorch if you have an NVIDIA GPU:

```bash
# For CUDA 11.8 (check your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## 🚀 Usage

### Automatic Integration
The image classifier is automatically integrated into your existing `koop_api_integratie.py` workflow:

```bash
python koop_api_integratie.py
```

The script will now:
1. Download traffic decision documents as before
2. **NEW**: Classify each image/PDF page before saving
3. Only save images that are classified as maps or aerial/satellite images
4. Log classification statistics

### Testing the Classifier
Test the classifier with a specific image:

```bash
python test_image_classifier.py path/to/your/image.png
```

Examples:
```bash
python test_image_classifier.py afbeeldingen/gmb-2024-1880-1.png
python test_image_classifier.py /full/path/to/image.jpg
```

This will:
- Load the CLIP model
- Analyze the specified image
- Show whether it would be downloaded (map/aerial) or skipped
- Display confidence scores for each category

### Manual Classification
You can also use the classifier programmatically:

```python
from image_classifier import get_classifier, should_download_image

# Initialize classifier (lazy-loaded singleton)
classifier = get_classifier()

# Classify from file path
result = classifier.classify_image_from_path("path/to/image.png")
print(f"Is map/aerial: {result['is_map_or_aerial']}")
print(f"Confidence: {result['confidence']:.2f}")

# Quick decision for download
image_bytes = open("image.png", "rb").read()
should_download = should_download_image(image_bytes)
```

## ⚙️ Configuration

### Confidence Threshold
You can adjust the classification sensitivity by modifying the `confidence_threshold` in `image_classifier.py`:

```python
# In ImageClassifier.__init__()
self.confidence_threshold = 0.4  # Lower = more permissive, Higher = more strict
```

### Classification Prompts
The text prompts used for classification can be customized:

```python
self.classification_prompts = [
    "a map, a schematic map, a city map, a road map, a topographic map",
    "a satellite image, an aerial photograph, an aerial view, a bird's eye view", 
    "text document, a road sign, a traffic sign, plain text, a form"
]
```

## 📊 What's Changed in the Main Script

### PDF Processing (`download_en_convert_pdf_bijlage`)
- Each PDF page is now classified before saving
- Only pages containing maps/aerial images are saved
- Shows statistics: "X/Y pages saved"
- Fallback: saves image if classification fails

### Embedded Images (`download_embedded_images_from_xml`)
- Each embedded image is classified before saving
- Non-map images are skipped entirely
- Logs why images were skipped or saved

### Logging
- New classification statistics in the final summary
- Enhanced logging shows which images were saved vs. skipped

## 🔍 Output Examples

### Console Output
```
🖼️ Afbeelding gevonden: https://zoek.officielebekendmakingen.nl/image123.png
✅ Afbeelding opgeslagen (kaart/luchtfoto): afbeeldingen/image123.png

📄 Converting PDF page 1...
✅ Opgeslagen (kaart/luchtfoto): afbeeldingen/exb-2024-123_page_1_bijlage.png
⏩ Overgeslagen pagina 2 (geen kaart/luchtfoto)
📊 1/2 pagina's opgeslagen voor exb-2024-123
```

### Classification Results
```python
{
    'is_map_or_aerial': True,
    'confidence': 0.87,
    'probabilities': {
        'maps': 0.87,
        'aerial_satellite': 0.08,
        'text_signs': 0.05
    },
    'classification': 'maps'
}
```

## 🛠️ Troubleshooting

### CLIP Model Not Loading
If you get CLIP import errors:
```bash
pip install ftfy regex tqdm
pip install clip-by-openai
```

### CUDA Out of Memory
If you get GPU memory errors:
```python
# Force CPU usage in image_classifier.py
classifier = ImageClassifier(device="cpu")
```

### Slow Performance
- First run downloads the CLIP model (~400MB)
- GPU acceleration significantly improves speed
- Consider increasing confidence thresholds to be more selective

## 📈 Performance Impact

### Benefits
- Reduces storage usage by filtering irrelevant images
- Saves time by not processing text-only documents
- Improves data quality for downstream analysis

### Considerations  
- Initial model download (~400MB) on first run
- Small processing overhead per image (~0.1-0.5 seconds)
- Uses ~1-2GB GPU memory when available

## 🔧 Advanced Usage

### Batch Processing Existing Images
If you want to classify existing images in your `afbeeldingen/` folder:

```python
from pathlib import Path
from image_classifier import get_classifier

classifier = get_classifier()
afbeeldingen_dir = Path("afbeeldingen")

for img_path in afbeeldingen_dir.glob("*.png"):
    result = classifier.classify_image_from_path(str(img_path))
    if not result['is_map_or_aerial']:
        print(f"Consider removing: {img_path} (classified as {result['classification']})")
```

### Custom Classification Classes
You can modify the prompts to create custom classification categories specific to your needs.

---

## 🚀 Next Steps

1. **Run the test script** to verify everything works
2. **Run your normal workflow** - it will now filter images automatically
3. **Monitor the logs** to see classification statistics
4. **Adjust thresholds** if needed based on your results

The system is designed to be conservative - if there's any uncertainty, it will save the image to avoid missing important content. 