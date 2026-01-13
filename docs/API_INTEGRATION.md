# ARCON Vetting API - Web App Integration Guide

**Base URL:** `https://arcon-vetting-api-64011286693.us-central1.run.app`

---

## Quick Reference

| Tier | Max File Size | Upload Method |
|------|---------------|---------------|
| `free` | 5 MB | Direct (`/vet`) |
| `pro` | 25 MB | Direct (`/vet`) |
| `enterprise` | 150 MB | Chunked Upload |

**Authentication Headers (required for all endpoints):**
```
X-API-Key: your-api-key
X-Tier: free | pro | enterprise
```

---

## Integration Flow

### For Files ≤ 30MB → Direct Upload

```
[User uploads file] → POST /vet → [Compliance Report]
```

### For Files > 30MB → Chunked Upload

```
[User uploads file] → POST /upload/init → [session_id]
                    → POST /upload/chunk/{session_id} (repeat for each chunk)
                    → POST /vet/session/{session_id} → [Compliance Report]
```

---

## Endpoints

### 1. Direct Vet (Files ≤ 30MB)

**`POST /vet`**

| Parameter | Type | Location | Required |
|-----------|------|----------|----------|
| `X-API-Key` | string | Header | Yes |
| `X-Tier` | string | Header | Yes |
| `file` | File | Body (multipart/form-data) | Yes |

---

### 2. Initialize Chunked Upload (Files > 30MB)

**`POST /upload/init`**

| Parameter | Type | Location | Required |
|-----------|------|----------|----------|
| `X-API-Key` | string | Header | Yes |
| `filename` | string | Body (JSON) | Yes |
| `file_size` | integer | Body (JSON) | Yes |
| `tier` | string | Body (JSON) | Yes |

**Response:**
```json
{
  "session_id": "abc123-uuid",
  "gcs_path": "uploads/abc123-uuid/filename.mp4"
}
```

---

### 3. Upload Chunk

**`POST /upload/chunk/{session_id}`**

| Parameter | Type | Location | Required |
|-----------|------|----------|----------|
| `X-API-Key` | string | Header | Yes |
| `chunk` | File | Body (multipart/form-data) | Yes |
| `chunk_index` | integer | Body (form-data) | Yes |

**Response:**
```json
{
  "success": true,
  "chunk_index": 0,
  "bytes_received": 26214400,
  "total_size": 78643200
}
```

---

### 4. Complete Upload & Get Analysis

**`POST /vet/session/{session_id}`**

| Parameter | Type | Location | Required |
|-----------|------|----------|----------|
| `X-API-Key` | string | Header | Yes |

**Response:** Same as `/vet` endpoint

---

## Code Examples

### JavaScript/Fetch - Direct Upload

```javascript
async function vetCreative(file, apiKey, tier) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('https://arcon-vetting-api-64011286693.us-central1.run.app/vet', {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'X-Tier': tier
    },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Vetting failed');
  }

  return await response.json();
}

// Usage
const fileInput = document.getElementById('fileInput');
const result = await vetCreative(fileInput.files[0], 'your-api-key', 'pro');
console.log(result.analysis);
```

---

### JavaScript/Fetch - Chunked Upload (Large Files)

```javascript
const API_URL = 'https://arcon-vetting-api-64011286693.us-central1.run.app';
const CHUNK_SIZE = 25 * 1024 * 1024; // 25MB chunks

async function vetLargeCreative(file, apiKey, tier, onProgress) {
  // Step 1: Initialize upload session
  const initResponse = await fetch(`${API_URL}/upload/init`, {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      filename: file.name,
      file_size: file.size,
      tier: tier
    })
  });

  if (!initResponse.ok) {
    const error = await initResponse.json();
    throw new Error(error.detail || 'Failed to initialize upload');
  }

  const { session_id } = await initResponse.json();

  // Step 2: Upload chunks
  let offset = 0;
  let chunkIndex = 0;

  while (offset < file.size) {
    const chunkEnd = Math.min(offset + CHUNK_SIZE, file.size);
    const chunk = file.slice(offset, chunkEnd);

    const chunkFormData = new FormData();
    chunkFormData.append('chunk', chunk, `chunk_${chunkIndex}`);
    chunkFormData.append('chunk_index', chunkIndex.toString());

    const chunkResponse = await fetch(`${API_URL}/upload/chunk/${session_id}`, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey
      },
      body: chunkFormData
    });

    if (!chunkResponse.ok) {
      throw new Error(`Chunk ${chunkIndex} upload failed`);
    }

    offset = chunkEnd;
    chunkIndex++;

    // Report progress (0-70% for upload phase)
    if (onProgress) {
      onProgress(Math.round((offset / file.size) * 70));
    }
  }

  // Step 3: Process file and get analysis
  if (onProgress) onProgress(75); // Processing phase

  const vetResponse = await fetch(`${API_URL}/vet/session/${session_id}`, {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'Content-Length': '0'
    }
  });

  if (!vetResponse.ok) {
    const error = await vetResponse.json();
    throw new Error(error.detail || 'Vetting failed');
  }

  if (onProgress) onProgress(100);

  return await vetResponse.json();
}

// Usage with progress callback
const result = await vetLargeCreative(
  fileInput.files[0],
  'your-api-key',
  'enterprise',
  (progress) => {
    progressBar.style.width = `${progress}%`;
    progressBar.textContent = `${progress}%`;
  }
);
```

