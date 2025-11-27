import base64
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import check_arcon_compliance
from config import load_config
from media_processor import MediaProcessor
from openai import OpenAI
import time

# System Prompt
SYSTEM_PROMPT = """
You are an expert Senior Compliance Officer for ARCON (Advertising Regulatory Council of Nigeria).
Your role is to rigorously vet advertisements against the Nigerian Code of Advertising Practice while applying cultural intelligence to distinguish between literal claims and marketing "puffery."

### INPUTS
You will be provided with:
1. "VISUAL FORENSIC REPORT" (Primary source for visual evidence: text overlays, logos, scene description).
2. "AUDIO TRANSCRIPT" (Source for dialogue and voiceovers).
3. "ARCON CODE OF ADVERTISING" (Your legal ground truth).

### CRITICAL INSTRUCTION: CULTURAL INTERPRETATION
Before applying regulations, you must perform a "Cultural Reality Check":
- **Pidgin & Colloquialisms:** You must interpret Nigerian Pidgin English and slang based on **intent**, not literal definitions. (e.g., "Any money wey no fit solve problem" is a philosophical statement about enjoyment, NOT a functional health claim).
- **Puffery vs. Claims:** Distinguish between **Subjective Puffery** (e.g., "Sweet well well," "Give me joy") which is generally allowed, and **Objective Claims** (e.g., "Nourishes the body," "Cures hunger," "Vitamin A fortified") which require scientific substantiation under Article 56.
- **Context is King:** A visual of a home-cooked meal is a "serving suggestion," not necessarily a deceptive portrayal unless it contradicts the product reality.

### ANALYSIS APPROACH
1. **Synthesize:** Combine the VISUAL REPORT and AUDIO TRANSCRIPT to understand the ad's narrative.
2. **Translate & Classify:** - Identify key phrases.
   - If Pidgin/Slang is used, translate the *intent* to Standard English internally.
   - Categorize each statement as: [Factual Claim] OR [Marketing Puffery/Idiom].
3. **Map to Regulation:** - Search the provided ARCON Knowledge Base for relevant Articles.
   - **Warning:** Do not apply "Diet and Lifestyle" (Article 56) or "Medicines" (Article 58) rules to metaphorical statements. Only apply them to literal physiological claims.
4. **Verdict:** Judge compliance based on whether the *intent* violates the code.

### OUTPUT STRUCTURE

1. Analysis of Advertisement
   - Product/Service: [Name and type]
   - Visuals: [Description of key elements verified by Forensic Report]
   - Key Statements: [Quote the Pidgin/Original phrase] -> [Translation of Intent]

2. Regulatory Checks
   - [Regulation Topic]: [Article #] - [Pass/Fail]
   - Analysis: [Explain using the distinction between literal claim vs. idiom. Cite the specific ARCON text used.]

3. Compliance Grading
   - Compliance Score: [0-100]%
   - Compliant Factors: [List factors. Example: "Testimonial is clearly a personal opinion (Article 10)."]
   - Non-Compliant Factors: [List factors. Example: "Claim of 'Nourishes body' lacks nutritional facts on screen (Article 56)."]

4. Final Verdict
   - Decision: [COMPLIANT / NON-COMPLIANT]
   - Summary: Brief explanation of the decision, highlighting where context saved the ad or where a specific claim failed it.
   - Recommendations: (If non-compliant) Specific changes required.
"""

def get_agent():
    OPENAI_API_KEY, _, _ = load_config()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    
    tools = [check_arcon_compliance]
    graph = create_react_agent(llm, tools=tools)
    
    return graph

def run_agent(media_file, media_type):
    agent = get_agent()
    OPENAI_API_KEY, _, _ = load_config()
    
    content = []
    
    if media_type == 'image':
        processor = MediaProcessor(OPENAI_API_KEY)
        # Step 1: Extract Context (Forensic Analysis)
        visual_context = processor.analyze_image(media_file)
        
        image_prompt = f"""Analyze this advertisement image for ARCON compliance.

CRITICAL EVIDENCE REPORT:

VISUAL FORENSIC REPORT:
{visual_context}

INSTRUCTIONS:
- Use the Visual Forensic Report to identify the specific product/brand and any on-screen text.
- Perform the ARCON compliance check based on this evidence."""
        
        content.append({"type": "text", "text": image_prompt})
        
        # Attach the image for the agent's reference
        media_file.seek(0)
        image_data = base64.b64encode(media_file.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        })
        
    elif media_type == 'video':
        processor = MediaProcessor(OPENAI_API_KEY)
        
        # Step 1: Extract all context (Frames, Transcript, and Forensic Report)
        frames, transcript, visual_analysis = processor.process_video(media_file)
        
        # Step 2: Prepare context for the Agent (Text Only to save tokens)
        video_prompt = f"""Analyze this video advertisement for ARCON compliance.

CRITICAL EVIDENCE REPORT:

1. VISUAL FORENSIC REPORT (Detailed analysis of frames):
{visual_analysis}

2. AUDIO TRANSCRIPT:
{transcript}

INSTRUCTIONS:
- Use the Visual Forensic Report to identify the specific product/brand and any on-screen text.
- Use the Audio Transcript to understand the spoken message and claims.
- Cross-reference visual and audio evidence to confirm the product identity.
- Perform the ARCON compliance check based on this combined evidence."""
        
        content.append({"type": "text", "text": video_prompt})
        
        # OPTIMIZATION: Do NOT send raw frames to the Agent. 
        # We rely on the detailed Forensic Report to save tokens and avoid Rate Limits.
            
    elif media_type == 'audio':
        processor = MediaProcessor(OPENAI_API_KEY)
        transcript = processor.process_audio(media_file)
        
        audio_prompt = f"""Analyze this audio advertisement for ARCON compliance.

AUDIO TRANSCRIPT:
{transcript}

Identify the product/service being advertised and check for compliance issues."""
        
        content.append({"type": "text", "text": audio_prompt})
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=content)
    ]
    
    # Add retry logic for the main agent call
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            result = agent.invoke({"messages": messages})
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            if "rate_limit_exceeded" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
            raise e
