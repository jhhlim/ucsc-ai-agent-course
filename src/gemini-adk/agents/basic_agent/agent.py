from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import google_search

from env_config import get_gemini_model, load_project_env

load_project_env()

root_agent = LlmAgent(
    model=get_gemini_model(),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[google_search]
)
