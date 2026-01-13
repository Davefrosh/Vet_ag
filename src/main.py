from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from schemas import VetResponse, Tier, TIER_FILE_LIMITS
from agent import run_agent
from config import load_config
from io import BytesIO
from google.cloud import storage
from google import auth
from datetime import timedelta
import os
import tempfile
import uuid
from typing import Optional

app = FastAPI(
    title="ARCON Vetting API",
    description="API to vet advertisements against ARCON regulations",
    version="2.0.0"
)

# In-memory store for chunked upload sessions
upload_sessions = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GCS_BUCKET = os.getenv("GCS_BUCKET", "advet-temp-uploads")

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "flac", "webm", "mpeg", "mpga"}


class UploadRequest(BaseModel):
    filename: str
    file_size: int
    tier: str


class UploadResponse(BaseModel):
    upload_url: str
    gcs_path: str


class ChunkedUploadInit(BaseModel):
    filename: str
    file_size: int
    tier: str


class ChunkedUploadInitResponse(BaseModel):
    session_id: str
    gcs_path: str


class ChunkedUploadCompleteResponse(BaseModel):
    success: bool
    message: str


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    _, _, _, _, api_secret_key = load_config()
    
    if not api_secret_key:
        raise HTTPException(status_code=500, detail="API_SECRET_KEY not configured on server")
    
    if x_api_key != api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return x_api_key


def get_tier(x_tier: str = Header(..., alias="X-Tier")):
    try:
        return Tier(x_tier.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{x_tier}'. Must be one of: free, pro, enterprise")


def get_tier_from_string(tier_str: str) -> Tier:
    try:
        return Tier(tier_str.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{tier_str}'. Must be one of: free, pro, enterprise")


class FileWrapper:
    def __init__(self, file_obj, filename: str):
        self._file = file_obj
        self.name = filename
    
    def seek(self, pos):
        return self._file.seek(pos)
    
    def read(self, size=-1):
        return self._file.read(size)


def get_media_type(filename: str) -> str | None:
    if not filename:
        return None
    ext = filename.split('.')[-1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    return None


def get_gcs_client():
    return storage.Client()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload/request", response_model=UploadResponse)
async def request_upload_url(
    request: UploadRequest,
    api_key: str = Depends(verify_api_key)
):
    tier = get_tier_from_string(request.tier)
    max_size = TIER_FILE_LIMITS[tier]
    
    if request.file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = request.file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size_mb:.2f} MB) exceeds {tier.value} tier limit ({max_size_mb:.0f} MB)"
        )
    
    media_type = get_media_type(request.filename)
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )
    
    import uuid
    import requests as http_requests
    
    gcs_path = f"uploads/{uuid.uuid4()}/{request.filename}"
    
    credentials, project = auth.default()
    from google.auth.transport import requests as google_requests
    auth_request = google_requests.Request()
    credentials.refresh(auth_request)
    
    resumable_url = f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}/o?uploadType=resumable&name={gcs_path}"
    
    response = http_requests.post(
        resumable_url,
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "application/octet-stream"
        },
        json={}
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Failed to create upload session: {response.text}")
    
    upload_url = response.headers.get("Location")
    
    return UploadResponse(upload_url=upload_url, gcs_path=gcs_path)


@app.post("/upload/init", response_model=ChunkedUploadInitResponse)
async def init_chunked_upload(
    request: ChunkedUploadInit,
    api_key: str = Depends(verify_api_key)
):
    """Initialize a chunked upload session for files > 32MB."""
    tier = get_tier_from_string(request.tier)
    max_size = TIER_FILE_LIMITS[tier]
    
    if request.file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = request.file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file_size_mb:.2f} MB) exceeds {tier.value} tier limit ({max_size_mb:.0f} MB)"
        )
    
    media_type = get_media_type(request.filename)
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )
    
    session_id = str(uuid.uuid4())
    gcs_path = f"uploads/{session_id}/{request.filename}"
    
    upload_sessions[session_id] = {
        "filename": request.filename,
        "file_size": request.file_size,
        "tier": request.tier,
        "gcs_path": gcs_path,
        "chunks": [],
        "bytes_received": 0
    }
    
    return ChunkedUploadInitResponse(session_id=session_id, gcs_path=gcs_path)


@app.post("/upload/chunk/{session_id}")
async def upload_chunk(
    session_id: str,
    chunk: UploadFile = File(...),
    chunk_index: int = Form(...),
    api_key: str = Depends(verify_api_key)
):
    """Upload a single chunk. Each chunk must be < 30MB."""
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = upload_sessions[session_id]
    
    content = await chunk.read()
    chunk_size = len(content)
    
    # Upload chunk to GCS
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    chunk_path = f"uploads/{session_id}/chunk_{chunk_index:04d}"
    blob = bucket.blob(chunk_path)
    blob.upload_from_string(content, content_type="application/octet-stream")
    
    session["chunks"].append(chunk_path)
    session["bytes_received"] += chunk_size
    
    return {
        "success": True,
        "chunk_index": chunk_index,
        "bytes_received": session["bytes_received"],
        "total_size": session["file_size"]
    }


