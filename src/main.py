from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import VetResponse
from agent import run_agent
from io import BytesIO

app = FastAPI(
    title="ARCON Vetting API",
    description="API to vet advertisements against ARCON regulations",
    version="1.0.0"
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
async def vet_advertisement(file: UploadFile = File(...)):
    """
    Vet an advertisement file against ARCON regulations.
    
    Accepts image (PNG, JPG), video (MP4, MOV, AVI), or audio (MP3, WAV, M4A, etc.) files.
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
        file_obj = BytesIO(content)
        
        # Wrap file to provide .name attribute for media_processor compatibility
        wrapped_file = FileWrapper(file_obj, file.filename)
        
        # Run the vetting agent
        analysis = run_agent(wrapped_file, media_type)
        
        return VetResponse(
            success=True,
            media_type=media_type,
            analysis=analysis
        )
        
    except Exception as e:
        return VetResponse(
            success=False,
            media_type=media_type,
            error=str(e)
        )

