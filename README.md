# Document Extractor

AI-powered document extraction system for college admissions. Extracts structured data from transcripts, ID documents, and certificates using OCR and LLMs.

## Features

- **Multi-format Support**: PDF, JPG, PNG, DOCX
- **AI-Powered Extraction**: EasyOCR + Tesseract for OCR, Ollama + Gemini for field extraction
- **Confidence Scoring**: Per-field and overall confidence scores
- **Template System**: Pre-built templates for transcripts, IDs, and certificates
- **REST API**: FastAPI endpoints for single and batch processing
- **Background Processing**: Celery + Redis for heavy workloads

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Ollama (for local LLM)

```bash
ollama pull llama3.2
ollama serve
```

### 4. Run the API

```bash
uvicorn src.main:app --reload
```

## API Usage

### Extract Single Document

```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@transcript.pdf" \
  -F "document_type=transcript"
```

### Response Example

```json
{
  "document_id": "abc123",
  "status": "completed",
  "document_type": "transcript",
  "extracted_data": {
    "student_name": "John Smith",
    "institution_name": "State University",
    "gpa": 3.75
  },
  "field_confidences": {
    "student_name": 0.95,
    "institution_name": 0.92,
    "gpa": 0.88
  },
  "overall_confidence": 0.92,
  "requires_review": false
}
```

### Batch Processing

```bash
curl -X POST "http://localhost:8000/extract/batch" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.jpg"
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `GEMINI_API_KEY` | - | Google Gemini API key (fallback) |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for Celery |
| `CONFIDENCE_THRESHOLD` | `0.8` | Min confidence for auto-accept |

## Project Structure

```
src/
├── main.py              # FastAPI application
├── processor.py         # Core processing pipeline
├── config.py            # Configuration management
├── tasks.py             # Celery background tasks
├── ingestion/           # Document loading (PDF, Image, DOCX)
├── preprocessing/       # Image enhancement for OCR
├── extraction/          # OCR and LLM extraction
├── templates/           # Document templates
└── output/              # Schemas and database models
```

## Celery Workers (for heavy processing)

```bash
# Start Redis
docker run -d -p 6379:6379 redis

# Start Celery worker
celery -A src.tasks worker --loglevel=info
```

## License

MIT