@app.post("/vet/session/{session_id}", response_model=VetResponse)
async def vet_from_session(
    session_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Complete chunked upload and process the file."""
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = upload_sessions[session_id]
    tier_enum = get_tier_from_string(session["tier"])
    filename = session["filename"]
    media_type = get_media_type(filename)
    
    tmp_path = None
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        
        # Sort chunks and compose them into final file
        chunk_blobs = sorted(session["chunks"])
        
        if len(chunk_blobs) == 1:
            # Single chunk, just rename
            final_blob = bucket.blob(session["gcs_path"])
            bucket.copy_blob(bucket.blob(chunk_blobs[0]), bucket, session["gcs_path"])
        else:
            # Multiple chunks, compose them (max 32 per compose operation)
            final_blob = bucket.blob(session["gcs_path"])
            source_blobs = [bucket.blob(cp) for cp in chunk_blobs]
            
            # GCS compose limit is 32, so we may need multiple passes
            while len(source_blobs) > 1:
                composed = []
                for i in range(0, len(source_blobs), 32):
                    batch = source_blobs[i:i+32]
                    if len(batch) == 1:
                        composed.append(batch[0])
                    else:
                        temp_name = f"uploads/{session_id}/composed_{i}"
                        temp_blob = bucket.blob(temp_name)
                        temp_blob.compose(batch)
                        composed.append(temp_blob)
                source_blobs = composed
            
            # Final compose or copy
            if source_blobs:
                final_blob = source_blobs[0]
                if final_blob.name != session["gcs_path"]:
                    bucket.copy_blob(final_blob, bucket, session["gcs_path"])
                    final_blob = bucket.blob(session["gcs_path"])
        
        # Download and process
        ext = filename.split('.')[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp_file:
            tmp_path = tmp_file.name
            final_blob.download_to_filename(tmp_path)
        
        with open(tmp_path, 'rb') as f:
            file_obj = BytesIO(f.read())
        
        wrapped_file = FileWrapper(file_obj, filename)
        analysis = run_agent(wrapped_file, media_type)
        
        # Cleanup: delete all chunks and final blob
        for cp in chunk_blobs:
            try:
                bucket.blob(cp).delete()
            except:
                pass
        try:
            final_blob.delete()
        except:
            pass
        
        # Remove session
        del upload_sessions[session_id]
        
        return VetResponse(
            success=True,
            media_type=media_type,
            tier=tier_enum.value,
            analysis=analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return VetResponse(
            success=False,
            media_type=media_type,
            tier=tier_enum.value,
            error=str(e)
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


@app.post("/vet/gcs", response_model=VetResponse)
async def vet_from_gcs(
    gcs_path: str = Form(...),
    tier: str = Form(...),
    api_key: str = Depends(verify_api_key)
):
    tier_enum = get_tier_from_string(tier)
    filename = gcs_path.split("/")[-1]
    media_type = get_media_type(filename)
    
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )
    
    tmp_path = None
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in storage")
        
        blob.reload()
        file_size = blob.size
        max_size = TIER_FILE_LIMITS[tier_enum]
        
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size_mb:.2f} MB) exceeds {tier_enum.value} tier limit ({max_size_mb:.0f} MB)"
            )
        
        ext = filename.split('.')[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp_file:
            tmp_path = tmp_file.name
            blob.download_to_filename(tmp_path)
        
        with open(tmp_path, 'rb') as f:
            file_obj = BytesIO(f.read())
        
        wrapped_file = FileWrapper(file_obj, filename)
        analysis = run_agent(wrapped_file, media_type)
        
        try:
            blob.delete()
        except:
            pass
        
        return VetResponse(
            success=True,
            media_type=media_type,
            tier=tier_enum.value,
            analysis=analysis
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        return VetResponse(
            success=False,
            media_type=media_type,
            tier=tier_enum.value,
            error=str(e)
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


@app.post("/vet", response_model=VetResponse)
async def vet_advertisement(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
    tier: Tier = Depends(get_tier)
):
    media_type = get_media_type(file.filename)
    
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )
    
    try:
        content = await file.read()
        file_size = len(content)
        
        max_size = TIER_FILE_LIMITS[tier]
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size_mb:.2f} MB) exceeds {tier.value} tier limit ({max_size_mb:.0f} MB)"
            )
        
        file_obj = BytesIO(content)
        wrapped_file = FileWrapper(file_obj, file.filename)
        analysis = run_agent(wrapped_file, media_type)
        
        return VetResponse(
            success=True,
            media_type=media_type,
            tier=tier.value,
            analysis=analysis
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        return VetResponse(
            success=False,
            media_type=media_type,
            tier=tier.value,
            error=str(e)
        )
