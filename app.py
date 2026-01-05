import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent import run_agent

st.set_page_config(page_title="AdVet Demo", page_icon="✅", layout="centered")

st.title("🎯 AdVet Demo")
st.caption("ARCON Compliance Vetting System")

st.markdown("*Max file size: 150MB (Enterprise)*")

uploaded_file = st.file_uploader(
    "Upload your creative",
    type=['jpg', 'jpeg', 'png', 'mp3', 'wav', 'm4a', 'flac', 'mp4', 'mov', 'avi']
)

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    
    ext = uploaded_file.name.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png']:
        media_type = 'image'
        st.image(uploaded_file, use_container_width=True)
    elif ext in ['mp3', 'wav', 'm4a', 'flac']:
        media_type = 'audio'
        st.audio(uploaded_file)
    elif ext in ['mp4', 'mov', 'avi']:
        media_type = 'video'
        st.video(uploaded_file)
    
    st.info(f"**{uploaded_file.name}** — {file_size_mb:.2f} MB")
    
    if st.button("🔍 Vet Creative", type="primary", use_container_width=True):
        with st.spinner("Analyzing..."):
            try:
                uploaded_file.seek(0)
                result = run_agent(uploaded_file, media_type)
                st.success("Done!")
                st.markdown(result)
            except Exception as e:
                st.error(f"Failed: {e}")
