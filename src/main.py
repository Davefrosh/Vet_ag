from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from schemas import VetResponse, Tier, TIER_FILE_LIMITS
from agent import run_agent
from config import load_config
from io import BytesIO

app = FastAPI(
    title="ARCON Vetting API",
    description="API to vet advertisements against ARCON regulations",
    version="2.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supported file extensions
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi"}
AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "flac", "webm", "mpeg", "mpga"}


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Validate the API key from request header."""
    _, _, _, _, api_secret_key = load_config()
    
    if not api_secret_key:
        raise HTTPException(
            status_code=500,
            detail="API_SECRET_KEY not configured on server"
        )
    
    if x_api_key != api_secret_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key


def get_tier(x_tier: str = Header(..., alias="X-Tier")):
    """Extract and validate tier from request header."""
    try:
        return Tier(x_tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{x_tier}'. Must be one of: free, pro, enterprise"
        )


class FileWrapper:
    """Wrapper to make UploadFile compatible with media_processor expectations."""
    def __init__(self, file_obj, filename: str):
        self._file = file_obj
        self.name = filename
    
    def seek(self, pos):
        return self._file.seek(pos)
    
    def read(self, size=-1):
        return self._file.read(size)


def get_media_type(filename: str) -> str | None:
    """Detect media type from file extension."""
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


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}


@app.post("/vet", response_model=VetResponse)
async def vet_advertisement(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
    tier: Tier = Depends(get_tier)
):
    """
    Vet an advertisement file against ARCON regulations.
    
    Requires:
    - X-API-Key header: Your API secret key
    - X-Tier header: User's subscription tier (free, pro, enterprise)
    
    Accepts image (PNG, JPG), video (MP4, MOV, AVI), or audio (MP3, WAV, M4A, etc.) files.
    
    File size limits:
    - Free: 5 MB
    - Pro: 25 MB
    - Enterprise: 150 MB
    """
    # Detect media type
    media_type = get_media_type(file.filename)
    
    if not media_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS}"
        )
    
    try:
        # Read file content into memory
        content = await file.read()
        file_size = len(content)
        
        # Validate file size against tier limit
        max_size = TIER_FILE_LIMITS[tier]
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size_mb:.2f} MB) exceeds {tier.value} tier limit ({max_size_mb:.0f} MB)"
            )
        
        file_obj = BytesIO(content)
        
        # Wrap file to provide .name attribute for media_processor compatibility
        wrapped_file = FileWrapper(file_obj, file.filename)
        
        # Run the vetting agent
        analysis = run_agent(wrapped_file, media_type)
        
        return VetResponse(
            success=True,
            media_type=media_type,
            tier=tier.value,
            analysis=analysis
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like file size limit)
        raise
        
    except Exception as e:
        return VetResponse(
            success=False,
            media_type=media_type,
            tier=tier.value,
            error=str(e)
        )

