import time
from collections import defaultdict
from team import Team
from drafter_agent import AutoGenDrafter
from typing import Optional
from player import Player


# DraftSimulator
# This class will now include the LLM drafter functionality
class DraftSimulator:
    def __init__(self):
        self.teams = []
        self.players = []
        self.current_round = 1
        self.max_rounds = 7
        self.llm_drafter = None

    # [Keep all your existing methods]
    def load_sample_players(self):
        """Load a sample list of players for testing"""
        sample_players = [
            Player("Trevor Lawrence", "QB", "Clemson", 9.5),
            Player("Justin Fields", "QB", "Ohio State", 9.2),
            Player("Zach Wilson", "QB", "BYU", 8.9),
            Player("Trey Lance", "QB", "North Dakota State", 8.7),
            Player("Mac Jones", "QB", "Alabama", 8.5),
            Player("Ja'Marr Chase", "WR", "LSU", 9.4),
            Player("DeVonta Smith", "WR", "Alabama", 9.3),
            Player("Jaylen Waddle", "WR", "Alabama", 9.1),
            Player("Kyle Pitts", "TE", "Florida", 9.6),
            Player("Pat Freiermuth", "TE", "Penn State", 8.9),
            Player("Penei Sewell", "OT", "Oregon", 9.5),
            Player("Rashawn Slater", "OT", "Northwestern", 9.2),
            Player("Christian Darrisaw", "OT", "Virginia Tech", 8.8),
            Player("Najee Harris", "RB", "Alabama", 8.9),
            Player("Travis Etienne", "RB", "Clemson", 8.7),
            Player("Javonte Williams", "RB", "North Carolina", 8.5),
            Player("Micah Parsons", "LB", "Penn State", 9.3),
            Player("Jeremiah Owusu-Koramoah", "LB", "Notre Dame", 9.0),
            Player("Patrick Surtain II", "CB", "Alabama", 9.4),
            Player("Jaycee Horn", "CB", "South Carolina", 9.2),
            Player("Caleb Farley", "CB", "Virginia Tech", 9.0),
            Player("Jaelan Phillips", "EDGE", "Miami", 9.1),
            Player("Kwity Paye", "EDGE", "Michigan", 9.0),
            Player("Christian Barmore", "DT", "Alabama", 8.9),
            Player("Gregory Rousseau", "EDGE", "Miami", 8.8),
            Player("Trevon Moehrig", "S", "TCU", 8.8),
            Player("Zaven Collins", "LB", "Tulsa", 8.7),
            Player("Alijah Vera-Tucker", "OG", "USC", 8.9),
            Player("Jamin Davis", "LB", "Kentucky", 8.6),
            Player("Rashod Bateman", "WR", "Minnesota", 8.7),
            Player("Kadarius Toney", "WR", "Florida", 8.6),
        ]
        self.players = sample_players

    def register_team(self, team_name: str):
        """Register a new team for the draft"""
        team = Team(team_name)
        self.teams.append(team)
        return team

    def display_available_players(self, position_filter: Optional[str] = None):
        """Display available players, optionally filtered by position"""
        available = [p for p in self.players if not p.drafted]

        if position_filter:
            available = [p for p in available if p.position == position_filter]

        if not available:
            message = "No players available"
            if position_filter:
                message += f" at position {position_filter}"
            print(message)
            return

        print(f"\n{'-' * 60}")
        print(
            f"Available Players" + (f" ({position_filter})" if position_filter else "")
        )
        print(f"{'-' * 60}")

        # Group by position
        by_position = defaultdict(list)
        for player in available:
            by_position[player.position].append(player)

        # Display players by position
        for position in sorted(by_position.keys()):
            print(f"\n{position}:")
            for idx, player in enumerate(
                sorted(by_position[position], key=lambda p: p.rating, reverse=True), 1
            ):
                print(
                    f"  {idx}. {player.name} ({player.college}) - Rating: {player.rating}"
                )

        print(f"{'-' * 60}\n")

    def find_player_by_name(self, name: str):
        """Find a player by name (case-insensitive, partial match)"""
        name = name.lower()
        matches = [p for p in self.players if name in p.name.lower() and not p.drafted]

        if not matches:
            print(f"No available player found matching '{name}'")
            return None

        if len(matches) == 1:
            return matches[0]

        # Multiple matches, ask for clarification
        print("\nMultiple players found:")
        for idx, player in enumerate(matches, 1):
            print(f"{idx}. {player}")

        while True:
            try:
                choice = int(input("\nSelect player number: "))
                if 1 <= choice <= len(matches):
                    return matches[choice - 1]
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a number.")

    # Add this new method:

    def add_llm_team(self, team_name="AI_General_Manager"):
        """Add an LLM-powered team to the draft"""
        team = Team(team_name)
        self.teams.append(team)
        self.llm_drafter = AutoGenDrafter(team_name)
        return team

    def display_draft_results(self):
        """Display draft results for all teams"""
        print("\n" + "=" * 70)
        print("DRAFT RESULTS")
        print("=" * 70)

        for team in self.teams:
            team.display_roster()
            print("\n")

    # Modify your run_draft method to handle the LLM team
    def run_draft(self):
        """Run the draft simulation with support for an LLM-powered team"""
        if not self.teams:
            print("No teams registered. Please register teams first.")
            return

        if not self.players:
            print("No players available. Please add players first.")
            return

        print("\n" + "=" * 70)
        print(
            f"NFL DRAFT SIMULATOR - {len(self.teams)} Teams, {self.max_rounds} Rounds"
        )
        print("=" * 70)

        for round_num in range(1, self.max_rounds + 1):
            print(f"\n\nROUND {round_num}")
            print("-" * 30)

            for pick_num, team in enumerate(self.teams, 1):
                overall_pick = (round_num - 1) * len(self.teams) + pick_num

                # Check if this is the LLM-powered team
                is_llm_team = (
                    self.llm_drafter and team.name == self.llm_drafter.team_name
                )

                if is_llm_team:
                    # LLM team's turn
                    print(
                        f"\nRound {round_num}, Pick {pick_num} (Overall: {overall_pick})"
                    )
                    print(f"AI Team on the clock: {team.name}")

                    # Get available players for the LLM
                    available_players = self.llm_drafter.get_available_players(
                        self.players
                    )

                    # Let the LLM make a decision
                    print("\nAI is analyzing available players and team needs...")
                    time.sleep(2)  # Simulate thinking time

                    ## can have the make draft selection give
                    ## the SMEs players for each position
                    player_name = self.llm_drafter.make_draft_selection(
                        available_players, team, pick_num, round_num
                    )

                    if player_name:
                        player = self.find_player_by_name(player_name)
                        if player:
                            team.add_player(player)
                            print(
                                f"\n{team.name} selects {player.name}, {player.position} from {player.college}"
                            )
                            time.sleep(2)
                        else:
                            print(
                                f"Error: AI selected {player_name} but player not found in database."
                            )
                    else:
                        print("Error: AI could not make a selection.")

                else:
                    # Human team's turn - use your existing UI
                    while True:
                        print(
                            f"\nRound {round_num}, Pick {pick_num} (Overall: {overall_pick})"
                        )
                        print(f"Team on the clock: {team.name}")

                        # Display commands
                        print("\nCommands:")
                        print("1. View available players (all)")
                        print("2. View available players by position")
                        print("3. View current team roster")
                        print("4. Draft a player")
                        print("5. View all team rosters")

                        command = input("\nEnter command (1-5): ")

                        if command == "1":
                            self.display_available_players()
                        elif command == "2":
                            pos = input(
                                "Enter position (QB, RB, WR, TE, OT, OG, C, DT, EDGE, LB, CB, S): "
                            ).upper()
                            self.display_available_players(pos)
                        elif command == "3":
                            team.display_roster()
                        elif command == "4":
                            # Draft a player
                            while True:  # Keep asking until a valid player is selected
                                player_name = input("\nEnter player name to draft: ")

                                # Allow canceling the draft
                                if player_name.lower() in ["cancel", "back", "return"]:
                                    print("Draft selection canceled.")
                                    break

                                player = self.find_player_by_name(player_name)

                                if player:
                                    team.add_player(player)
                                    print(
                                        f"\n{team.name} selects {player.name}, {player.position} from {player.college}"
                                    )
                                    time.sleep(2)
                                    break  # Successfully drafted a player

                                # If we get here, no player was found
                                retry = input("Player not found. Try again? (y/n): ")
                                if retry.lower() != "y":
                                    break  # Exit without drafting

                            break  # Move to next team
                        elif command == "5":
                            # Display all team rosters
                            for t in self.teams:
                                t.display_roster()
                        else:
                            print("Invalid command. Please try again.")

            # Check if all players are drafted
            if all(p.drafted for p in self.players):
                print("\nAll players have been drafted!")
                break

        # Draft complete, show results
        self.display_draft_results()


# Example usage
def main():
    # Initialize the enhanced draft simulator
    draft = DraftSimulator()

    # Load sample players
    draft.load_sample_players()

    # Register teams
    print("NFL DRAFT SIMULATOR WITH AI GM")
    print("=" * 30)

    # Let user decide how many human teams (1-4)
    num_human_teams = int(input("Enter number of human-controlled teams (1-4): "))

    # Register human teams
    for i in range(num_human_teams):
        team_name = input(f"Enter name for Team {i+1}: ")
        draft.register_team(team_name)

    # Add the AI team
    draft.add_llm_team("AI_General_Manager")

    # Set rounds
    draft.max_rounds = int(input("Enter number of rounds: "))

    # Run the draft
    draft.run_draft()


if __name__ == "__main__":
    main()
