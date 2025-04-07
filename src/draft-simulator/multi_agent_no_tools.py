import os

from autogen import GroupChat, AssistantAgent
from autogen import GroupChatManager

import autogen
from typing import Callable, Dict, List

OPENAI_API_KEY = os.getenv("API_KEY")
config_list = [
    {
        # use gpt-3.5-turbo-1106 or gpt-4o-mini for POC
        # # change to gpt-4 for production
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
    }
]


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: List[Callable],
        description: str,
        config_list: List[dict] = config_list,
    ):
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
                "cache_seed": None,
            },
            description=self.description,
        )

        # Create a function map from the tools (functions must have __name__ defined)
        function_map: Dict[str, Callable] = {func.__name__: func for func in self.tools}

        # Register the functions as tools
        agent.register_function(function_map=function_map)

        return agent


user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    human_input_mode="ALWAYS",
    code_execution_config=False,
    description="A human user capable of working with Autonomous AI Agents.",
)

player_metrics = {
    "Trevor Lawrence": 9.5,
    "Justin Fields": 9.2,
    "Zach Wilson": 8.9,
    "Trey Lance": 8.7,
    "Mac Jones": 8.5,
    "Najee Harris": 8.9,
    "Travis Etienne": 8.7,
    "Javonte Williams": 8.5,
    "Ja'Marr Chase": 3.1,
    "DeVonta Smith": 9.3,
    "Jaylen Waddle": 9.1,
    "Rashod Bateman": 8.7,
    "Kadarius Toney": 8.6,
}


def get_player_metric(name: str) -> float:
    """
    Retrieve the fantasy football metric for a given player.

    Args:
        name: The full name of the player (e.g., "Trevor Lawrence").

    Returns:
        The player's metric as a float if found, or a message indicating the player was not found.

    Example:
        metric = get_player_metric("Ja'Marr Chase")  # Returns 9.4
        unknown = get_player_metric("Bo Jackson")    # Returns "Player not found"
    """
    return player_metrics.get(name, "Player not found")


quarterback_agent = BaseAgent(
    system_prompt="""
    You are an expert in fantasy football quarterbacks, and your job is to choose a single quarterback 
    for your fantasy football team. You should only generate the first and last name of the quarterback you're 
    choosing and nothing else. 
    
    IMPORTANT: You should only make a decision based on the player rating you receive from the prompt, no prior knowledge. 
    Select the highest rated quarterback from the available ones. You should not use any outside knowledge of these players.

    Provide the first and last name of the quarterback to draft.
    """,
    name="quarterback_agent",
    config_list=config_list,
    description="""This agent is responsible for determining the single best quarterback to be drafted out of all available quarterbacks.
    """,
    tools=[],
).create_agent()

wide_receiver_agent = BaseAgent(
    system_prompt="""
    You are an expert in fantasy football wide receivers, and your job is to choose a single wide receiver 
    for your fantasy football team. You should only generate the first and last name of the wide receiver you're 
    choosing and nothing else. 
    
    IMPORTANT: You should only make a decision based on the player rating you receive from the prompt, no prior knowledge. 
    Select the highest rated wide receiver from the available ones. You should not use any outside knowledge of these players.

    Provide the first and last name of the wide receiver to draft.
    """,
    name="wide_receiver_agent",
    config_list=config_list,
    description="""This agent is responsible for determining the single best wide receiver to be drafted out of all available wide receivers.
    """,
    tools=[],
).create_agent()

running_back_agent = BaseAgent(
    system_prompt="""
    You are an expert in fantasy football running backs, and your job is to choose a single running back
    for your fantasy football team. You should only generate the first and last name of the running back you're 
    choosing and nothing else. 
    
    IMPORTANT: You should only make a decision based on the player rating you receive from the prompt, no prior knowledge. 
    Select the highest rated running back from the available ones. You should not use any outside knowledge of these players.

    Provide the first and last name of the running back to draft.
    """,
    name="running_back_agent",
    config_list=config_list,
    description="""This agent is responsible for determining the single best running back to be drafted out of all available running backs.
    """,
    tools=[],
).create_agent()

head_drafter_agent = autogen.AssistantAgent(
    system_message="""
    You are in a conversation with 3 agents. One agent will give you the single best quarterback,
    one agent will give you the single best wide receiver, and one agent will give you the single best running
    back. Your job is to draft a fantasy football team. The format of the teams in this league is 
    1 Quarterback, 1 Wide Receiver, and 1 Running Back. So, determine what you think the team needs at the moment
    and based on that, ask the agents for the options you can draft (they will give you 1 player that they think
    should be drafted at their specialized position), and choose a player to draft. You should never choose who to draft
    before conversing with the other agents that know who the best available player is at each position. Because this is 
    only for one round of the draft, you will only need to choose one player for now. Respond with the first
    and last name of the player that you want to draft based on the options you were given in the conversation.
    """,
    name="head_drafter_agent",
    llm_config={
        "config_list": config_list,
    },
    description="""This agent is responsible for determining the next pick for the fantasy football team, 
    and will give the first and last name of the player.
    """,
)

groupchat = GroupChat(
    agents=[
        user_proxy,
        quarterback_agent,
        wide_receiver_agent,
        running_back_agent,
        head_drafter_agent,
    ],
    messages=[],
    max_round=100,
)
manager = GroupChatManager(
    groupchat=groupchat,
    llm_config={
        "config_list": config_list,
    },
)

available_players = """
QB:
  
Trevor Lawrence (Clemson) - Rating: 9.5
Justin Fields (Ohio State) - Rating: 9.2
Zach Wilson (BYU) - Rating: 8.9
Trey Lance (North Dakota State) - Rating: 8.7
Mac Jones (Alabama) - Rating: 8.5

RB:
  
Najee Harris (Alabama) - Rating: 8.9
Travis Etienne (Clemson) - Rating: 8.7
Javonte Williams (North Carolina) - Rating: 8.5

WR:
  
Ja'Marr Chase (LSU) - Rating: 3.1
DeVonta Smith (Alabama) - Rating: 9.3
Jaylen Waddle (Alabama) - Rating: 9.1
Rashod Bateman (Minnesota) - Rating: 8.7
Kadarius Toney (Florida) - Rating: 8.6
"""


message = (
    "Here are the available players that can be drafted: "
    + available_players
    + "Here is your current team: "
    + "What is your next pick for your team?"
)

user_proxy.initiate_chat(manager, message=message)
