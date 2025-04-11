import csv
import json
import re
import time
import random
from team import Team
from drafter_multi_agent import AutoGenDrafter
from typing import Optional, List
from player import Player


# DraftSimulator
# This class now includes automated team drafting functionality
class DraftSimulator:
    def __init__(self):
        self.teams = []
        self.draft_order = []  # Store draft order separately
        self.players = []
        self.current_round = 1
        self.max_rounds = 9
        self.llm_drafter = None
        self.drafted_players = []  # Track names of drafted players
        self.auto_teams = []  # Track automated teams

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

    def register_auto_team(self, team_name: str):
        """Register an automated team for the draft"""
        team = Team(team_name)
        self.teams.append(team)
        self.auto_teams.append(team)
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

    def find_best_player_by_position(self, position: str):
        """Find the best available player by position (first in the list)"""
        available = [p for p in self.players if not p.drafted and p.position == position]

        if available:
            return available[0]  # Return the first available player (highest ranked)
        return None

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

    def get_team_positions(self, team: Team):
        """
        Safely get the count of positions in a team's roster
        """
        # Initialize counts for all positions
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'K': 0, 'DST': 0}

        # Find the drafted players for this team
        team_players = []
        for player in self.players:
            if hasattr(player, 'drafted') and player.drafted and hasattr(player, 'drafted_by'):
                if player.drafted_by == team.name:
                    team_players.append(player)

        # Count by position
        for player in team_players:
            if player.position in position_counts:
                position_counts[player.position] += 1

        return position_counts

    def make_auto_team_selection(self, team: Team, pick_num: int, round_num: int):
        """
        Make an automated player selection for a team using best player available strategy,
        while ensuring the roster requirements (1 QB, 2 RB, 2 WR, 1 TE, 1 K) are eventually met
        """
        # Get all available players (already ordered by their ranking in the CSV)
        available_players = [p for p in self.players if not p.drafted]
        if not available_players:
            return None

        # Get position counts from players already drafted by this team
        roster_count = self.get_team_positions(team)

        # Define target roster composition
        target_composition = {
            'QB': 1,
            'RB': 2,
            'WR': 2,
            'TE': 1,
        }

        # Calculate how many picks are left for this team
        team_players_count = sum(roster_count.values())
        remaining_picks = self.max_rounds - team_players_count

        # Check if we've already reached the limit for any position
        position_at_limit = {}
        for pos, target in target_composition.items():
            position_at_limit[pos] = roster_count.get(pos, 0) >= target

        # Filter out positions that have already reached their roster limits
        valid_players = [p for p in available_players if not position_at_limit.get(p.position, False)]

        # If there are valid players that don't exceed position limits, pick the best one
        if valid_players:
            return valid_players[0]  # First player is highest ranked

        # If all positions are at their limits but we still have picks left
        # Just take best available regardless of position limits
        if available_players:
            return available_players[0]

        return None

    def run_draft(self):
        """Run the draft simulation with support for automated teams and an LLM-powered team"""
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

                # Check if this is an automated team
                is_auto_team = team in self.auto_teams

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

                elif is_auto_team:
                    # Automated team's turn
                    print(
                        f"\nRound {round_num}, Pick {pick_num} (Overall: {pick_counter})"
                    )
                    print(f"Auto Team on the clock: {team.name}")

                    # Simulate thinking time
                    print("\nAuto team is making a selection...")
                    time.sleep(1)

                    # Make the automated selection
                    player = self.make_auto_team_selection(team, pick_num, round_num)

                    if player:
                        # Add player to team (make sure we're adding the Player object)
                        team.add_player(player)

                        # Mark as drafted
                        player.drafted = True
                        player.drafted_by = team.name

                        # Add to drafted list (just the name)
                        self.drafted_players.append(player.name)

                        print(
                            f"\n{team.name} selects {player.name}, {player.position} from {player.team}"
                        )
                        time.sleep(1)
                    else:
                        print(f"Error: Auto team {team.name} could not make a selection.")
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


    def normalize_player_name(self, name: str) -> str:
        """Normalize player name by removing suffixes like Jr., Sr., III, etc."""
        return re.sub(r'\s+(Jr\.|Sr\.|III|IV|II)\.?$', '', name).strip()

    def analyze_fantasy_performance(self, fantasy_points_csv: str, output_file: str = None):
        """
        Analyze the fantasy performance of all teams based on a CSV file with fantasy points.
        Returns basic ranking data and optionally saves to a JSON file.

        Args:
            fantasy_points_csv: Path to CSV file with fantasy points data
            output_file: Optional path to save results as JSON

        Returns:
            List of dictionaries with team rankings
        """
        if not self.teams:
            print("No teams available for analysis. Please run the draft first.")
            return []

        print("\nAnalyzing fantasy performance...")

        # Load fantasy points data
        fantasy_points_data = {}

        try:
            with open(fantasy_points_csv, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Extract player info
                    player_name = row.get('Player', '')
                    position = row.get('Pos', '')

                    # Extract total points - in the CSV it appears to be under the 'TTL' column
                    total_points = row.get('TTL', '0')

                    # Skip row if any required field is missing
                    if not player_name or not position or not total_points:
                        continue

                    # Convert points to float
                    try:
                        points = float(total_points)
                    except (ValueError, TypeError):
                        points = 0

                    # Create a normalized key for the player (name + position)
                    normalized_name = self.normalize_player_name(player_name)
                    key = (normalized_name.lower(), position)

                    # Store player data
                    fantasy_points_data[key] = {
                        'name': player_name,
                        'position': position,
                        'points': points
                    }

            print(f"Loaded fantasy points for {len(fantasy_points_data)} players")
        except Exception as e:
            print(f"Error loading fantasy points data: {e}")
            return []

        # Calculate points for each team
        team_results = []

        # Track players not found for reporting
        players_not_found = []

        for team in self.teams:
            total_points = 0
            player_points = []
            team_players_not_found = []

            # Access team.roster with proper structure - it's a dict with position keys and lists of players
            if hasattr(team, 'roster'):
                # Iterate through each position group in the roster
                for position, position_players in team.roster.items():
                    # Iterate through each player in this position group
                    for player in position_players:
                        if hasattr(player, 'name'):
                            player_name = player.name
                            player_position = player.position if hasattr(player, 'position') else position

                            # Normalize player name
                            normalized_name = self.normalize_player_name(player_name).lower()

                            # Try exact position match first
                            key = (normalized_name, player_position)
                            player_data = fantasy_points_data.get(key)

                            # If not found, try other positions
                            if not player_data:
                                for k, v in fantasy_points_data.items():
                                    if k[0] == normalized_name:
                                        player_data = v
                                        break

                            points = 0
                            if player_data:
                                points = player_data['points']
                                total_points += points
                            else:
                                team_players_not_found.append(player_name)

                            # Store individual player points for reference
                            player_points.append({
                                'name': player_name,
                                'position': player_position,
                                'points': points
                            })

            if team_players_not_found:
                players_not_found.append({
                    'team': team.name,
                    'players': team_players_not_found
                })

            # Add team result
            team_results.append({
                'team_name': team.name,
                'total_points': total_points,
                'players': sorted(player_points, key=lambda x: x['points'], reverse=True)  # Sort players by points
            })

        # Sort teams by total points
        ranked_teams = sorted(team_results, key=lambda x: x['total_points'], reverse=True)

        # Add rank to each team
        for i, team in enumerate(ranked_teams, 1):
            team['rank'] = i

        # Create simplified results for output
        simplified_results = []
        for team in ranked_teams:
            # Find the top player
            top_player = {'name': 'None', 'points': 0}
            if team['players']:
                top_player = max(team['players'], key=lambda x: x.get('points', 0))

            simplified_results.append({
                'rank': team['rank'],
                'team_name': team['team_name'],
                'total_points': team['total_points'],
                'top_player': top_player['name'],
                'top_player_points': top_player['points']
            })

        # Display results
        print("\nTEAM RANKINGS BY FANTASY POINTS:")
        print("-" * 70)
        print(f"{'Rank':<5} {'Team':<25} {'Points':<10} {'Top Player':<25} {'Player Pts':<10}")
        print("-" * 70)

        for team in simplified_results:
            print(
                f"{team['rank']:<5} {team['team_name'][:25]:<25} {team['total_points']:.1f} {team['top_player'][:25]:<25} {team['top_player_points']:.1f}")

        # Report on players not found
        if players_not_found:
            print("\nWARNING: Some players were not found in the fantasy points data:")
            for team_data in players_not_found:
                print(f"  {team_data['team']}: {', '.join(team_data['players'])}")

        # Save to JSON file if requested
        if output_file:
            try:
                # Check if output file ends with .py
                if output_file.endswith('.py'):
                    # Create a Python file with the data
                    with open(output_file, 'w') as f:
                        f.write("# Fantasy Football Team Rankings\n\n")
                        f.write("rankings = [\n")
                        for team in simplified_results:
                            f.write(f"    {{\n")
                            f.write(f"        'rank': {team['rank']},\n")
                            f.write(f"        'team_name': '{team['team_name']}',\n")
                            f.write(f"        'total_points': {team['total_points']},\n")
                            f.write(f"        'top_player': '{team['top_player']}',\n")
                            f.write(f"        'top_player_points': {team['top_player_points']}\n")
                            f.write(f"    }},\n")
                        f.write("]\n")
                else:
                    # Create a JSON file
                    with open(output_file, 'w') as f:
                        json.dump(simplified_results, f, indent=2)
                    print(f"\nResults saved to {output_file}")
            except Exception as e:
                print(f"Error saving results: {e}")

        return simplified_results

# Example usage
def main():
    # Initialize the enhanced draft simulator
    draft = DraftSimulator()

    # Load sample players
    draft.load_players_from_csv("tools/data/official_2024_fantasy_rankings/ESPN_Standard.csv")

    # Register teams
    print("FANTASY DRAFT SIMULATOR WITH AUTO TEAMS AND AI GM")
    print("=" * 40)

    # Ask for number of auto teams (minimum 11)
    num_auto_teams = max(11, int(input("Enter number of auto-generated teams (minimum 11): ")))

    # Create auto teams
    for i in range(num_auto_teams):
        team_name = f"Auto Team {i + 1}"
        draft.register_auto_team(team_name)

    # Add the AI team
    draft.add_llm_team("AI_General_Manager")

    # Set rounds (we need to have enough rounds to fulfill roster requirements)
    num_rounds = max(7, int(input("Enter number of rounds (minimum 7): ")))
    draft.max_rounds = num_rounds

    # Randomize draft order
    draft.set_random_draft_order()

    # Run the draft
    draft.run_draft()

    # Then analyze performance using your fantasy points CSV
    draft.analyze_fantasy_performance('tools/data/FantasyPros_Fantasy_Football_Points_PPR.csv', 'fantasy_rankings.json')


if __name__ == "__main__":
    main()