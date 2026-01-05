# ARCON Vetting API Documentation

**Base URL:** `https://arcon-vetting-api-64011286693.us-central1.run.app`

**Interactive Docs:** [Swagger UI](https://arcon-vetting-api-64011286693.us-central1.run.app/docs) | [ReDoc](https://arcon-vetting-api-64011286693.us-central1.run.app/redoc)

---

## Authentication

All requests to the `/vet` endpoint require authentication via API key.

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` | Yes | Your secret API key |
| `X-Tier` | Yes | User's subscription tier: `free`, `pro`, or `enterprise` |

---

## Subscription Tiers

| Tier | Max File Size |
|------|---------------|
| `free` | 5 MB |
| `pro` | 25 MB |
| `enterprise` | 150 MB |

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running. Does not require authentication.

**Request:**
```
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

### 2. Vet Advertisement

**Endpoint:** `POST /vet`

**Description:** Upload an advertisement file (image, video, or audio) to check compliance against ARCON regulations.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Headers:**
  - `X-API-Key` (required): Your secret API key
  - `X-Tier` (required): User's subscription tier
- **Body Parameter:** `file` (required) - The advertisement file

**Supported File Formats:**

| Type | Extensions |
|------|------------|
| Image | PNG, JPG, JPEG |
| Video | MP4, MOV, AVI |
| Audio | MP3, WAV, M4A, FLAC, WEBM, MPEG, MPGA |

---

## Example Requests

### cURL

```bash
curl -X POST "https://arcon-vetting-api-64011286693.us-central1.run.app/vet" \
  -H "X-API-Key: your-secret-key" \
  -H "X-Tier: pro" \
  -F "file=@/path/to/advertisement.mp4"
```

### JavaScript (Fetch)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('https://arcon-vetting-api-64011286693.us-central1.run.app/vet', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-secret-key',
    'X-Tier': 'pro'
  },
  body: formData
});

const result = await response.json();
console.log(result);
```

### Python (requests)

```python
import requests

url = "https://arcon-vetting-api-64011286693.us-central1.run.app/vet"
headers = {
    "X-API-Key": "your-secret-key",
    "X-Tier": "pro"
}

with open("advertisement.mp4", "rb") as f:
    files = {"file": f}
    response = requests.post(url, headers=headers, files=files)

print(response.json())
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "success": true,
  "media_type": "video",
  "tier": "pro",
  "analysis": "**Product:** Honeywell Semolina\n\n**Compliance Score:** 95%\n\n**Compliance Summary:**\n| Area Checked | Status | Article | Remarks |\n|--------------|--------|---------|--------|\n| Honesty | PASS | Art. 1 | No misleading claims |\n| Decency | PASS | Art. 2 | Content appropriate |\n\n**Verdict:** COMPLIANT",
  "error": null
}
```

---

## Error Responses

### 401 Unauthorized - Invalid API Key

```json
{
  "detail": "Invalid API key"
}
```

### 400 Bad Request - Missing or Invalid Tier

```json
{
  "detail": "Invalid tier 'invalid'. Must be one of: free, pro, enterprise"
}
```

### 400 Bad Request - Unsupported File Type

```json
{
  "detail": "Unsupported file type. Supported: {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'm4a', 'flac', 'webm', 'mpeg', 'mpga'}"
}
```

### 413 Payload Too Large - File Exceeds Tier Limit

```json
{
  "detail": "File size (30.50 MB) exceeds pro tier limit (25 MB)"
}
```

### 200 OK - Processing Failed

```json
{
  "success": false,
  "media_type": "image",
  "tier": "free",
  "analysis": null,
  "error": "Error message describing what went wrong"
}
```

---

## Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the vetting completed successfully |
| `media_type` | string | Type of media processed: `image`, `video`, or `audio` |
| `tier` | string | The subscription tier used for this request |
| `analysis` | string or null | The compliance analysis report (markdown formatted) |
| `error` | string or null | Error message if `success` is false |

---

## Analysis Report Format

The `analysis` field contains a markdown-formatted compliance report with:

- **Product:** Name and category of the advertised product
- **Compliance Score:** Percentage score (100% = fully compliant)
- **Compliance Summary:** Table of checked areas with PASS/FAIL status
- **Verdict:** COMPLIANT or NON-COMPLIANT
- **Issues Found:** List of violations (if any)
- **Recommendations:** Suggested fixes (if non-compliant)

---

## Notes

- Video processing may take 30-60 seconds depending on length
- Large files (near tier limits) may take longer to process
- The API uses GPT-4o-mini for visual analysis
- Audio transcription is powered by AssemblyAI
- Regulations checked: Nigerian Code of Advertising Practice (ARCON)

---

## GitHub Secrets Required for Deployment

| Secret Name | Description |
|-------------|-------------|
| `GCP_PROJECT_ID` | Google Cloud Project ID |
| `GCP_REGION` | Google Cloud region (e.g., `us-central1`) |
| `GCP_SA_KEY` | Service account key JSON |
| `OPENAI_API_KEY` | OpenAI API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service key |
| `ASSEMBLYAI_API_KEY` | AssemblyAI API key |
| `API_SECRET_KEY` | Secret key for API authentication |