import csv
import time
import random
from team import Team
from drafter_multi_agent import AutoGenDrafter
from typing import Optional, List
from player import Player


# DraftSimulator
# This class will now include the LLM drafter functionality with drafted player tracking
class DraftSimulator:
    def __init__(self):
        self.teams = []
        self.draft_order = []  # Store draft order separately
        self.players = []
        self.current_round = 1
        self.max_rounds = 9
        self.llm_drafter = None
        self.drafted_players = []  # Track names of drafted players

    # [Keep all your existing methods]
    def load_players_from_csv(self, csv_filename):
        """Load players directly from a CSV file"""
        self.players = []

        try:
            with open(csv_filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Extract the required fields
                    name = row.get('Name', '')
                    team = row.get('Team', '')
                    position = row.get('Pos', '')

                    # Skip row if any required field is missing
                    if not name or not team or not position:
                        continue

                    # Create a Player object
                    player = Player(name, position, team)
                    self.players.append(player)

            print(f"Loaded {len(self.players)} players from {csv_filename}")
        except Exception as e:
            print(f"Error loading players from CSV: {e}")
            raise

        return self.players

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

        # Simply display players in the order they appear in the CSV
        for idx, player in enumerate(available, 1):
            print(f"  {idx}. {player.name} ({player.position}, {player.team})")

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

    def add_llm_team(self, team_name="AI_General_Manager"):
        """Add an LLM-powered team to the draft"""
        team = Team(team_name)
        self.teams.append(team)
        self.llm_drafter = AutoGenDrafter(team_name)
        return team

    def set_random_draft_order(self):
        """Randomize the draft order of teams"""
        # Create a copy of the teams list
        teams_copy = self.teams.copy()
        # Shuffle the teams randomly
        random.shuffle(teams_copy)
        # Store the randomized order
        self.draft_order = teams_copy

        # Print the draft order
        print("\nDRAFT ORDER")
        print("-" * 20)
        for i, team in enumerate(self.draft_order, 1):
            print(f"{i}. {team.name}")
        print()

    def get_round_draft_order(self, round_num):
        """
        Get the draft order for a specific round (implements snake draft)

        Args:
            round_num: The round number (1-based)

        Returns:
            List of teams in the order they draft for this round
        """
        # Even rounds go in reverse order
        if round_num % 2 == 0:
            return list(reversed(self.draft_order))
        # Odd rounds go in normal order
        else:
            return self.draft_order

    def display_draft_results(self):
        """Display draft results for all teams"""
        print("\n" + "=" * 70)
        print("DRAFT RESULTS")
        print("=" * 70)

        for team in self.teams:
            team.display_roster()
            print("\n")

    def get_drafted_player_names(self) -> List[str]:
        """Get a list of all drafted player names"""
        return self.drafted_players

    def mark_player_as_drafted(self, player: Player):
        """Mark a player as drafted and add to the drafted list"""
        if player and not player.drafted:
            player.drafted = True
            self.drafted_players.append(player.name)

    # Modify your run_draft method to handle drafted player tracking
    def run_draft(self):
        """Run the draft simulation with support for an LLM-powered team"""
        if not self.teams:
            print("No teams registered. Please register teams first.")
            return

        if not self.players:
            print("No players available. Please add players first.")
            return

        # Set random draft order if not already set
        if not self.draft_order:
            self.set_random_draft_order()

        print("\n" + "=" * 70)
        print(
            f"NFL DRAFT SIMULATOR - {len(self.teams)} Teams, {self.max_rounds} Rounds (Snake Draft)"
        )
        print("=" * 70)

        pick_counter = 0  # Track overall pick number

        for round_num in range(1, self.max_rounds + 1):
            print(f"\n\nROUND {round_num}")
            print("-" * 30)

            # Get the draft order for this round (snake draft)
            round_draft_order = self.get_round_draft_order(round_num)

            # Display round draft order
            order_direction = "←" if round_num % 2 == 0 else "→"
            print(f"Draft Direction: {order_direction} ({['Normal', 'Reversed'][round_num % 2 == 0]} order)")

            for pick_num, team in enumerate(round_draft_order, 1):
                pick_counter += 1  # Increment the overall pick counter

                # Check if this is the LLM-powered team
                is_llm_team = (
                        self.llm_drafter and team.name == self.llm_drafter.team_name
                )

                if is_llm_team:
                    # LLM team's turn
                    print(
                        f"\nRound {round_num}, Pick {pick_num} (Overall: {pick_counter})"
                    )
                    print(f"AI Team on the clock: {team.name}")

                    # Get available players for the LLM
                    available_players = [p for p in self.players if not p.drafted]

                    # Update the LLM drafter with the list of drafted players
                    self.llm_drafter.set_drafted_players(self.drafted_players)

                    # Pass available players to the LLM
                    available_players = self.llm_drafter.get_available_players(available_players)

                    # Let the LLM make a decision
                    print("\nAI is analyzing available players and team needs...")
                    time.sleep(2)  # Simulate thinking time

                    player_name = self.llm_drafter.make_draft_selection(
                        available_players, team, pick_num, round_num
                    )

                    if player_name:
                        player = self.find_player_by_name(player_name)
                        if player:
                            # Add player to team
                            team.add_player(player)

                            # Mark as drafted
                            player.drafted = True
                            player.drafted_by = team.name

                            # Add to drafted list
                            self.drafted_players.append(player.name)

                            print(
                                f"\n{team.name} selects {player.name}, {player.position} from {player.team}"
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
                            f"\nRound {round_num}, Pick {pick_num} (Overall: {pick_counter})"
                        )
                        print(f"Team on the clock: {team.name}")

                        # Display commands
                        print("\nCommands:")
                        print("1. View available players (all)")
                        print("2. View available players by position")
                        print("3. View current team roster")
                        print("4. Draft a player")
                        print("5. View all team rosters")
                        print("6. View drafted players")
                        print("7. View draft order")

                        command = input("\nEnter command (1-7): ")

                        if command == "1":
                            self.display_available_players()
                        elif command == "2":
                            pos = input(
                                "Enter position (QB, RB, WR, TE, K, DST): "
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
                                    # Add player to team
                                    team.add_player(player)

                                    # Mark as drafted
                                    player.drafted = True
                                    player.drafted_by = team.name

                                    # Add to drafted list
                                    self.drafted_players.append(player.name)

                                    print(
                                        f"\n{team.name} selects {player.name}, {player.position} from {player.team}"
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
                        elif command == "6":
                            # Display drafted players
                            print("\nDrafted players so far:")
                            if self.drafted_players:
                                for idx, name in enumerate(self.drafted_players, 1):
                                    print(f"  {idx}. {name}")
                            else:
                                print("  No players drafted yet.")
                        elif command == "7":
                            # Display draft order with arrow showing direction
                            print("\nOriginal Draft Order:")
                            for i, t in enumerate(self.draft_order, 1):
                                print(f"  {i}. {t.name}")

                            print(
                                f"\nCurrent Round ({round_num}) Order ({['Normal', 'Reversed'][round_num % 2 == 0]}):")
                            for i, t in enumerate(round_draft_order, 1):
                                print(f"  {i}. {t.name}")
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
    draft.load_players_from_csv("tools/data/official_2024_fantasy_rankings/ESPN_Standard.csv")

    # Register teams
    print("NFL DRAFT SIMULATOR WITH AI GM")
    print("=" * 30)

    # Let user decide how many human teams (1-4)
    num_human_teams = int(input("Enter number of human-controlled teams (1-4): "))

    # Register human teams
    for i in range(num_human_teams):
        team_name = input(f"Enter name for Team {i + 1}: ")
        draft.register_team(team_name)

    # Add the AI team
    draft.add_llm_team("AI_General_Manager")

    # Set rounds
    draft.max_rounds = int(input("Enter number of rounds: "))

    # Randomize draft order
    draft.set_random_draft_order()

    # Run the draft
    draft.run_draft()


if __name__ == "__main__":
    main()