---

### JavaScript - Complete Integration Example

```javascript
const API_URL = 'https://arcon-vetting-api-64011286693.us-central1.run.app';
const CHUNK_SIZE = 25 * 1024 * 1024;
const DIRECT_UPLOAD_LIMIT = 30 * 1024 * 1024; // 30MB

async function vetCreativeAuto(file, apiKey, tier, onProgress) {
  if (file.size <= DIRECT_UPLOAD_LIMIT) {
    // Use direct upload for smaller files
    return await vetCreativeDirect(file, apiKey, tier);
  } else {
    // Use chunked upload for larger files
    return await vetLargeCreative(file, apiKey, tier, onProgress);
  }
}

async function vetCreativeDirect(file, apiKey, tier) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/vet`, {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'X-Tier': tier
    },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Vetting failed');
  }

  return await response.json();
}

// Full usage example with UI
document.getElementById('vetButton').addEventListener('click', async () => {
  const file = document.getElementById('fileInput').files[0];
  const tier = getUserTier(); // Your function to get user's tier
  const apiKey = getApiKey(); // Your function to get API key

  // Validate file size against tier
  const tierLimits = { free: 5, pro: 25, enterprise: 150 };
  const fileSizeMB = file.size / (1024 * 1024);
  
  if (fileSizeMB > tierLimits[tier]) {
    alert(`File size (${fileSizeMB.toFixed(1)}MB) exceeds ${tier} tier limit (${tierLimits[tier]}MB)`);
    return;
  }

  try {
    showLoading(true);
    
    const result = await vetCreativeAuto(file, apiKey, tier, (progress) => {
      updateProgressBar(progress);
    });

    if (result.success) {
      displayComplianceReport(result.analysis);
    } else {
      showError(result.error);
    }
  } catch (error) {
    showError(error.message);
  } finally {
    showLoading(false);
  }
});
```

---

### Python (requests) - Direct Upload

```python
import requests

API_URL = "https://arcon-vetting-api-64011286693.us-central1.run.app"

def vet_creative(file_path: str, api_key: str, tier: str) -> dict:
    """Vet a creative file for compliance."""
    headers = {
        "X-API-Key": api_key,
        "X-Tier": tier
    }
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            f"{API_URL}/vet",
            headers=headers,
            files=files,
            timeout=120  # Videos may take longer
        )
    
    response.raise_for_status()
    return response.json()

# Usage
result = vet_creative("advertisement.mp4", "your-api-key", "pro")
print(result["analysis"])
```

---

### Python (requests) - Chunked Upload (Large Files)

```python
import requests
import os

API_URL = "https://arcon-vetting-api-64011286693.us-central1.run.app"
CHUNK_SIZE = 25 * 1024 * 1024  # 25MB

def vet_large_creative(file_path: str, api_key: str, tier: str, on_progress=None) -> dict:
    """Vet a large creative file using chunked upload."""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    headers = {"X-API-Key": api_key}
    
    # Step 1: Initialize upload session
    init_response = requests.post(
        f"{API_URL}/upload/init",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "filename": filename,
            "file_size": file_size,
            "tier": tier
        }
    )
    init_response.raise_for_status()
    session_id = init_response.json()["session_id"]
    
    # Step 2: Upload chunks
    with open(file_path, "rb") as f:
        chunk_index = 0
        bytes_uploaded = 0
        
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            
            chunk_response = requests.post(
                f"{API_URL}/upload/chunk/{session_id}",
                headers=headers,
                files={"chunk": (f"chunk_{chunk_index}", chunk)},
                data={"chunk_index": chunk_index}
            )
            chunk_response.raise_for_status()
            
            bytes_uploaded += len(chunk)
            chunk_index += 1
            
            if on_progress:
                progress = int((bytes_uploaded / file_size) * 70)
                on_progress(progress)
    
    # Step 3: Process file and get analysis
    if on_progress:
        on_progress(75)
    
    vet_response = requests.post(
        f"{API_URL}/vet/session/{session_id}",
        headers={**headers, "Content-Length": "0"},
        timeout=300  # Large files may take longer
    )
    vet_response.raise_for_status()
    
    if on_progress:
        on_progress(100)
    
    return vet_response.json()

