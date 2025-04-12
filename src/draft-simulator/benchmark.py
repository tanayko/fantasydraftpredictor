import pandas as pd
import re


# Load the CSV file
file_path = "tools/data/FantasyPros_Fantasy_Football_Points_PPR.csv"
data = pd.read_csv(file_path)

# Filter top 11 players for each position
positions = ["QB", "WR", "RB", "TE"]
top_players = {}

for position in positions:
    top_players[position] = data[data["Pos"] == position].nlargest(11, "TTL")

# Display the top players for each position
for position, players in top_players.items():
    print(f"Top 11 {position}s:")
    print(players[["Player", "TTL"]])
    print()

    # Calculate and display the average points for each position
    for position, players in top_players.items():
        average_points = players["TTL"].mean()
        print(f"Average points for top 11 {position}s: {average_points:.2f}")
        # Calculate the benchmark score

# Calculate the benchmark score using mean
benchmark_score = (
    top_players["QB"]["TTL"].mean()
    + 2.5 * top_players["WR"]["TTL"].mean()
    + 2.5 * top_players["RB"]["TTL"].mean()
    + top_players["TE"]["TTL"].mean()
)

# Calculate the benchmark score using median
benchmark_score_median = (
    top_players["QB"]["TTL"].median()
    + 2.5 * top_players["WR"]["TTL"].median()
    + 2.5 * top_players["RB"]["TTL"].median()
    + top_players["TE"]["TTL"].median()
)

# Print both benchmark scores
print(f"Benchmark score using mean (QB + 2.5WR + 2.5RB + TE): {benchmark_score:.2f}")
print(
    f"Benchmark score using median (QB + 2.5WR + 2.5RB + TE): {benchmark_score_median:.2f}"
)


# Load the ESPN Standard rankings CSV file
espn_file_path = "tools/data/official_2024_fantasy_rankings/ESPN_Standard.csv"
espn_data = pd.read_csv(espn_file_path)

# Filter top 11 players for each position based on the smallest "ESPN" ranking
espn_top_players = {}

for position in positions:
    espn_top_players[position] = espn_data[espn_data["Pos"] == position].nsmallest(
        11, "ESPN"
    )


# Define suffix pattern to strip from names
suffix_pattern = r"\s+(Jr\.|Sr\.|II|III|IV|V)$"

# Normalize the names in the data['Player'] column
data["Player_clean"] = data["Player"].str.replace(suffix_pattern, "", regex=True)

# Collect results into a list of dictionaries
results = []

for position, players in espn_top_players.items():
    for _, player in players.iterrows():
        player_name_clean = re.sub(suffix_pattern, "", player["Name"])
        ttl_row = data[data["Player_clean"] == player_name_clean]

        if not ttl_row.empty:
            ttl = ttl_row.iloc[0]["TTL"]
        else:
            ttl = None

        results.append(
            {
                "Position": position,
                "Name": player["Name"],
                "ESPN": player["ESPN"],
                "TTL": ttl,
            }
        )

# Convert list to DataFrame
espn_ttl_results = pd.DataFrame(results)
# Calculate median and mean TTL for each position
position_stats = espn_ttl_results.groupby("Position")["TTL"].agg(["mean", "median"])

# Print the results
print("Median and Mean TTL for each position:")
print(position_stats)

# Calculate benchmark score using mean and median from position_stats
benchmark_mean = (
    position_stats.loc["QB", "mean"]
    + 2.5 * position_stats.loc["WR", "mean"]
    + 2.5 * position_stats.loc["RB", "mean"]
    + position_stats.loc["TE", "mean"]
)

benchmark_median = (
    position_stats.loc["QB", "median"]
    + 2.5 * position_stats.loc["WR", "median"]
    + 2.5 * position_stats.loc["RB", "median"]
    + position_stats.loc["TE", "median"]
)

# Print the benchmark scores
print(f"Benchmark score using mean (QB + 2.5WR + 2.5RB + TE): {benchmark_mean:.2f}")
print(f"Benchmark score using median (QB + 2.5WR + 2.5RB + TE): {benchmark_median:.2f}")
