"""
Export Router
Handles data export endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from typing import Optional, List
from datetime import datetime
import logging

from app.services.export_service import ExportService
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/export")
async def export_data(
    collection: str = Query(..., description="Collection to export"),
    format: str = Query("json", description="Export format: json, csv, or xlsx"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to include"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Export data from a collection
    
    Supported formats:
    - json: Full JSON export with nested structures
    - csv: Flat CSV format (Excel compatible)
    - xlsx: Excel file format
    
    Example:
        GET /api/export?collection=products&format=csv&fields=name,price
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        export_service = ExportService(db)
        
        # Parse fields
        field_list = None
        if fields:
            field_list = [f.strip() for f in fields.split(",")]
        
        # Export based on format
        if format == "json":
            content = await export_service.export_to_json(
                user_id=str(current_user["_id"]),
                collection=collection,
                fields=field_list
            )
            media_type = "application/json"
            filename = f"{collection}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
        elif format == "csv":
            content = await export_service.export_to_csv(
                user_id=str(current_user["_id"]),
                collection=collection,
                fields=field_list
            )
            media_type = "text/csv"
            filename = f"{collection}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif format == "xlsx":
            content = await export_service.export_to_excel(
                user_id=str(current_user["_id"]),
                collection=collection,
                fields=field_list
            )
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{collection}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Use json, csv, or xlsx"
            )
        
        await increment_api_calls(current_user["_id"])
        
        # Return file
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content))
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )

@router.get("/export/preview")
async def preview_export(
    collection: str = Query(..., description="Collection to preview"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Preview export statistics
    
    Returns information about the data that would be exported:
    - Number of records
    - Available fields
    - Estimated file sizes
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        export_service = ExportService(db)
        
        stats = await export_service.get_export_stats(
            user_id=str(current_user["_id"]),
            collection=collection
        )
        
        await increment_api_calls(current_user["_id"])
        
        # Estimate file sizes (rough estimates)
        record_count = stats['count']
        field_count = len(stats['fields'])
        
        # Rough estimates: 100 bytes per field per record
        estimated_json_size = record_count * field_count * 100
        estimated_csv_size = record_count * field_count * 50
        estimated_xlsx_size = record_count * field_count * 80
        
        return {
            "success": True,
            "collection": collection,
            "record_count": record_count,
            "fields": stats['fields'],
            "field_count": field_count,
            "estimated_sizes": {
                "json_kb": round(estimated_json_size / 1024, 2),
                "csv_kb": round(estimated_csv_size / 1024, 2),
                "xlsx_kb": round(estimated_xlsx_size / 1024, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview failed: {str(e)}"
        )