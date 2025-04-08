import os
from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    UserProxyAgent,
    register_function,
)
from typing import Callable, List
import re

# OPENAI_API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = "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"

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
        name (str): The full name of the player (e.g., "Trevor Lawrence").

    Returns:
        dict: A dictionary containing the player's metric information:
            - "name" (str): The player's full name.
            - "metric" (float or None): The numerical performance metric of the player. None if not found.
            - "error" (str, optional): An error message if the player is not found in the dataset.

    Example:
        result = get_player_metric("Jaylen Waddle")
        # Returns {"name": "Jaylen Waddle", "metric": 9.1}

        result = get_player_metric("Bo Jackson")
        # Returns {"name": "Bo Jackson", "metric": None, "error": "Player not found"}
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

        for tool in self.tools:
            register_function(
                tool,
                caller=agent,
                executor=user_proxy,
                name=tool.__name__,
                description=tool.__doc__ or "Tool function",
            )

        return agent


# Custom class to capture messages with a simpler approach
class CapturingUserProxyAgent(UserProxyAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_messages = []

    def receive(self, message, sender, request_reply=None, silent=False):
        # Store the message content
        if message.get("content"):
            self.all_messages.append(f"{sender.name}: {message.get('content')}")

        # Continue with normal processing
        return super().receive(message, sender, request_reply, silent)


# Create the capturing agent
user_proxy = CapturingUserProxyAgent(
    name="User_proxy",
    human_input_mode="NEVER",  # Changed to NEVER to avoid waiting for human input
    code_execution_config=False,
    description="A human user capable of working with Autonomous AI Agents.",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda msg: msg is not None
                                   and "content" in msg
                                   and msg["content"] is not None
                                   and "TERMINATE" in msg["content"],  # Changed from "**TERMINATE**"
)

quarterback_agent = BaseAgent(
    system_prompt="""
You are an expert in fantasy football quarterbacks. Your job is to select ONE quarterback to recommend.

Instructions:
1. You MUST use the `get_player_metric` tool for each player name provided.
2. Only use the metric output — do not guess or use prior knowledge.
3. Choose the ONE player with the highest metric.
4. Output ONLY the first and last name of that player AND their rating (only one player) — nothing else.

Do NOT list all players or explain your choice.
Do NOT share metrics for anyone else.

""",
    name="quarterback_agent",
    config_list=config_list,
    description="This agent picks the best quarterback.",
    tools=[get_player_metric],
).create_agent()

wide_receiver_agent = BaseAgent(
    system_prompt="""
You are an expert in fantasy football wide receivers. Your job is to select ONE wide receiver to recommend.

Instructions:
1. You MUST use the `get_player_metric` tool for each player name provided.
2. Only use the metric output — do not guess or use prior knowledge.
3. Choose the ONE player with the highest metric.
4. Output ONLY the first and last name of that player AND their rating (only one player) — nothing else.

Do NOT list all players or explain your choice.
Do NOT share metrics for anyone else.

""",
    name="wide_receiver_agent",
    config_list=config_list,
    description="This agent picks the best wide receiver.",
    tools=[get_player_metric],
).create_agent()

running_back_agent = BaseAgent(
    system_prompt="""
You are an expert in fantasy football running backs. Your job is to select ONE running back to recommend.

Instructions:
1. You MUST use the `get_player_metric` tool for each player name provided.
2. Only use the metric output — do not guess or use prior knowledge.
3. Choose the ONE player with the highest metric.
4. Output ONLY the first and last name of that player AND their rating (only one player) — nothing else.

Do NOT list all players or explain your choice.
Do NOT share metrics for anyone else.

""",
    name="running_back_agent",
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

You must NOT infer player metrics from tool outputs or logs. You can only use the final player name that each position agent provides in their message.

Do NOT reconstruct full lists from prior tool calls.

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
    max_round=20,  # Setting a reasonable number of turns
)

manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})

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


def extract_player_name_from_output(output_text):
    """
    Extract the player name from the head drafter agent's final decision message.

    Args:
        output_text (str): The output text from the group chat conversation

    Returns:
        str: The name of the chosen player, or None if no match is found
    """
    # Try multiple patterns to match different message formats

    # Pattern 1: Looks for "my fantasy football team is **PlayerName**"
    match = re.search(r'my fantasy football team is\s+\*\*(.*?)\*\*(?:\.|,)?\s*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        return player_name.strip()

    # Pattern 2: Original pattern - "I choose **PlayerName**"
    match = re.search(r'I choose (?:\*\*)?(.*?)(?:\*\*)?\.\s*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        # Remove any remaining markdown if present
        player_name = re.sub(r'\*\*', '', player_name)
        return player_name.strip()

    # Pattern 3: Most general pattern - looks for bold text right before TERMINATE
    match = re.search(r'\*\*(.*?)\*\*(?:\.|,|\s)*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        return player_name.strip()

    # Pattern 4: Very flexible - looks for name in final message
    lines = output_text.strip().split('\n')
    for i in range(len(lines) - 1, -1, -1):
        if "TERMINATE" in lines[i]:
            # Check the last few lines before TERMINATE for player names
            for j in range(max(0, i - 5), i + 1):
                # Look for bold text in this line
                bold_match = re.search(r'\*\*(.*?)\*\*', lines[j])
                if bold_match:
                    return bold_match.group(1).strip()

    return None


# Run the chat and extract the player
def run_draft_and_get_player():
    print("Starting the draft conversation...")

    # Run the chat
    user_proxy.initiate_chat(
        manager,
        message=message,
        max_turns=20  # Limit the conversation to 20 turns to prevent hanging
    )

    # Get all messages as a single string
    all_messages_text = "\n".join(user_proxy.all_messages)

    # Print for debugging
    print("\nAll messages captured:")
    print(all_messages_text)

    # Extract the player name
    player_name = extract_player_name_from_output(all_messages_text)

    print(f"\nExtracted player choice: {player_name}")
    return player_name


if __name__ == "__main__":
    try:
        # Run the draft and get the player
        player_choice = run_draft_and_get_player()

        # Store the player name for later use
        if player_choice:
            with open("selected_player.txt", "w") as f:
                f.write(player_choice)

            print(f"The selected player name '{player_choice}' has been stored in 'selected_player.txt'")
        else:
            print("No player was selected or the conversation didn't complete properly.")

            # For debugging: write all captured messages to a file
            with open("conversation_log.txt", "w") as f:
                f.write("\n".join(user_proxy.all_messages))
            print("Conversation log saved to 'conversation_log.txt'")

    except Exception as e:
        print(f"An error occurred: {e}")

        # For debugging: write all captured messages to a file even if there was an error
        try:
            with open("conversation_log_error.txt", "w") as f:
                f.write("\n".join(user_proxy.all_messages))
            print("Conversation log saved to 'conversation_log_error.txt'")
        except:
            pass