# Usage
def print_progress(progress):
    print(f"Progress: {progress}%")

result = vet_large_creative(
    "large_video.mp4",
    "your-api-key",
    "enterprise",
    on_progress=print_progress
)
print(result["analysis"])
```

---

### Python - Complete Integration Example

```python
import requests
import os

API_URL = "https://arcon-vetting-api-64011286693.us-central1.run.app"
CHUNK_SIZE = 25 * 1024 * 1024
DIRECT_UPLOAD_LIMIT = 30 * 1024 * 1024

TIER_LIMITS = {
    "free": 5 * 1024 * 1024,
    "pro": 25 * 1024 * 1024,
    "enterprise": 150 * 1024 * 1024
}

def vet_creative_auto(file_path: str, api_key: str, tier: str, on_progress=None) -> dict:
    """
    Automatically choose direct or chunked upload based on file size.
    
    Args:
        file_path: Path to the creative file
        api_key: Your ARCON API key
        tier: User's subscription tier (free/pro/enterprise)
        on_progress: Optional callback function(progress: int)
    
    Returns:
        dict: API response with 'success', 'analysis', and 'error' fields
    
    Raises:
        ValueError: If file exceeds tier limit
        requests.HTTPError: If API request fails
    """
    file_size = os.path.getsize(file_path)
    
    # Validate file size against tier
    if file_size > TIER_LIMITS[tier]:
        raise ValueError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) "
            f"exceeds {tier} tier limit ({TIER_LIMITS[tier] / 1024 / 1024}MB)"
        )
    
    if file_size <= DIRECT_UPLOAD_LIMIT:
        return vet_creative_direct(file_path, api_key, tier)
    else:
        return vet_large_creative(file_path, api_key, tier, on_progress)


def vet_creative_direct(file_path: str, api_key: str, tier: str) -> dict:
    """Direct upload for files ≤ 30MB."""
    headers = {"X-API-Key": api_key, "X-Tier": tier}
    
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/vet",
            headers=headers,
            files={"file": f},
            timeout=120
        )
    
    response.raise_for_status()
    return response.json()


# Usage example for web backend (e.g., Django/Flask)
def handle_vet_request(uploaded_file, user_tier, api_key):
    """Example handler for a web framework."""
    import tempfile
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.filename) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    
    try:
        result = vet_creative_auto(tmp_path, api_key, user_tier)
        return {
            "success": result["success"],
            "analysis": result["analysis"],
            "error": result.get("error")
        }
    finally:
        os.unlink(tmp_path)  # Clean up temp file
```

---

## Response Format

### Success Response

```json
{
  "success": true,
  "media_type": "video",
  "tier": "enterprise",
  "analysis": "**Product:** Honeywell Noodles\n\n**Compliance Score:** 100%\n\n**Compliance Summary:**\n| Area Checked | Status | Article | Remarks |\n|--------------|--------|---------|--------|\n| Honesty | PASS | Art. 1 | No misleading claims |\n| Health Claims | PASS | Art. 14 | No unsubstantiated claims |\n\n**Verdict:** ✅ COMPLIANT",
  "error": null
}
```

### Compliance Verdicts

| Score | Verdict |
|-------|---------|
| 100% | ✅ COMPLIANT |
| 80-99% | ⚠️ COMPLIANT WITH RECOMMENDATIONS |
| 50-79% | ⛔ PARTIALLY COMPLIANT |
| <50% | ❌ NON-COMPLIANT |

---

## Error Handling

| HTTP Code | Error | Cause |
|-----------|-------|-------|
| 401 | Invalid API key | Wrong or missing `X-API-Key` |
| 400 | Invalid tier | Invalid `X-Tier` value |
| 400 | Unsupported file type | File extension not supported |
| 413 | Payload too large | File exceeds tier limit |
| 404 | Session not found | Invalid `session_id` for chunked upload |

---

## Supported File Types

| Type | Extensions |
|------|------------|
| Image | `.png`, `.jpg`, `.jpeg` |
| Video | `.mp4`, `.mov`, `.avi` |
| Audio | `.mp3`, `.wav`, `.m4a`, `.flac`, `.webm` |

---

## Performance Notes

- **Images:** ~5-10 seconds
- **Short videos (<1 min):** ~15-30 seconds
- **Long videos (1-5 min):** ~30-90 seconds
- **Large files (Enterprise):** May take 2-5 minutes total (upload + processing)

---

## Security Recommendations

1. **Never expose API key in frontend code** - Use a backend proxy
2. **Validate file types on your server** before sending to API
3. **Validate file sizes against tier** before upload
4. **Set appropriate timeouts** for large file uploads
5. **Implement retry logic** for failed chunk uploads
