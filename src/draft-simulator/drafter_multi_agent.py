import os
import re
from typing import List, Callable
from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    UserProxyAgent,
    register_function,
)
from combined_fantasy_tools import display_position_rankings_with_filtering


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
                "api_key": os.getenv("API_KEY"),
                "base_url": "https://api.openai.com/v1",
            }
        ]
        self.description = description

    def create_agent(self) -> AssistantAgent:
        agent = AssistantAgent(
            name=self.name,
            system_message=self.system_prompt,
            llm_config={
                "cache_seed": None,
                "config_list": self.config_list,
            },
            description=self.description,
        )

        agent.client.cache = None

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
        self.api_key = os.getenv("API_KEY")
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
        te_extractor, te_analyzer = self.make_extractor_analyzer_agents("tight_end")

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

        # Create the head drafter agent with updated prompt
        head_drafter_agent = AssistantAgent(
            name="head_drafter_agent",
            system_message="""
            You are the Head Drafter for a fantasy football team. Your role is to coordinate the draft process and make the final player selection.
            Make smart decisions based on the recommendations from the position-specific analyzers and strategies you already know.

            DRAFT PROCESS:
            1. FIRST: Review the current roster and identify positions that still need to be filled
               - A complete roster needs: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX (RB/WR)
               - IMPORTANT: YOUR ROSTER MUST HAVE THIS FORMAT (ONE QUARTERBACK, TWO RUNNING BACKS, 2 WIDE RECEIVERS, 1 TIGHT END, 1 FLEX)
               - IF YOU DON'T HAVE A TIGHT END IN THE LAST ROUND, YOU MUST TAKE A TIGHT END
               - IF YOU DON'T HAVE A QUARTERBACK IN THE LAST ROUND, YOU MUST TAKE A QUARTERBACK
               - You just need recommendations for each position ONCE per round and choose only ONE player, not the whole roster.

            2. SECOND: Request recommendations from position-specific analyzer agents
               - ONLY ask analyzers for positions you still need to fill
               - Ask one analyzer at a time and wait for their response before asking another
               - NEVER make up or predict what an analyzer might recommend - wait for their actual response

            3. THIRD: After collecting recommendations, evaluate them and select ONE player to draft
               - In early rounds, prioritize RB and WR positions unless an exceptional QB or TE is available
               - Never consider players from the "already drafted" list
               - Try not to draft players on the same NFL team

            COMMUNICATE CLEARLY:
            - When asking an analyzer for a recommendation, direct your message specifically to them (e.g., "running_back_analyzer, what is your recommendation?")
            - Wait for each analyzer to respond before asking the next one
            - When making your final decision, clearly state the selected player's full name

            FINAL SELECTION FORMAT:
            - IMPORTANT: YOUR ROSTER MUST HAVE THIS FORMAT (ONE QUARTERBACK, TWO RUNNING BACKS, 2 WIDE RECEIVERS, 1 TIGHT END, 1 FLEX)
            - If you already have more than 2 RBs or WRs, FLEX is NOT needed and is FILLED.
            - IF YOU DON'T HAVE A TIGHT END IN THE LAST ROUND, YOU MUST TAKE A TIGHT END
            - IF YOU DON'T HAVE A QUARTERBACK IN THE LAST ROUND, YOU MUST TAKE A QUARTERBACK
            When you've made your decision, YOU MUST format your output exactly as:

            I select [PLAYER FULL NAME]
            **TERMINATE**

            You should only chose ONE player. If you chose multiple players, your output WILL be ignored.
            Also, if at the end your roster does not meet the format, the team will be ELIMINATED. 
            """,
            llm_config={"cache_seed": None, "config_list": self.config_list},
            description="Picks best overall player to draft based on recommendations.",
        )

        head_drafter_agent.client.cache = None

        # Store all agents
        self.agents = {
            "qb_extractor": qb_extractor,
            "qb_analyzer": qb_analyzer,
            "wr_extractor": wr_extractor,
            "wr_analyzer": wr_analyzer,
            "rb_extractor": rb_extractor,
            "rb_analyzer": rb_analyzer,
            "te_extractor": te_extractor,
            "te_analyzer": te_analyzer,
            "head_drafter": head_drafter_agent,
            "user_proxy": user_proxy,
        }

        # Create the group chat
        groupchat = GroupChat(
            agents=[
                user_proxy,
                qb_extractor,
                qb_analyzer,
                wr_extractor,
                wr_analyzer,
                rb_extractor,
                rb_analyzer,
                te_extractor,
                te_analyzer,
                head_drafter_agent,
            ],
            messages=[],
            max_round=100,
        )

        # Create the manager with stronger guidance
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config={
                "cache_seed": None,
                "config_list": self.config_list,
            },  # Disable caching
            max_consecutive_auto_reply=20,
            system_message="""
            You are a group chat manager for a fantasy football draft conversation. The head_drafter_agent should ALWAYS start the conversation.
            Follow this exact sequence:

            1. The head_drafter_agent first analyzes roster needs
            2. The head_drafter_agent asks a specific position analyzer for a recommendation
            3. The position analyzer requests data from their respective position extractor
            4. The respective position extractor provides data
            5. The position analyzer gives ONE recommendation back to the head_drafter_agent
            6. Steps 2-5 repeat for other NEEDED positions
            7. The head_drafter_agent makes the final selection

            Enforce this exact flow. Do not allow analyzers to respond unless directly asked by the head_drafter_agent.
            Do not allow extractors to get data if analyzers do not ask for data. Do not have the head_drafter_agent do
            reasoning for a specific position itself. The head_drafter_agent should finish the conversation just to make
            the final pick for that round.
            """,
        )

        self.agents["manager"] = manager

    def make_extractor_analyzer_agents(self, position: str):
        """Create extractor and analyzer agents for a specific position"""
        # Standard extractor prompt template for all positions
        extractor_prompt = f"""
        You are a data extractor ONLY for the {position} position. Your job is to provide stats when requested by the {position}_analyzer.
        Do NOT extract data for any other position except {position}.

        WHEN ACTIVATED:
        1. The {position}_analyzer will ask you for data with a list of already drafted players
        2. Use the display_position_rankings_with_filtering() tool with the following parameters:
           - position: (one of QB, RB, WR, TE) for your respective position
           - limit: 10 (to get top 10 players)
           - excluded_players: EXACTLY the list of already drafted players provided by the analyzer

        DO NOT respond to any agent except the {position}_analyzer.
        ONLY use the tool when specifically asked by the {position}_analyzer.
        """

        # Position-specific analyzer prompts with unique evaluation criteria for each position
        analyzer_prompts = {
            "quarterback": """
            You are a fantasy football expert specializing ONLY in the quarterback position.

            YOUR JOB:
            1. When the head_drafter_agent asks you for a recommendation, first ask the quarterback_extractor for data, providing the complete list of already drafted players.
            2. Once you receive data from the extractor, analyze it to determine the best available quarterback.
            3. Make ONE clear recommendation based on:
               - Passing yards, TDs, and interceptions from previous season
               - Supporting cast quality (WR/TE talent)
               - IMPORTANT: Rushing ability (rushing yards and TDs add significant value)
               - Projected pass attempts per game
               - Matchup potential
               - The ranking of the players is important and usually is a good indicator of where they SHOULD be drafted,
                 but just take them as a recommendation

            YOUR RECOMMENDATION FORMAT:
            When making your recommendation to the head_drafter_agent, use exactly this format:

            "QB RECOMMENDATION: [Player Name] - [Key Stats] - [Brief 1-2 sentence explanation]"

            DO NOT recommend any players who have already been drafted.
            ONLY respond when directly asked by the head_drafter_agent.
            The explanation should only include reasoning from statistics you receive from the extractor and pertain to fantasy football.
            """,
            "wide_receiver": """
            You are a fantasy football expert specializing ONLY in the wide receiver position.

            YOUR JOB:
            1. When the head_drafter_agent asks you for a recommendation, first ask the wide_receiver_extractor for data, providing the complete list of already drafted players.
            2. Once you receive data from the extractor, analyze it to determine the best available wide receiver.
            3. Make ONE clear recommendation based on:
               - Target share and target volume
               - Touchdown potential
               - Quarterback quality
               - Offensive quality
               - Matchup potential
               - The ranking of the players is important and usually is a good indicator of where they SHOULD be drafted,
                 but just take them as a recommendation

            YOUR RECOMMENDATION FORMAT:
            When making your recommendation to the head_drafter_agent, use exactly this format:

            "WR RECOMMENDATION: [Player Name] - [Key Stats] - [Brief 1-2 sentence explanation]"

            DO NOT recommend any players who have already been drafted.
            ONLY respond when directly asked by the head_drafter_agent.
            The explanation should only include reasoning from statistics you receive from the extractor and pertain to fantasy football.
            """,
            "running_back": """
            You are a fantasy football expert specializing ONLY in the running back position.

            YOUR JOB:
            1. When the head_drafter_agent asks you for a recommendation, first ask the running_back_extractor for data, providing the complete list of already drafted players.
            2. Once you receive data from the extractor, analyze it to determine the best available running back.
            3. Make ONE clear recommendation based on:
               - Workload (carries and touches per game)
               - Important: Pass-catching ability (receptions have high value)
               - Red zone/goal line usage
               - Offensive quality
               - Matchup potential
               - The ranking of the players is important and usually is a good indicator of where they SHOULD be drafted,
                 but just take them as a recommendation

            YOUR RECOMMENDATION FORMAT:
            When making your recommendation to the head_drafter_agent, use exactly this format:

            "RB RECOMMENDATION: [Player Name] - [Key Stats] - [Brief 1-2 sentence explanation]"

            DO NOT recommend any players who have already been drafted.
            ONLY respond when directly asked by the head_drafter_agent.
            The explanation should only include reasoning from statistics you receive from the extractor and pertain to fantasy football.
            """,
            "tight_end": """
            You are a fantasy football expert specializing ONLY in the tight end position.

            YOUR JOB:
            1. When the head_drafter_agent asks you for a recommendation, first ask the tight_end_extractor for data, providing the complete list of already drafted players.
            2. Once you receive data from the extractor, analyze it to determine the best available tight end.
            3. Make ONE clear recommendation based on:
               - Pass catching stats
               - Matchup potential
               - The ranking of the players is important and usually is a good indicator of where they SHOULD be drafted,
                 but just take them as a recommendation

            YOUR RECOMMENDATION FORMAT:
            When making your recommendation to the head_drafter_agent, use exactly this format:

            "TE RECOMMENDATION: [Player Name] - [Key Stats] - [Brief 1-2 sentence explanation]"

            DO NOT recommend any players who have already been drafted.
            ONLY respond when directly asked by the head_drafter_agent.
            The explanation should only include reasoning from statistics you receive from the extractor and pertain to fantasy football.
            """,
        }

        # Use position-specific analyzer prompt if available, otherwise use a generic one
        analyzer_prompt = analyzer_prompts.get(position)

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
            llm_config={
                "cache_seed": None,
                "config_list": self.config_list,
            },  # Disable caching
            description=f"Analyzes and ranks {position} players only",
        )

        analyzer.client.cache = None  # Disable cache to prevent stale responses

        return extractor, analyzer

    def get_available_players(self, players):
        """Format available players in a structure for the draft agents"""
        # Filter out already drafted players (both by drafted flag and by name in drafted_players list)
        self.available_players = [
            p for p in players if not p.drafted and p.name not in self.drafted_players
        ]
        return self.available_players

    def extract_player_name_from_output(self, output_text):
        """Extract the player name from the chat output"""
        # Look for the specific selection format first

        print(f"OUTPUT TEXT: {output_text}")
        selection_pattern = r"I select ([^\n]+?)(?:\s+\*\*TERMINATE\*\*|\s*$)"
        selection_match = re.search(selection_pattern, output_text, re.IGNORECASE)
        if selection_match:
            potential_name = selection_match.group(1).strip()
            # Check if this matches an available player name
            for player in self.available_players:
                if player.name.lower() in potential_name.lower():
                    return player.name
            # If no exact match but the name doesn't appear in drafted players, return it
            if potential_name not in self.drafted_players:
                return potential_name

        # Fallback: Look for lines immediately before TERMINATE
        last_terminate_pos = output_text.rfind("TERMINATE")
        if last_terminate_pos > 0:
            context_before = output_text[
                max(0, last_terminate_pos - 500) : last_terminate_pos
            ]
            lines = context_before.strip().split("\n")
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if not line or line.startswith("-") or line.startswith("*"):
                    continue
                for player in self.available_players:
                    if player.name in line:
                        return player.name

        # Additional pattern searches if needed
        patterns = [
            r"I (?:choose|select|draft|pick)\s+([^.\n]+)",
            r"select\s+([^.\n]+)",
            r"draft\s+([^.\n]+)",
            r"recommendation:\s+([^-\n]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output_text, re.IGNORECASE)
            if match:
                potential_name = match.group(1).strip()
                # Check if the extracted name is not in the drafted players list
                if potential_name not in self.drafted_players:
                    # Verify it matches an available player
                    for player in self.available_players:
                        if player.name.lower() in potential_name.lower():
                            return player.name
                    return potential_name

        return None

    def make_draft_selection(
        self, available_players, team, draft_position, current_round
    ):
        """Use the multi-agent system to make a draft decision"""
        # Initialize agents if not already done
        if not self.agents:
            self.initialize_agents()

        # Store available players
        self.available_players = [
            p
            for p in available_players
            if not p.drafted and p.name not in self.drafted_players
        ]

        # Format current roster
        current_roster = ""
        if team.roster:
            current_roster = "Your current roster:\n"
            for pos, players in team.roster.items():
                for player in players:
                    current_roster += (
                        f"- {player.name} - {player.position} ({player.team})\n"
                    )
        else:
            current_roster = "Your roster is currently empty."

        # Add drafted players info
        drafted_info = "Already drafted players (DO NOT SELECT THESE):\n"
        if self.drafted_players:
            for name in self.drafted_players:
                drafted_info += f"- {name}\n"
        else:
            drafted_info += "No players have been drafted yet."

        # Build the structured message
        message = (
            f"DRAFT ROUND {current_round}, PICK {draft_position}\n\n"
            f"{current_roster}\n\n"
            f"{drafted_info}\n\n"
            f"You are making a selection for the {self.team_name}. "
            f"Remember that a complete roster requires: 1 QB, 2 RB, 2 WR, 1 TE, and 1 FLEX (RB/WR)."
        )

        # Get the user proxy and manager
        user_proxy = self.agents["user_proxy"]
        manager = self.agents["manager"]

        print("Starting the multi-agent draft conversation...")

        # Reset message history for all agents before starting a new draft selection
        for agent_name, agent in self.agents.items():
            agent.clear_history()
            print(
                f"""{agent_name} message history cleared.

                Messages now: {agent.chat_messages}"""
            )

        # Run the chat with a retry mechanism
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                user_proxy.initiate_chat(
                    manager,
                    message=message,
                    max_turns=20,  # Limit conversation length to avoid errors
                )
                break  # Exit the loop if successful
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {str(e)}")
                if attempt == max_attempts - 1:  # Last attempt
                    print("All attempts failed. Using fallback selection method.")
                    # Don't re-raise, continue to fallback selection
                else:
                    # Reset message history for all agents before retrying
                    for agent_name, agent in self.agents.items():
                        agent.clear_history()
                        # print(
                        #     f"""{agent_name} message history cleared.

                        #     Messages now: {agent.chat_messages}"""
                        # )

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

            # Fallback: pick highest rated player at position of need
            needed_positions = []
            if not any(p for p in team.roster.get("QB", []) if p is not None):
                needed_positions.append("QB")
            if len(team.roster.get("RB", [])) < 2:
                needed_positions.append("RB")
            if len(team.roster.get("WR", [])) < 2:
                needed_positions.append("WR")
            if not any(p for p in team.roster.get("TE", []) if p is not None):
                needed_positions.append("TE")

            # Prioritize RB/WR in early rounds
            if current_round <= 3 and (
                "RB" in needed_positions or "WR" in needed_positions
            ):
                priority_positions = [
                    pos for pos in ["RB", "WR"] if pos in needed_positions
                ]
                # Filter available players by priority positions
                position_players = [
                    p
                    for p in self.available_players
                    if p.position in priority_positions
                ]
            else:
                # Use all needed positions
                position_players = [
                    p for p in self.available_players if p.position in needed_positions
                ]

            # If no position players found or no needs identified, take best available player
            if not position_players:
                position_players = self.available_players

            # Sort by overall rank and select the best player
            for player in sorted(
                position_players, key=lambda p: getattr(p, "rating", 999), reverse=True
            ):
                player_name = player.name
                print(f"Fallback selection: {player_name}")
                break

        return player_name
