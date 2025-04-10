from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    UserProxyAgent,
    register_function,
)
from typing import Callable, List
import re

from combined_fantasy_tools import (
    find_player_stats,
    get_players_by_position,
    display_position_rankings
)

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


def get_player_metric(name: str, position: str) -> dict:
    """
    Retrieve the fantasy football metric for a given player, including their position.

    Args:
        name (str): The full name of the player.
        position (str): The position of the player (e.g., 'QB', 'WR', 'RB').

    Returns:
        dict: Dictionary with the following keys:
            - "name": player's name (str)
            - "position": player's position (str)
            - "metric": player's metric (float), or None if not found
            - "error": error message if player not found (optional)

    Example:
        get_player_metric("Trevor Lawrence", "QB")
        => {"name": "Trevor Lawrence", "position": "QB", "metric": 9.5}
    """
    if name in player_metrics:
        return {"name": name, "position": position, "metric": player_metrics[name]}
    else:
        return {
            "name": name,
            "position": position,
            "metric": None,
            "error": "Player not found",
        }


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


# Custom class to capture messages similar to the first code file
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


# Create the capturing agent instead of the regular UserProxyAgent
user_proxy = CapturingUserProxyAgent(
    name="User_proxy",
    human_input_mode="NEVER",  # Changed to NEVER to avoid waiting for human input
    code_execution_config=False,
    description="A human user capable of working with Autonomous AI Agents.",
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda msg: msg is not None
                                   and "content" in msg
                                   and msg["content"] is not None
                                   and "TERMINATE" in msg["content"],
)

# Prompts
EXTRACTOR_PROMPT = (
    lambda position: f"""
You are a data extractor for the SPECIFIED position {position}. Your job is to fetch comprehensive metrics for each provided player.

You have access to these tools:
1. get_position_rankings(position: str, limit: int, excluded_players: List[str]) - Get rankings for players in your position. The position parameter will be one of (QB, RB, WR, TE, K, DST). You can exclude all drafted players by adding them to the excluded_players parameter, so that you don't even consider them.

Use the tools appropriately to gather information and return all results.
"""
)

ANALYZER_PROMPT = (
    lambda position: f"""
You are a fantasy position expert for the SPECIFIED positon {position} - do NOT speak for other positions AT ALL.
If you speak for other positions, you will be terminated.
You are in a conversation with an extractor agent for YOUR POSITION and a head drafter.
You must ask the extractor agent to fetch the stats for each player after which you will receive stats for each player.
First, ask for the top 10 rankings for your position.
Then, decide which players to take based on their ranking and their "Schedule_Rating" field. Schedule rating is not a huge
factor for much better players but if players are similar, we should take ones with a better schedule. 
Additionally, you have access to how good the offense of the player is. If an offense is much, much better than other players,
let's take that player. But, if they are similar, then this doesn't matter.
Then, you can request detailed information about specific players you're interested in.
You should ONLY ask for players relevant to YOUR position.
You MUST pick the ONE best player THAT IS IN THE AVAILABLE PLAYER LIST and ONLY give the head drafter agent ONLY the player's full name and metric in this format:
<Full Name>\n**TERMINATE**
"""
)


def make_extractor_analyzer_agents(position: str):
    """
    Creates a pair of agents for a specific position:
    - Extractor: fetches player metrics
    - Analyzer: picks the best player from those metrics

    Args:
        position (str): The football position (e.g., 'qb', 'wr', 'rb')

    Returns:
        tuple: (extractor_agent, analyzer_agent)
    """
    extractor = BaseAgent(
        name=f"{position}_extractor",
        system_prompt=EXTRACTOR_PROMPT(position),
        config_list=config_list,
        description=f"Extracts {position} player data",
        tools=[find_player_stats,
               get_players_by_position,
               display_position_rankings],
    ).create_agent()

    analyzer = AssistantAgent(
        name=f"{position}_analyzer",
        system_message=ANALYZER_PROMPT(position),
        llm_config={"config_list": config_list},
        description=f"Analyzes and ranks {position} players only - NO OTHER POSITIONS",
    )

    return extractor, analyzer


qb_extractor, qb_analyzer = make_extractor_analyzer_agents("quarter_back")
wr_extractor, wr_analyzer = make_extractor_analyzer_agents("wide_receiver")
rb_extractor, rb_analyzer = make_extractor_analyzer_agents("running_back")

head_drafter_agent = AssistantAgent(
    name="head_drafter_agent",
    system_message="""
You are in a conversation with analyzer agents for quarter back, wide receiver, and running back.
If there is already a player on your team for a certain position, you MUST ignore that position - do NOT ask the anaylzer for that position.
Each analyzer gives their best pick.
You MUST NOT draft a player until you have received the top pick from each ANALYZER AGENT.
You MUST only give each anaylzer agent the list of players in the position they are responsible for.
Do NOT hallucinate yourself, you are in a conversation with specialized position agents - you MUST consult with them first


The analyzers MUST rely on extractor agents to fetch metrics, and you must allow that process to complete.
Once you have all three final recommendations, discuss their names and metrics and choose ONE player to draft. 
Output their full name and write TERMINATE.
""",
    llm_config={"config_list": config_list},
    description="Picks best overall player to draft.",
)

