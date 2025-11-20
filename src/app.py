import streamlit as st
from agent import run_agent

st.set_page_config(page_title="ARCON Vetting Agent", layout="wide", page_icon="🛡️")

st.title("🛡️ ARCON Advertisement Vetting System")
st.markdown("""
Upload an advertisement image to check compliance against ARCON (Advertising Regulatory Council of Nigeria) regulations.
""")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("**Architecture:** ReAct Agent with RAG")
    st.markdown("**Model:** GPT-4o-mini")
    st.markdown("**Vector Store:** Supabase")
    st.markdown("**Regulations:** Nigerian Code of Advertising")
    st.divider()
    st.caption("Upload an ad image to get instant compliance analysis.")

# Main layout
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Upload Advertisement")
    
    uploaded_file = st.file_uploader(
        "Choose an advertisement image", 
        type=['png', 'jpg', 'jpeg'],
        help="Upload a clear image of the advertisement you want to vet"
    )
    
    # Display uploaded image
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Advertisement", use_container_width=True)
        
        # Vet button
        if st.button("🔍 Vet Advertisement", type="primary", use_container_width=True):
            with st.spinner("🔎 Analyzing advertisement against ARCON regulations..."):
                try:
                    # Run the agent with a simple prompt
                    response = run_agent(
                        "Analyze this advertisement image for ARCON compliance.", 
                        uploaded_file
                    )
                    st.session_state['result'] = response
                    st.session_state['has_result'] = True
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    st.session_state['has_result'] = False
    else:
        st.info("👆 Please upload an advertisement image to begin vetting.")

with col2:
    st.subheader("📋 Compliance Analysis")
    
    if st.session_state.get('has_result', False):
        st.markdown(st.session_state['result'])
        
        # Option to download report
        st.download_button(
            label="📥 Download Report",
            data=st.session_state['result'],
            file_name="arcon_compliance_report.txt",
            mime="text/plain"
        )
    else:
        st.info("Analysis results will appear here after vetting.")
