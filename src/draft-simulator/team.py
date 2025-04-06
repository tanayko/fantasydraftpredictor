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
        
    def display_roster(self):
        print(f"\n{'-' * 50}")
        print(f"{self.name} Current Roster:")
        print(f"{'-' * 50}")
        
        if not any(self.roster.values()):
            print("No players drafted yet.")
            return
            
        for position, players in sorted(self.roster.items()):
            if players:
                print(f"\n{position}:")
                for idx, player in enumerate(players, 1):
                    print(f"  {idx}. {player.name} ({player.college}) - Rating: {player.rating}")
        print(f"{'-' * 50}\n")
