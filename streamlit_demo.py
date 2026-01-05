"""
Streamlit Demo for ARCON Compliance Vetting System
Test the AssemblyAI integration with image, audio, and video files.
"""

import streamlit as st
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent import run_agent

# Page configuration
st.set_page_config(
    page_title="AdVet - ARCON Compliance Vetting",
    page_icon="✅",
    layout="wide"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #28a745;
    }
    .stButton > button {
        width: 100%;
        background-color: #1E3A5F;
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        font-size: 1.1rem;
    }
    .stButton > button:hover {
        background-color: #2C5282;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🎯 AdVet Demo</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">ARCON Compliance Vetting System - AssemblyAI Integration Test</p>', unsafe_allow_html=True)

# Tier limits display
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Free Tier", "5 MB", "max")
with col2:
    st.metric("Pro Tier", "25 MB", "max")
with col3:
    st.metric("Enterprise Tier", "150 MB", "max")
st.markdown("---")

# File upload section
st.subheader("📁 Upload Your Creative")

uploaded_file = st.file_uploader(
    "Choose an image, audio, or video file",
    type=['jpg', 'jpeg', 'png', 'gif', 'webp',  # Images
          'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac',  # Audio
          'mp4', 'mov', 'avi', 'webm', 'mkv'],  # Video
    help="Supported formats: Images (JPG, PNG, GIF, WebP), Audio (MP3, WAV, M4A, AAC, OGG, FLAC), Video (MP4, MOV, AVI, WebM, MKV)"
)

if uploaded_file is not None:
    # Determine media type
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    audio_extensions = ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac']
    video_extensions = ['mp4', 'mov', 'avi', 'webm', 'mkv']
    
    if file_extension in image_extensions:
        media_type = 'image'
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
    elif file_extension in audio_extensions:
        media_type = 'audio'
        st.audio(uploaded_file, format=f'audio/{file_extension}')
    elif file_extension in video_extensions:
        media_type = 'video'
        st.video(uploaded_file)
    else:
        media_type = None
        st.error("Unsupported file format")
    
    # File info
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📊 **File:** {uploaded_file.name} | **Size:** {file_size_mb:.2f} MB | **Type:** {media_type.upper() if media_type else 'Unknown'}")
    
    # Vet button
    if media_type:
        st.markdown("---")
        
        if st.button("🔍 VET CREATIVE", type="primary"):
            with st.spinner("🔄 Analyzing your creative... This may take a moment for audio/video files."):
                try:
                    # Reset file pointer
                    uploaded_file.seek(0)
                    
                    # Run the vetting agent
                    result = run_agent(uploaded_file, media_type)
                    
                    st.success("✅ Vetting Complete!")
                    st.markdown("---")
                    st.subheader("📋 Compliance Analysis Result")
                    st.markdown(result)
                    
                except Exception as e:
                    st.error(f"❌ Vetting analysis wasn't carried out: {str(e)}")

else:
    st.info("👆 Upload a creative file to begin vetting")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    <p>AdVet Demo | Testing AssemblyAI Integration</p>
    <p>Audio/Video transcription powered by AssemblyAI | Analysis powered by GPT-4o-mini</p>
</div>
""", unsafe_allow_html=True)
