"""
OCR (Optical Character Recognition) Router
Extract text from images and PDFs using Tesseract
Similar to Adobe Acrobat OCR
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
import pytesseract
from PIL import Image
import io
import tempfile
import os

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/ocr", tags=["OCR Document Recognition"])


class OCRResult(BaseModel):
    """OCR extraction result"""
    text: str
    confidence: Optional[float] = None
    language: str = "eng"
    page_count: int = 1


class OCRRequest(BaseModel):
    """OCR processing request"""
    data_id: str
    language: str = "eng+kor"  # English + Korean
    detect_orientation: bool = True


# Tesseract configuration
# For Windows: Set path if tesseract is not in PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Supported languages
SUPPORTED_LANGUAGES = {
    "eng": "English",
    "kor": "Korean",
    "jpn": "Japanese",
    "chi_sim": "Chinese Simplified",
    "chi_tra": "Chinese Traditional",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish"
}


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported OCR languages
    """
    
    return {
        "success": True,
        "languages": SUPPORTED_LANGUAGES,
        "default": "eng+kor",
        "note": "You can combine languages with '+' (e.g., 'eng+kor')"
    }


@router.post("/extract", response_model=OCRResult)
async def extract_text_from_upload(
    file: UploadFile = File(...),
    language: str = Query("eng+kor", description="OCR language (e.g., 'eng+kor')"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Extract text from uploaded image or PDF
    
    Supports:
    - Images: JPG, PNG, TIFF, BMP
    - PDF: Single or multi-page
    
    Language codes:
    - eng: English
    - kor: Korean
    - eng+kor: English + Korean (recommended)
    """
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file type
    content_type = file.content_type
    filename = file.filename.lower()
    
    # Read file content
    content = await file.read()
    
    try:
        # Handle images
        if content_type.startswith('image/') or filename.endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp')):
            image = Image.open(io.BytesIO(content))
            
            # Perform OCR
            text = pytesseract.image_to_string(image, lang=language)
            
            # Get confidence (optional)
            try:
                data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except:
                avg_confidence = None
            
            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence,
                language=language,
                page_count=1
            )
        
        # Handle PDFs
        elif content_type == 'application/pdf' or filename.endswith('.pdf'):
            # For PDF, we need pdf2image
            try:
                from pdf2image import convert_from_bytes
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF processing requires 'pdf2image' and 'poppler' to be installed"
                )
            
            # Convert PDF to images
            images = convert_from_bytes(content)
            
            # Extract text from all pages
            all_text = []
            all_confidences = []
            
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image, lang=language)
                all_text.append(f"--- Page {i+1} ---\n{page_text}")
                
                try:
                    data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    if confidences:
                        all_confidences.extend(confidences)
                except:
                    pass
            
            combined_text = "\n\n".join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else None
            
            return OCRResult(
                text=combined_text.strip(),
                confidence=avg_confidence,
                language=language,
                page_count=len(images)
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {content_type}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.post("/process/{data_id}")
async def process_stored_document(
    data_id: str,
    language: str = Query("eng+kor", description="OCR language"),
    save_text: bool = Query(True, description="Save extracted text to database"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Process OCR on a stored document
    
    Extracts text and optionally saves it to the database
    for future searching
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    # Get document
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # For now, return message that file needs to be uploaded for OCR
    # In production, you would fetch the file from R2/MongoDB and process it
    
    return {
        "success": True,
        "message": "To process OCR, please use the /ocr/extract endpoint with file upload",
        "data_id": data_id,
        "note": "Future versions will support direct OCR of stored files"
    }


@router.get("/stats")
async def get_ocr_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get OCR processing statistics
    """
    
    db = await get_database()
    
    # Get OCR history
    ocr_history = await db.ocr_history.count_documents({
        "user_id": str(current_user["_id"])
    })
    
    # Get total pages processed
    pipeline = [
        {
            "$match": {
                "user_id": str(current_user["_id"])
            }
        },
        {
            "$group": {
                "_id": None,
                "total_pages": {"$sum": "$page_count"},
                "avg_confidence": {"$avg": "$confidence"}
            }
        }
    ]
    
    stats = await db.ocr_history.aggregate(pipeline).to_list(None)
    
    if stats:
        total_pages = stats[0].get("total_pages", 0)
        avg_confidence = stats[0].get("avg_confidence", 0)
    else:
        total_pages = 0
        avg_confidence = 0
    
    return {
        "success": True,
        "stats": {
            "total_documents": ocr_history,
            "total_pages": total_pages,
            "average_confidence": round(avg_confidence, 2) if avg_confidence else None
        },
        "supported_languages": len(SUPPORTED_LANGUAGES),
        "ocr_engine": "Tesseract OCR"
    }


@router.get("/test")
async def test_ocr_installation():
    """
    Test if Tesseract OCR is properly installed
    """
    
    try:
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        
        # Try to get available languages
        langs = pytesseract.get_languages()
        
        return {
            "success": True,
            "tesseract_installed": True,
            "version": str(version),
            "available_languages": langs,
            "message": "Tesseract OCR is properly installed and configured"
        }
    
    except Exception as e:
        return {
            "success": False,
            "tesseract_installed": False,
            "error": str(e),
            "message": "Tesseract OCR is not installed or not in PATH",
            "installation_guide": {
                "windows": "Download from: https://github.com/UB-Mannheim/tesseract/wiki",
                "macos": "brew install tesseract",
                "linux": "sudo apt-get install tesseract-ocr",
                "note": "After installation, you may need to restart the application"
            }
        }


@router.post("/batch")
async def batch_ocr(
    files: List[UploadFile] = File(...),
    language: str = Query("eng+kor", description="OCR language"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Process multiple files in batch
    """
    
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per batch"
        )
    
    results = []
    errors = []
    
    for file in files:
        try:
            content = await file.read()
            
            # Simple image processing (full implementation similar to extract endpoint)
            if file.content_type.startswith('image/'):
                image = Image.open(io.BytesIO(content))
                text = pytesseract.image_to_string(image, lang=language)
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "text_length": len(text),
                    "preview": text[:100] + "..." if len(text) > 100 else text
                })
            else:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "Only images supported in batch mode"
                })
        
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": True,
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors if errors else None
    }