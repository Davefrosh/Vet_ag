import base64
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import check_arcon_compliance
from config import load_config

# System Prompt
SYSTEM_PROMPT = """
# OVERVIEW
You are an expert Senior Compliance Officer for ARCON (Advertising Regulatory Council of Nigeria). 
Your role is to rigorously vet advertisement images and text against the Nigerian Code of Advertising Practice.

# RULES
1. **Vision Analysis**: You have vision capabilities. Analyze any provided image thoroughly. Identify the product, all text claims, visual elements (models, setting), and any disclaimers.
2. **Fact-Checking**: Do not assume compliance. Use the `check_arcon_compliance` tool to find the specific articles that apply to the product category (e.g., Alcohol, Health, Banking) or the claims made.
3. **Strict Enforcement**: Apply the regulations strictly. If a rule says "No minors," and you see a minor, it is NON-COMPLIANT.
4. **Citation**: You MUST cite specific Articles from the retrieved regulations to support your decision.

# TOOLS
- `check_arcon_compliance(query)`: Use this to look up the law. 
  - Example 1: If the ad is for beer, search "alcohol advertising rules".
  - Example 2: If the ad claims "Cures all cancer", search "health claims cure diseases".

# OUTPUT
Your final response must be structured exactly as follows:

**1. Analysis of Advertisement**
   - **Product/Service**: [Name/Type]
   - **Visuals**: [Description of images/people]
   - **Claims**: [Text claims found]

**2. Regulatory Checks**
   - [Regulation Topic]: [Relevant Article #] - [Pass/Fail]
   - *Reasoning based on retrieved text.*

**3. Final Verdict**
   - **Decision**: [COMPLIANT / NON-COMPLIANT]
   - **Summary**: Brief explanation of the decision.
   - **Recommendations**: (If non-compliant) Specific changes required to fix it.

# EXAMPLE
**1. Analysis of Advertisement**
   - **Product**: Star Lager Beer
   - **Visuals**: A group of young people (looking under 18) drinking at a beach party.
   - **Claims**: "The taste of freedom."

**2. Regulatory Checks**
   - Models in Alcohol Ads: Article 36 - Fail
   - *Reasoning: Article 36 prohibits using minors or young persons in alcohol ads.*

**3. Final Verdict**
   - **Decision**: NON-COMPLIANT
   - **Summary**: The ad violates Article 36 by using models that appear to be minors.
   - **Recommendations**: Replace models with obvious adults (over 21) and ensure they are not portrayed engaging in irresponsible drinking.
"""

def get_agent():
    # Initialize the LLM - using GPT-4o-mini for cost efficiency with multimodal capabilities
    OPENAI_API_KEY, _, _ = load_config()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    
    tools = [check_arcon_compliance]
    
    # Create the ReAct agent using LangGraph's prebuilt function
    graph = create_react_agent(llm, tools=tools, messages_modifier=SYSTEM_PROMPT)
    
    return graph

def run_agent(user_input: str, image_file=None):
    """
    Runs the agent with the given input and optional image file (bytes).
    
    Args:
        user_input: Text prompt from the user.
        image_file: Optional file-like object containing the image.
    """
    agent = get_agent()
    
    content = [{"type": "text", "text": user_input}]
    
    if image_file:
        # Convert image bytes to base64
        image_file.seek(0)
        image_data = base64.b64encode(image_file.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        })
        
    messages = [HumanMessage(content=content)]
    
    # Invoke the agent
    result = agent.invoke({"messages": messages})
    
    # Extract the final response
    last_message = result["messages"][-1]
    
    return last_message.content
