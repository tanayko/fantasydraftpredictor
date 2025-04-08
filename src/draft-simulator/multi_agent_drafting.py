import os
from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    UserProxyAgent,
    register_function,
)
from typing import Callable, List

OPENAI_API_KEY = os.getenv("API_KEY")

config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
    }
]

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


def get_player_metric(name: str) -> dict:
    """
    Retrieve the fantasy football metric for a given player.

    Args:
        name (str): The full name of the player.

    Returns:
        dict: Dictionary with player's name, metric, and optional error.
    """
    if name in player_metrics:
        return {"name": name, "metric": player_metrics[name]}
    else:
        return {"name": name, "metric": None, "error": "Player not found"}


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

        agent.reflect_on_tool_use = True
        agent.output_content_type = "structured"
        agent.include_tools_in_prompt = True

        for tool in self.tools:
            register_function(
                tool,
                caller=agent,
                executor=agent,
                name=tool.__name__,
                description=tool.__doc__ or "Tool function",
            )

        return agent


user_proxy = UserProxyAgent(
    name="User_proxy",
    human_input_mode="TERMINATE",
    code_execution_config=False,
    description="A human user capable of working with Autonomous AI Agents.",
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda msg: msg is not None
    and "content" in msg
    and msg["content"] is not None
    and "TERMINATE" in msg["content"],
)

# ---------------- Agent Prompts with Structured Flow ------------------
QB_PROMPT = """
You are an expert in fantasy football quarterbacks. Your job is to select ONE quarterback to recommend.

Step 1:
- Use the `get_player_metric` tool to fetch the metric for each player.

Step 2 (on your next turn):
- Identify the player with the highest metric.
- Output ONLY their full name and metric in the format:
  <Full Name> (Metric: <Metric Score>)
- Then write: **TERMINATE**

Do NOT list other players or explain your reasoning.
"""

WR_PROMPT = QB_PROMPT.replace("quarterback", "wide receiver")

RB_PROMPT = QB_PROMPT.replace("quarterback", "running back")

quarterback_agent = BaseAgent(
    name="quarterback_agent",
    system_prompt=QB_PROMPT,
    config_list=config_list,
    description="This agent picks the best quarterback.",
    tools=[get_player_metric],
).create_agent()

wide_receiver_agent = BaseAgent(
    name="wide_receiver_agent",
    system_prompt=WR_PROMPT,
    config_list=config_list,
    description="This agent picks the best wide receiver.",
    tools=[get_player_metric],
).create_agent()

running_back_agent = BaseAgent(
    name="running_back_agent",
    system_prompt=RB_PROMPT,
    config_list=config_list,
    description="This agent picks the best running back.",
    tools=[get_player_metric],
).create_agent()

head_drafter_agent = AssistantAgent(
    name="head_drafter_agent",
    system_message="""
You are in a conversation with 3 agents. One will give you the best QB, one the best WR, and one the best RB.

Your job is to build a fantasy football team with 1 QB, 1 WR, and 1 RB. 
You MUST ask each agent for their top player, then choose one player for the next draft pick.

Once you have the players, discuss their names and the metrics and choose the best one.

You must NOT infer player metrics from tool outputs or logs. You can ONLY use the 
final player name and their ratings that each position agent provides as best in their message.

At the end, return the first and last name of the chosen player. ALSO say TERMINATE to end the conversation.
""",
    llm_config={"config_list": config_list},
    description="This agent picks the best overall player for the next draft slot.",
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
    llm_config={"config_list": config_list},
    max_consecutive_auto_reply=20,
    system_message="You are a group chat manager. You will manage the conversation between the agents.",
)

available_players = """
QB:
  1. Trevor Lawrence (Clemson)
  2. Justin Fields (Ohio State)
  3. Zach Wilson (BYU)
  4. Trey Lance (North Dakota State)
  5. Mac Jones (Alabama)

RB:
  1. Najee Harris (Alabama)
  2. Travis Etienne (Clemson)
  3. Javonte Williams (North Carolina)

WR:
  1. Ja'Marr Chase (LSU)
  2. DeVonta Smith (Alabama)
  3. Jaylen Waddle (Alabama)
  4. Rashod Bateman (Minnesota)
  5. Kadarius Toney (Florida)
"""

message = (
    "Here are the available players that can be drafted: "
    + available_players
    + "Here is your current team: "
    + "What is your next pick for your team?"
)

user_proxy.initiate_chat(manager, message=message, max_consecutive_auto_reply=100)
