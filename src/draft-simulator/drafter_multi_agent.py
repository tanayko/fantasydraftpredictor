import os
import re
from typing import List, Optional, Callable
from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    UserProxyAgent,
    register_function,
)
from combined_fantasy_tools import (
    display_position_rankings_with_filtering
)


class BaseAgent:
    def __init__(
            self,
            name: str,
            system_prompt: str,
            tools: List[Callable],
            description: str,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.config_list = [
            {
                "model": "gpt-4o-mini",  # Use gpt-4o-mini for more affordability
                "api_key": "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",
                "base_url": "https://api.openai.com/v1",
            }
        ]
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


# AutoGen drafter using multi-agent approach
class AutoGenDrafter:
    """An advanced AutoGen-powered drafter using multi-agent conversations"""

    def __init__(self, team_name="AutoGen Multi-Agent GM"):
        self.team_name = team_name
        self.api_key = "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"
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        self.config_list = [
            {
                "model": "gpt-4o-mini",  # Use gpt-4o-mini for more affordability
                "api_key": self.api_key,
                "base_url": "https://api.openai.com/v1",
            }
        ]
        # Initialize agents dictionary to be created later
        self.agents = {}
        self.available_players = None
        self.drafted_players = []  # Track drafted players

    def set_drafted_players(self, drafted_players: List[str]):
        """
        Update the list of drafted players

        Args:
            drafted_players: List of player names that have been drafted
        """
        self.drafted_players = drafted_players

    def initialize_agents(self):
        """Initialize all the necessary agents for the draft"""
        # Create position-specific extractor and analyzer agents
        qb_extractor, qb_analyzer = self.make_extractor_analyzer_agents("quarterback")
        wr_extractor, wr_analyzer = self.make_extractor_analyzer_agents("wide_receiver")
        rb_extractor, rb_analyzer = self.make_extractor_analyzer_agents("running_back")

        # Custom class to capture messages in conversation
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

        # Create the user proxy agent
        user_proxy = CapturingUserProxyAgent(
            name="User_proxy",
            human_input_mode="NEVER",  # Never wait for human input
            code_execution_config=False,
            description="A human user capable of working with Autonomous AI Agents.",
            max_consecutive_auto_reply=5,
            is_termination_msg=lambda msg: msg is not None
                                           and "content" in msg
                                           and msg["content"] is not None
                                           and "TERMINATE" in msg["content"],
        )

        # Create the head drafter agent
        head_drafter_agent = AssistantAgent(
            name="head_drafter_agent",
            system_message="""
            You are in a conversation with analyzer agents for quarterback, wide receiver, and running back.
            If there is already a player on your team for a certain position, you MUST ignore that position - do NOT ask the analyzer for that position.
            Each analyzer gives their best pick.
            You MUST NOT draft a player until you have received the top pick from each ANALYZER AGENT.
            You MUST only give each analyzer agent the list of players in the position they are responsible for.
            You MUST also give each analyzer agent the list of players that have been drafted.
            Do NOT hallucinate yourself, you are in a conversation with specialized position agents - you MUST consult with them first.

            The analyzers MUST rely on extractor agents to fetch metrics, and you must allow that process to complete.
            Once you have all recommendations, discuss their names and metrics and choose ONE player to draft. 
            Output their full name and write TERMINATE.
            """,
            llm_config={"config_list": self.config_list},
            description="Picks best overall player to draft.",
        )

        # Store all agents
        self.agents = {
            "qb_extractor": qb_extractor,
            "qb_analyzer": qb_analyzer,
            "wr_extractor": wr_extractor,
            "wr_analyzer": wr_analyzer,
            "rb_extractor": rb_extractor,
            "rb_analyzer": rb_analyzer,
            "head_drafter": head_drafter_agent,
            "user_proxy": user_proxy
        }

        # Create the group chat
        groupchat = GroupChat(
            agents=[
                user_proxy,
                qb_extractor, qb_analyzer,
                wr_extractor, wr_analyzer,
                rb_extractor, rb_analyzer,
                head_drafter_agent,
            ],
            messages=[],
            max_round=100,
        )

        # Create the manager
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config={"config_list": self.config_list},
            max_consecutive_auto_reply=20,
            system_message="You are a group chat manager. You will manage the conversation between the agents.",
        )

        self.agents["manager"] = manager

    def make_extractor_analyzer_agents(self, position: str):
        """Create extractor and analyzer agents for a specific position"""
        # Extractor prompt
        extractor_prompt = f"""
        You are a data extractor for the SPECIFIED position {position}. Your job is to fetch comprehensive metrics for each provided player.

        You have access to these tools:
        1. display_position_rankings_with_filtering(position: str, limit: int, ) - Get rankings for players in your position. The position parameter will be one of (QB, RB, WR, TE, K, DST). IMPORTANT: Add all drafted players to the excluded_players parameter.

        Use the tools appropriately to gather information and return all results.
        """

        # Analyzer prompt
        analyzer_prompt = f"""
        You are a fantasy position expert for the SPECIFIED position {position} - do NOT speak for other positions AT ALL.
        If you speak for other positions, you will be terminated.
        You are in a conversation with an extractor agent for YOUR POSITION and a head drafter.
        You must ask the extractor agent to fetch the stats for each player after which you will receive stats for each player.
        First, ask for the top 10 rankings for your position and give the list of players that have been drafted.
        Then, decide which players to take based on their ranking and their "Schedule_Rating" field. Schedule rating is not a huge
        factor for much better players but if players are similar, we should take ones with a better schedule. 
        Additionally, you have access to how good the offense of the player is. If an offense is much, much better than other players,
        let's take that player. But, if they are similar, then this doesn't matter.
        Then, you can request detailed information about specific players you're interested in.
        You should ONLY ask for players relevant to YOUR position.
        You MUST pick the ONE best player THAT IS IN THE AVAILABLE PLAYER LIST and ONLY give the head drafter agent ONLY the player's full name and metric in this format:
        <Full Name>\n**TERMINATE**
        """

        # Create the extractor agent
        extractor = BaseAgent(
            name=f"{position}_extractor",
            system_prompt=extractor_prompt,
            description=f"Extracts {position} player data",
            tools=[display_position_rankings_with_filtering],
        ).create_agent()

        # Create the analyzer agent
        analyzer = AssistantAgent(
            name=f"{position}_analyzer",
            system_message=analyzer_prompt,
            llm_config={"config_list": self.config_list},
            description=f"Analyzes and ranks {position} players only - NO OTHER POSITIONS",
        )

        return extractor, analyzer

    def get_available_players(self, players):
        """Format available players in a structure for the draft agents"""
        # Filter out already drafted players (both by drafted flag and by name in drafted_players list)
        self.available_players = [p for p in players if not p.drafted and p.name not in self.drafted_players]
        return self.available_players

    def extract_player_name_from_output(self, output_text):
        """Extract the player name from the chat output"""
        # First, find the last occurrence of "TERMINATE"
        last_terminate_pos = output_text.rfind("TERMINATE")
        if last_terminate_pos <= 0:
            return None

        # Extract the 500 characters before the last TERMINATE
        context_before = output_text[max(0, last_terminate_pos - 500):last_terminate_pos]

        # Look for lines immediately before TERMINATE
        lines = context_before.strip().split('\n')
        for i in range(len(lines) - 1, -1, -1):
            # Skip empty lines or lines with special markers
            line = lines[i].strip()
            if not line or line.startswith('-') or line.startswith('*'):
                continue

            # Check if this line contains a player name
            for player in self.available_players:
                if player.name in line:
                    return player.name

        # If we can't find a match using player names, look for bold text pattern
        match = re.search(r'\*\*(.*?)\*\*\s*(?:\.|,|\s)*TERMINATE', output_text)
        if match:
            potential_name = match.group(1).strip()
            # Check if the extracted name is not in the drafted players list
            if potential_name not in self.drafted_players:
                return potential_name

        # Look for patterns indicating drafting
        match = re.search(r'I (?:choose|select|draft|pick)\s+\*?\*(.*?)\*?\*', output_text, re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip()
            # Check if the extracted name is not in the drafted players list
            if potential_name not in self.drafted_players:
                return potential_name

        return None

    def make_draft_selection(self, available_players, team, draft_position, current_round):
        """Use the multi-agent system to make a draft decision"""
        # Initialize agents if not already done
        if not self.agents:
            self.initialize_agents()

        # Store available players
        self.available_players = [p for p in available_players if not p.drafted and p.name not in self.drafted_players]

        # Format players by position for the agents
        formatted_players = ""
        position_players = {}

        # Group players by position
        for player in self.available_players:
            pos = player.position
            if pos not in position_players:
                position_players[pos] = []
            position_players[pos].append(player)

        # Format the player list
        for pos in sorted(position_players.keys()):
            formatted_players += f"\n{pos}s ({pos}):\n"
            for idx, player in enumerate(position_players[pos], 1):
                formatted_players += f"  {idx}. {player.name} ({player.team}) - {pos}\n"

        # Format current roster
        current_roster = ""
        if team.roster:
            current_roster = "Here is your current team: \n"
            for pos, players in team.roster.items():
                for player in players:
                    current_roster += f"{player.name} - {player.position} ({player.team}) \n"

        # Add drafted players info if any exist
        drafted_info = ""
        if self.drafted_players:
            drafted_info = "\nThese players have already been drafted (DO NOT select them):\n"
            for name in self.drafted_players:
                drafted_info += f"- {name}\n"

        # Build the message
        message = (
                f"Here are the available players that can be drafted: "
                + formatted_players
                + drafted_info
                + current_roster
                + f"\nYou are making a selection in Round {current_round}, Pick {draft_position}.\n"
                + "What is your next pick for your team? \n"
        )

        # Get the user proxy and manager
        user_proxy = self.agents["user_proxy"]
        manager = self.agents["manager"]

        print("Starting the multi-agent draft conversation...")

        # Run the chat
        user_proxy.initiate_chat(
            manager,
            message=message,
            max_turns=100  # Limit the conversation
        )

        # Get all messages as a single string
        all_messages_text = "\n".join(user_proxy.all_messages)

        # For debugging
        if os.getenv("DEBUG_DRAFT"):
            print("\nAll messages captured:")
            print(all_messages_text)

        # Extract the player name
        player_name = self.extract_player_name_from_output(all_messages_text)

        # If we couldn't get a player via the normal process, save logs and use fallback
        if not player_name:
            print("Could not extract player name from agent conversation.")

            # Write logs for debugging
            with open("conversation_log.txt", "w") as f:
                f.write(all_messages_text)
            print("Conversation log saved to 'conversation_log.txt'")

            # Fallback: pick highest rated player
            for player in sorted(self.available_players, key=lambda p: p.rating, reverse=True):
                player_name = player.name
                print(f"Fallback selection: {player_name}")
                break

        return player_name