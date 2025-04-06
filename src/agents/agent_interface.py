from autogen import AssistantAgent
from typing import Callable, Dict, List
from dotenv import load_dotenv
import os

# have a .env file in the root directory with the following content:
# API_KEY=your_openai_api_key
load_dotenv()
OPENAI_API_KEY = os.getenv("API_KEY")

# Define config list
config_list = [
    {

        # use gpt-3.5-turbo-1106 or gpt-4o-mini for POC
        # change to gpt-4 for production
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1"
    }
]

class BaseAgent:
    def __init__(self, name: str, system_prompt: str, tools: List[Callable], description: str, config_list: List[dict] = config_list):
        
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.config_list = config_list
        self.description = description

    def create_agent(self) -> AssistantAgent:
        # Create the assistant agent with system prompt
        agent = AssistantAgent(
            name=self.name,
            system_message=self.system_prompt,
            llm_config={
                "config_list": self.config_list,
                "temperature": 0,
            },
            description=self.description
        )

        # Create a function map from the tools (functions must have __name__ defined)
        function_map: Dict[str, Callable] = {
            func.__name__: func for func in self.tools
        }

        # Register the functions as tools
        agent.register_function(function_map=function_map)

        return agent
