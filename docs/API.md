# ARCON Vetting API Documentation

**Base URL:** `https://arcon-vetting-api-64011286693.us-central1.run.app`

**Interactive Docs:** [Swagger UI](https://arcon-vetting-api-64011286693.us-central1.run.app/docs) | [ReDoc](https://arcon-vetting-api-64011286693.us-central1.run.app/redoc)

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running.

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
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/advertisement.mp4"
```

### JavaScript (Fetch)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('https://arcon-vetting-api-64011286693.us-central1.run.app/vet', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

### Python (requests)

```python
import requests

url = "https://arcon-vetting-api-64011286693.us-central1.run.app/vet"

with open("advertisement.mp4", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print(response.json())
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "success": true,
  "media_type": "video",
  "analysis": "**Product:** Honeywell Semolina\n\n**Compliance Score:** 95%\n\n**Compliance Summary:**\n| Area Checked | Status | Article | Remarks |\n|--------------|--------|---------|--------|\n| Honesty | PASS | Art. 1 | No misleading claims |\n| Decency | PASS | Art. 2 | Content appropriate |\n\n**Verdict:** COMPLIANT",
  "error": null
}
```

### Error Response - Unsupported File (400 Bad Request)

```json
{
  "detail": "Unsupported file type. Supported: {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'm4a', 'flac', 'webm', 'mpeg', 'mpga'}"
}
```

### Error Response - Processing Failed (200 OK)

```json
{
  "success": false,
  "media_type": "image",
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
- Large files (>100MB) may timeout
- The API uses GPT-4o-mini for analysis
- Regulations checked: Nigerian Code of Advertising Practice (ARCON)

