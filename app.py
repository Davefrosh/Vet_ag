import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "https://arcon-vetting-api-64011286693.us-central1.run.app")
API_KEY = os.getenv("API_KEY", "advet-api-key-2024-secure")

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
            with st.spinner("Analyzing... This may take a few minutes for large files."):
                try:
                    uploaded_file.seek(0)
                    file_content = uploaded_file.read()
                    
                    if file_size_mb > 30:
                        st.info("Large file detected. Using cloud upload flow...")
                        
                        response = requests.post(
                            f"{API_URL}/upload/request",
                            headers={"X-API-Key": API_KEY},
                            json={
                                "filename": uploaded_file.name,
                                "file_size": len(file_content),
                                "tier": tier
                            }
                        )
                        
                        if response.status_code != 200:
                            st.error(f"Upload request failed: {response.text}")
                            st.stop()
                        
                        upload_data = response.json()
                        upload_url = upload_data["upload_url"]
                        gcs_path = upload_data["gcs_path"]
                        
                        upload_response = requests.put(
                            upload_url,
                            data=file_content,
                            headers={"Content-Type": "application/octet-stream"}
                        )
                        
                        if upload_response.status_code != 200:
                            st.error(f"File upload failed: {upload_response.text}")
                            st.stop()
                        
                        vet_response = requests.post(
                            f"{API_URL}/vet/gcs",
                            headers={"X-API-Key": API_KEY},
                            data={"gcs_path": gcs_path, "tier": tier}
                        )
                    else:
                        uploaded_file.seek(0)
                        vet_response = requests.post(
                            f"{API_URL}/vet",
                            headers={"X-API-Key": API_KEY, "X-Tier": tier},
                            files={"file": (uploaded_file.name, file_content)}
                        )
                    
                    if vet_response.status_code == 200:
                        result = vet_response.json()
                        if result.get("success"):
                            st.success("Done!")
                            st.markdown(result.get("analysis", "No analysis returned"))
                        else:
                            st.error(f"Vetting failed: {result.get('error')}")
                    else:
                        st.error(f"API error: {vet_response.text}")
                        
                except Exception as e:
                    st.error(f"Failed: {e}")
