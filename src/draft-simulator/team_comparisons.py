import csv

espn_players = [
    "Christian McCaffrey",
    "Bijan Robinson",
    "CeeDee Lamb",
    "Tyreek Hill",
    "Josh Allen",
    "Sam LaPorta",
    "Breece Hall",
]

ai_players = [
    "Jalen Hurts",
    "Jahmyr Gibbs",
    "Derrick Henry",
    "Dalton Schultz",
    "Cooper Kupp",
    "Jaylen Waddle",
    "DeVonta Smith",
]


def get_player_points(file_path, players):
    player_points = {}
    with open(file_path, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Player"] in players:
                player_points[row["Player"]] = float(row["TTL"])
    return player_points


file_path = "tools/data/FantasyPros_Fantasy_Football_Points_PPR.csv"

# Calculate points for ESPN players
espn_player_points = get_player_points(file_path, espn_players)
espn_total_points = sum(espn_player_points.values())

# Calculate points for AI players
ai_player_points = get_player_points(file_path, ai_players)
ai_total_points = sum(ai_player_points.values())

# Print results
print("ESPN Players and their TTL points:")
for player, points in espn_player_points.items():
    print(f"{player}: {points} points")
print(f"Total TTL points for ESPN players: {espn_total_points}\n")

print("AI Players and their TTL points:")
for player, points in ai_player_points.items():
    print(f"{player}: {points} points")
print(f"Total TTL points for AI players: {ai_total_points}\n")

# Compare totals
if espn_total_points > ai_total_points:
    print("ESPN players have a higher total score.")
elif espn_total_points < ai_total_points:
    print("AI players have a higher total score.")
else:
    print("Both ESPN and AI players have the same total score.")
