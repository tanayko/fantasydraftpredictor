from autogen import ConversableAgent
from collections import defaultdict
import os

OPENAI_API_KEY = os.getenv("API_KEY")

class AutoGenDrafter:
    """A simple AutoGen-powered NFL drafter"""

    def __init__(self, team_name="AutoGen GM"):
        self.team_name = team_name
        self.agent = self._create_drafter_agent()

    def _create_drafter_agent(self):
        """Create the AutoGen agent for drafting"""

        # Define the system prompt for the drafter
        system_prompt = """
        You are an expert NFL Draft analyst and General Manager. Your task is to analyze available players
        and make draft selections that best fit the team's needs.
        
        When making a draft selection, follow these guidelines:
        - Prioritize drafting players at positions not currently on the team's roster
        - Choose the highest-rated player at positions of need. If multiple positions are available, select the one with the highest rating.
        - If all positions have at least one player, select the best overall player available
        - Reply with ONLY the full name of the selected player, nothing else
        """
        print(f"Creating agent for team: {self.team_name}")
        # Create the agent without tools
        agent = ConversableAgent(
            name=self.team_name,
            system_message=system_prompt,
            llm_config={
                "config_list": [
                    {
                        # use gpt-3.5-turbo-1106 or gpt-4o-mini for POC
                        # # change to gpt-4 for production
                        "model": "gpt-4o-mini",
                        "api_key": OPENAI_API_KEY,
                        "base_url": "https://api.openai.com/v1",
                    }
                ],
                "temperature": 0,
            },
        )

        return agent

    def get_available_players(self, players, position_filter=None):
        """
        Format available players in a way the agent can understand.
        Returns a structured representation of available players.
        """
        available = [p for p in players if not p.drafted]

        if position_filter:
            available = [p for p in available if p.position == position_filter]

        # Group players by position without sorting by rating
        by_position = defaultdict(list)
        for player in available:
            by_position[player.position].append(
                {
                    "name": player.name,
                    "position": player.position,
                    "college": player.college,
                    "rating": player.rating,
                }
            )

        # Convert defaultdict to regular dict for easier handling
        return dict(by_position)

    def make_draft_selection(
        self, available_players, team, draft_position, current_round
    ):
        """
        Use the AutoGen agent to make a draft decision.
        """
        # Format draft prompt
        prompt = self._format_draft_prompt(
            available_players, team, draft_position, current_round
        )

        # Call the agent with the prompt
        response = self.agent.generate_reply(
            messages=[{"role": "user", "content": prompt}]
        )

        print(f"Agent response: {response}")

        # Extract player name from response
        player_name = self._extract_player_from_response(response)

        if not player_name:
            # Fallback if agent fails
            return self._fallback_selection(available_players, team)

        return player_name

    def _format_draft_prompt(
        self, available_players, team, draft_position, current_round
    ):
        """Format a prompt for the AutoGen agent to make a draft decision"""
        prompt = (
            f"You are the General Manager for the {team.name} NFL team. "
            f"You are making a selection in Round {current_round}, Pick {draft_position}.\n\n"
        )

        # Add roster information
        prompt += "Your current roster by position:\n"
        if any(team.roster.values()):
            for position, players in team.roster.items():
                if players:
                    prompt += f"{position}: {', '.join([p.name for p in players])}\n"
        else:
            prompt += "Your roster is currently empty.\n"

        # Add available players
        prompt += "\nAvailable players by position:\n"
        for position, players in available_players.items():
            if players:
                prompt += f"\n{position}:\n"
                for player in players:
                    prompt += f"- {player['name']} ({player['college']}) - Rating: {player['rating']}\n"

        # Add the specific instruction
        prompt += "\nYour task: Choose the highest-rated player at a position that isn't currently on your team. "
        prompt += "If multiple positions are available, select the one with the highest rating.\n"
        prompt += (
            "If all positions are covered, select the best player available overall.\n"
        )
        prompt += (
            "Reply with ONLY the full name of the player you select, nothing else."
        )

        print(f"Draft prompt for agent:\n{prompt}")

        return prompt

    def _extract_player_from_response(self, response):
        """Extract player name from agent response"""
        # The agent should return just the player name, but clean it up to be sure
        player_name = response.strip()

        # Remove any potential explanations the agent might add
        if "\n" in player_name:
            player_name = player_name.split("\n")[0]

        # Remove any punctuation
        for char in [".", ",", ":", ";"]:
            if player_name.endswith(char):
                player_name = player_name[:-1]

        return player_name.strip()

    def _fallback_selection(self, available_players, team):
        """Fallback logic if agent fails to make a valid selection"""
        # Get positions that already have players in the roster
        roster_positions = set(team.roster.keys())

        # Find positions that aren't in the team yet
        missing_positions = [
            pos
            for pos in available_players.keys()
            if pos not in roster_positions and available_players[pos]
        ]

        # If there are positions not in roster, pick the highest-rated player from those
        if missing_positions:
            # Take the first missing position and its highest-rated player
            position = missing_positions[0]
            players = available_players[position]
            highest_rated = max(players, key=lambda p: p["rating"])
            return highest_rated["name"]

        # If all positions have at least one player, pick the highest-rated player overall
        best_player = None
        best_rating = -1

        for position in available_players:
            for player in available_players[position]:
                if player["rating"] > best_rating:
                    best_rating = player["rating"]
                    best_player = player

        return best_player["name"] if best_player else None
