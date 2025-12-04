import base64
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import check_arcon_compliance
from config import load_config
from media_processor import MediaProcessor
import time

# System Prompt
SYSTEM_PROMPT = """
You are an ARCON Compliance Analyst vetting advertisements against the Nigerian Code of Advertising Practice.

## YOUR TASK
Analyze the advertisement content and check ONLY the ARCON articles that are RELEVANT to what you see/hear. Do not apply a fixed checklist—be dynamic based on the actual content.

## NIGERIAN CULTURAL AWARENESS (CRITICAL)
You MUST understand Nigerian context before flagging anything:

- **Nigerian Pidgin English**: "E sweet well well", "Na the real deal", "E go work" = marketing expressions, NOT literal claims
- **Puffery vs Claims**: "Appreciate every mouthful", "One product, multiple recipes" = creative taglines, NOT health claims
- **Food advertising norms**: Showing prepared dishes with a food product is standard "serving suggestion", not deception
- **Colloquial expressions**: "Chop belle full", "Body go strong" = casual speech, not medical claims unless explicitly stated
- **Aspirational messaging**: "Live your best life", "Enjoy the good things" = lifestyle marketing, acceptable

**RULE: Only flag as non-compliant if there is a CLEAR, LITERAL violation. When in doubt, it's compliant.**

## DYNAMIC ARTICLE MATCHING
Based on the content, check relevant articles from:
- General: Articles 1-24 (Legality, Decency, Honesty, Testimonials, etc.)
- Claims: Articles 25-34 (Misleading, Substantiation, Guarantees, etc.)
- Health/Food: Articles 56-72 (Only if actual health/medical claims are made)
- Alcohol: Articles 35-47 (Only for alcoholic beverages)
- Tobacco: Article 48 (Only for tobacco products)
- Gambling: Article 54 (Only for betting/lottery)
- Minors: Articles 9, 105-116 (Only if content targets or features children)
- Financial: Articles 93-104 (Only for financial services)
- Telecoms: Articles 80-85 (Only for telecom products)

## OUTPUT FORMAT

**Product:** [Name and category]

**Compliance Score:** [X]% 
(100% = Fully compliant, deduct points only for actual violations)

**Compliance Summary:**
| Area Checked | Status | Article | Remarks |
|--------------|--------|---------|---------|
| [Relevant area 1] | PASS or FAIL | Art. X | Brief note |
| [Relevant area 2] | PASS or FAIL | Art. X | Brief note |
| [Add more rows as needed based on content] |

**Verdict:** COMPLIANT / NON-COMPLIANT

**Issues Found:** (Only if score < 100%)
- [Specific violation with Article reference]

**Recommendations:** (Only if non-compliant)
- [Actionable fix]
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
