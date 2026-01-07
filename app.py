import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "https://arcon-vetting-api-64011286693.us-central1.run.app")
API_KEY = os.getenv("API_KEY", "advet-api-key-2024-secure")
CHUNK_SIZE = 25 * 1024 * 1024  # 25MB chunks

st.set_page_config(page_title="AdVet Demo", page_icon="✅", layout="centered")

st.title("🎯 AdVet Demo")
st.caption("ARCON Compliance Vetting System")

tier = st.selectbox("Select Tier", ["free", "pro", "enterprise"], index=2)

tier_limits = {"free": 5, "pro": 25, "enterprise": 150}
st.info(f"**{tier.upper()}** tier - Max file size: {tier_limits[tier]} MB")

uploaded_file = st.file_uploader(
    "Upload your creative",
    type=['jpg', 'jpeg', 'png', 'mp3', 'wav', 'm4a', 'flac', 'mp4', 'mov', 'avi']
)


def chunked_upload(file_content: bytes, filename: str, tier: str, progress_bar):
    """Upload large file using chunked upload flow."""
    file_size = len(file_content)
    
    # Step 1: Initialize upload session
    init_response = requests.post(
        f"{API_URL}/upload/init",
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
        json={"filename": filename, "file_size": file_size, "tier": tier},
        timeout=60
    )
    
    if init_response.status_code != 200:
        raise Exception(f"Failed to initialize upload: {init_response.text}")
    
    init_data = init_response.json()
    session_id = init_data["session_id"]
    
    # Step 2: Upload chunks
    offset = 0
    chunk_index = 0
    
    while offset < file_size:
        chunk_end = min(offset + CHUNK_SIZE, file_size)
        chunk = file_content[offset:chunk_end]
        
        chunk_response = requests.post(
            f"{API_URL}/upload/chunk/{session_id}",
            headers={"X-API-Key": API_KEY},
            files={"chunk": ("chunk", chunk, "application/octet-stream")},
            data={"chunk_index": chunk_index},
            timeout=120
        )
        
        if chunk_response.status_code != 200:
            raise Exception(f"Failed to upload chunk {chunk_index}: {chunk_response.text}")
        
        offset = chunk_end
        chunk_index += 1
        progress_bar.progress(offset / file_size * 0.7, text=f"Processing file... {int(offset / file_size * 70)}%")
    
    # Step 3: Process file
    progress_bar.progress(0.75, text="Extracting content...")
    
    vet_response = requests.post(
        f"{API_URL}/vet/session/{session_id}",
        headers={"X-API-Key": API_KEY, "Content-Length": "0"},
        timeout=600
    )
    
    progress_bar.progress(1.0, text="Generating compliance report...")
    
    return vet_response


if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png']:
        st.image(uploaded_file, use_container_width=True)
    elif ext in ['mp3', 'wav', 'm4a', 'flac']:
        st.audio(uploaded_file)
    elif ext in ['mp4', 'mov', 'avi']:
        st.video(uploaded_file)
    
    st.write(f"**{uploaded_file.name}** — {file_size_mb:.2f} MB")
    
    if file_size_mb > tier_limits[tier]:
        st.error(f"File exceeds {tier.upper()} tier limit of {tier_limits[tier]} MB")
    else:
        if st.button("🔍 Vet Creative", type="primary", use_container_width=True):
            try:
                uploaded_file.seek(0)
                file_content = uploaded_file.read()
                
                if file_size_mb > 30:
                    # Large file: use chunked upload
                    progress_bar = st.progress(0, text="Preparing analysis...")
                    vet_response = chunked_upload(file_content, uploaded_file.name, tier, progress_bar)
                else:
                    # Small file: direct upload
                    with st.spinner("Analyzing..."):
                        vet_response = requests.post(
                            f"{API_URL}/vet",
                            headers={"X-API-Key": API_KEY, "X-Tier": tier},
                            files={"file": (uploaded_file.name, file_content)},
                            timeout=300
                        )
                
                if vet_response.status_code == 200:
                    result = vet_response.json()
                    if result.get("success"):
                        st.success("✅ Analysis Complete!")
                        st.markdown(result.get("analysis", "No analysis returned"))
                    else:
                        st.error(f"Vetting failed: {result.get('error')}")
                else:
                    st.error(f"API error: {vet_response.text}")
                    
            except Exception as e:
                st.error(f"Failed: {e}")
