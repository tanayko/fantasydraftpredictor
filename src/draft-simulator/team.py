from collections import defaultdict
from typing import List, Dict
from player import Player


class Team:
    def __init__(self, name: str):
        self.name = name
        self.roster: Dict[str, List[Player]] = defaultdict(list)

    def add_player(self, player: Player):
        player.drafted = True
        player.drafted_by = self.name
        self.roster[player.position].append(player)

    def display_roster(self, log_file_path):
        roster_output = f"\n{'-' * 50}\n"
        roster_output += f"{self.name} Current Roster:\n"
        roster_output += f"{'-' * 50}\n"

        if not any(self.roster.values()):
            roster_output += "No players drafted yet.\n"
        else:
            for position, players in sorted(self.roster.items()):
                if players:
                    roster_output += f"\n{position}:\n"
                    for idx, player in enumerate(players, 1):
                        roster_output += f"  {idx}. {player.name} ({player.team})\n"
        roster_output += f"{'-' * 50}\n"
        print(roster_output)

        # Append roster_output to the log file path
        with open(log_file_path, "a") as file:
            file.write(roster_output)
