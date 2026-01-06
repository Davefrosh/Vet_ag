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

app = FastAPI(
    title="ARCON Vetting API",
    description="API to vet advertisements against ARCON regulations",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    gcs_path = f"uploads/{uuid.uuid4()}/{request.filename}"
    
    from google.auth.transport import requests as google_requests
    
    credentials, project = auth.default()
    auth_request = google_requests.Request()
    credentials.refresh(auth_request)
    
    service_account_email = "64011286693-compute@developer.gserviceaccount.com"
    
    client = storage.Client(credentials=credentials, project=project)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(gcs_path)
    
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_type="application/octet-stream",
        service_account_email=service_account_email,
        access_token=credentials.token
    )
    
    return UploadResponse(upload_url=upload_url, gcs_path=gcs_path)


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