groupchat = GroupChat(
    agents=[
        user_proxy,
        qb_extractor,
        qb_analyzer,
        wr_extractor,
        wr_analyzer,
        rb_extractor,
        rb_analyzer,
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
Quarterbacks (QB):
  1. Trevor Lawrence (Clemson) - QB
  2. Justin Fields (Ohio State) - QB
  3. Zach Wilson (BYU) - QB
  4. Trey Lance (North Dakota State) - QB
  5. Mac Jones (Alabama) - QB

Running Backs (RB):
  1. Najee Harris (Alabama) - RB
  2. Travis Etienne (Clemson) - RB
  3. Javonte Williams (North Carolina) - RB

Wide Receivers (WR):
  1. Ja'Marr Chase (LSU) - WR
  3. Jaylen Waddle (Alabama) - WR
  4. Rashod Bateman (Minnesota) - WR
  5. Kadarius Toney (Florida) - WR
"""

message = (
        "Here are the available players that can be drafted: "
        + available_players
        + "Here is your current team: \n"
        + "DeVonta Smith - WR (Alabama) \n\n"
        + "What is your next pick for your team? \n"
)


def extract_player_name_from_output(output_text):
    """
    Extract the player name from the head drafter agent's final decision message.

    Args:
        output_text (str): The output text from the group chat conversation

    Returns:
        str: The name of the chosen player, or None if no match is found
    """
    # Split by 'head_drafter_agent:' to focus only on the head drafter's messages
    # Then take the last message which should contain the final decision
    head_drafter_messages = output_text.split('chat_manager:')

    # If we have at least 2 messages from the head drafter
    if len(head_drafter_messages) >= 2:
        # Get the last message which should have the final decision
        final_message = head_drafter_messages[-1]

        # Check if the message contains "TERMINATE"
        if "TERMINATE" in final_message:
            # Pattern 1: Looks for bold text near end of message
            match = re.search(r'\*\*(.*?)\*\*\s*(?:\.|,|\s)*TERMINATE', final_message)
            if match:
                player_name = match.group(1)
                return player_name.strip()

            # Pattern 2: Look for the player name that appears right before TERMINATE
            # Get the lines before TERMINATE
            lines = final_message.strip().split('\n')
            terminate_index = -1

            for i, line in enumerate(lines):
                if "TERMINATE" in line:
                    terminate_index = i
                    break

            if terminate_index > 0:
                # Check the line immediately before TERMINATE
                prev_line = lines[terminate_index - 1].strip()
                if prev_line and len(prev_line) > 0 and not prev_line.startswith('-') and not prev_line.startswith('*'):
                    # This is likely our player name
                    return prev_line.strip()

    # If we couldn't find the name using the preferred methods, fall back to checking the last occurrence
    # of a player name before TERMINATE in the entire text

    # First, find the last occurrence of "TERMINATE"
    last_terminate_pos = output_text.rfind("TERMINATE")
    if last_terminate_pos > 0:
        # Extract the 500 characters before the last TERMINATE
        context_before = output_text[max(0, last_terminate_pos - 500):last_terminate_pos]

        # Look for any player names in this context
        for player in player_metrics.keys():
            if player in context_before:
                # Find the last occurrence of this player name
                last_pos = context_before.rfind(player)
                if last_pos > 0:
                    return player

    # If all else fails, check for any specific indicators in the text
    match = re.search(r'I will go ahead and draft\s+\*\*(.*?)\*\*', output_text)
    if match:
        return match.group(1).strip()

    return None


# Run the chat and extract the player
def run_draft_and_get_player():
    print("Starting the draft conversation...")

    # Run the chat
    user_proxy.initiate_chat(
        manager,
        message=message,
        max_turns=100  # Limit the conversation to avoid hanging
    )

    # Get all messages as a single string
    all_messages_text = "\n".join(user_proxy.all_messages)

    # Extract the player name
    player_name = extract_player_name_from_output(all_messages_text)

    # Additional validation check
    print("\nExtraction process:")
    # Get the last 500 characters before TERMINATE
    last_terminate_pos = all_messages_text.rfind("TERMINATE")
    if last_terminate_pos > 0:
        context = all_messages_text[max(0, last_terminate_pos - 500):last_terminate_pos + 10]
        print(f"Context around final TERMINATE:\n{context}")

    # Highlight chosen player
    if player_name:
        highlighted_context = all_messages_text.replace(player_name, f">>> {player_name} <<<")
        print(f"\nHighlighted player in final message:\n{highlighted_context[-500:]}")

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