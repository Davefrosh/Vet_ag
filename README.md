# ARCON Vetting API

A stateless ReAct agent built with LangGraph and GPT-4o-mini to vet advertising content against ARCON regulations. Served as a REST API via FastAPI and deployed on Google Cloud Run.

## Architecture

- **API**: FastAPI (`src/main.py`)
- **Agent**: Stateless ReAct Agent (`src/agent.py`) using `langgraph`
- **LLM**: GPT-4o-mini (handles text, images, videos and audio)
- **Tools**: RAG Tool (`tools.py`) to query Supabase vector store
- **Database**: Supabase (`pgvector`)
- **Deployment**: Google Cloud Run

## API Endpoint

### `POST /vet`

Vet an advertisement file against ARCON regulations.

**Request**: `multipart/form-data`
- `file`: Advertisement file (image/video/audio)

**Supported Formats**:
- Images: PNG, JPG, JPEG
- Videos: MP4, MOV, AVI
- Audio: MP3, WAV, M4A, FLAC, WEBM, MPEG

**Response**:
```json
{
  "success": true,
  "media_type": "image",
  "analysis": "**Product:** ... **Compliance Score:** 95% ..."
}
```

### `GET /health`

Health check endpoint for Cloud Run.

## Local Development

1. Create `.env` file with required environment variables:
   ```
   OPENAI_API_KEY=your_key
   SUPABASE_URL=your_url
   SUPABASE_SERVICE_KEY=your_key
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   uvicorn src.main:app --reload
   ```

## Deployment

Deployment is automated via GitHub Actions on push to `main` branch.

### Required GitHub Secrets

- `GCP_PROJECT_ID`: Google Cloud project ID
- `GCP_REGION`: Deployment region (e.g., `us-central1`)
- `GCP_SA_KEY`: Service account JSON key
- `OPENAI_API_KEY`: OpenAI API key
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_KEY`: Supabase service key

### Manual Deployment

```bash
# Build image
docker build -t arcon-vetting-api .

# Run locally
docker run -p 8080:8080 --env-file .env arcon-vetting-api
```
