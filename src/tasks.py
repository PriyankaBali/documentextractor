"""Celery tasks for background document processing."""

from celery import Celery
from celery.result import AsyncResult

from .config import get_settings
from .processor import DocumentProcessor
from .output.schemas import DocumentStatus

settings = get_settings()

# Initialize Celery
celery_app = Celery(
    "document_extractor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,  # Process one task at a time for heavy workloads
)

# Global processor (initialized per worker)
_processor = None


def get_processor():
    """Get or create processor instance."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


@celery_app.task(bind=True, name="process_document")
def process_document_task(
    self,
    content_base64: str,
    filename: str,
    document_type: str | None = None,
) -> dict:
    """Process a single document asynchronously.
    
    Args:
        content_base64: Base64 encoded file content.
        filename: Original filename.
        document_type: Optional document type hint.
        
    Returns:
        Extraction result as dictionary.
    """
    import base64
    from .output.schemas import DocumentTypeEnum
    
    # Decode content
    content = base64.b64decode(content_base64)
    
    # Parse document type
    doc_type_hint = None
    if document_type:
        try:
            doc_type_hint = DocumentTypeEnum(document_type)
        except ValueError:
            pass
    
    # Process document
    processor = get_processor()
    result = processor.process_file(
        content=content,
        filename=filename,
        document_type_hint=doc_type_hint,
    )
    
    # Return serializable result
    return result.response.model_dump(mode="json")


@celery_app.task(bind=True, name="process_batch")
def process_batch_task(
    self,
    documents: list[dict],
    callback_url: str | None = None,
) -> dict:
    """Process multiple documents as a batch.
    
    Args:
        documents: List of {"content_base64": str, "filename": str}.
        callback_url: Optional URL to POST results.
        
    Returns:
        Batch result with all extractions.
    """
    import base64
    import httpx
    
    processor = get_processor()
    results = []
    
    for i, doc in enumerate(documents):
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": i + 1, "total": len(documents)},
        )
        
        try:
            content = base64.b64decode(doc["content_base64"])
            result = processor.process_file(
                content=content,
                filename=doc["filename"],
            )
            results.append(result.response.model_dump(mode="json"))
        except Exception as e:
            results.append({
                "filename": doc.get("filename", "unknown"),
                "status": "failed",
                "error": str(e),
            })
    
    batch_result = {
        "batch_id": self.request.id,
        "total_documents": len(documents),
        "status": "completed",
        "results": results,
    }
    
    # Send callback if configured
    if callback_url:
        try:
            httpx.post(callback_url, json=batch_result, timeout=30)
        except Exception:
            pass  # Ignore callback errors
    
    return batch_result


def get_task_status(task_id: str) -> dict:
    """Get status of a background task.
    
    Args:
        task_id: Celery task ID.
        
    Returns:
        Task status and result if available.
    """
    result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": result.status,
    }
    
    if result.ready():
        if result.successful():
            response["result"] = result.get()
        else:
            response["error"] = str(result.result)
    elif result.status == "PROGRESS":
        response["progress"] = result.info
    
    return response
