import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re

sns.set(style="whitegrid")

# === Load summary file ===
summary_path = "draft_results/draft_results_analysis.csv"
df = pd.read_csv(summary_path)

# === 1. Distribution of AI GM Scores and Ranks ===
fig, axs = plt.subplots(1, 2, figsize=(14, 5))

# Score distribution
sns.histplot(
    df["AI_General_Manager"].dropna(), bins=10, kde=True, ax=axs[0], color="lightblue"
)
axs[0].set_title("Distribution of AI GM Scores")
axs[0].set_xlabel("Score")
axs[0].set_ylabel("Frequency")

# Rank distribution (as histogram now)
sns.histplot(
    df["AI_Rank"].dropna(),
    bins=range(1, 14),
    ax=axs[1],
    color="lightgreen",
    discrete=True,
)
axs[1].set_title("Distribution of AI GM Ranks")
axs[1].set_xlabel("Rank")
axs[1].set_ylabel("Count")

plt.tight_layout()
plt.savefig("draft_results/ai_gm_distribution.png")
plt.show()

# === 2. Bar Chart of Key Summary Stats ===

ai_mean = df["AI_General_Manager"].mean()
overall_league_mean = df["Mean"].mean()  # from 'Mean' column

stats_df = pd.DataFrame(
    {
        "Metric": [
            "ESPN Top Picks Benchmark",
            "Overall League Avg",
            "AI Mean",
        ],
        "Score": [
            1671.6,  # 🔹 ESPN top picks total TTL
            overall_league_mean,
            ai_mean,
        ],
    }
)

# Plot: Narrow figure, tall height, narrow bars
plt.figure(figsize=(7, 5))  # 🔹 Narrow and tall
ax = sns.barplot(
    x="Metric", y="Score", data=stats_df, palette="mako", width=0.2
)  # 🔹 Narrower bars

# Formatting
plt.ylim(0, 1800)  # 🔹 Start from 0 to avoid exaggeration
plt.ylabel("Fantasy Points")
plt.title("AI GM vs League and ESPN Benchmarks")
plt.xticks(rotation=20)

# 🔹 Add value labels on top of bars
for bar in ax.patches:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height + 15,  # a bit above the bar
        f"{height:.1f}",
        ha="center",
        va="bottom",
        fontsize=10,
    )

plt.tight_layout()
plt.savefig("draft_results/benchmark_stats.png")
plt.show()

# === 4. Max/Min/AI Score Over Drafts ===
plt.figure(figsize=(10, 5))
df_sorted = df.sort_values("Filename")
plt.plot(
    [f"Draft {i}" for i in range(len(df_sorted))],
    df_sorted["Max"],
    label="Max",
    marker="o",
)
plt.plot(
    [f"Draft {i}" for i in range(len(df_sorted))],
    df_sorted["Min"],
    label="Min",
    marker="o",
)
plt.plot(
    [f"Draft {i}" for i in range(len(df_sorted))],
    df_sorted["AI_General_Manager"],
    label="AI GM",
    marker="o",
    linestyle="--",
    color="orange",
)
plt.xticks(rotation=90)
plt.title("Max, Min, and AI GM Scores Across Drafts")
plt.xlabel("Draft File")
plt.ylabel("Points")
plt.legend()
plt.tight_layout()
plt.savefig("draft_results/max_min_ai_over_drafts.png")
plt.show()


# Load TTL CSV once
ttl_csv_path = "./tools/data/FantasyPros_Fantasy_Football_Points_PPR.csv"  # 🔁 Replace with actual path
ttl_df = pd.read_csv(ttl_csv_path)


# Preprocess player names with suffix removal
suffix_pattern = r"\b(Jr\.?|Sr\.?|II|III|IV|V)\b"
ttl_df["Player_clean"] = ttl_df["Player"].apply(
    lambda name: re.sub(suffix_pattern, "", name).strip().lower()
)


def get_player_points(player_name):
    cleaned_name = re.sub(suffix_pattern, "", player_name).strip().lower()
    match = ttl_df[ttl_df["Player_clean"] == cleaned_name]
    if not match.empty:
        return match.iloc[0]["TTL"]
    print(
        f"[⚠️  Not Found] '{player_name}' (normalized to '{cleaned_name}') not found in TTL data."
    )
    return 0


# === Collect player scores by position ===
roster_dir = "draft_results"
position_points = {}

for file in sorted(os.listdir(roster_dir)):
    if file.startswith("rosters_") and file.endswith(".csv"):
        df = pd.read_csv(os.path.join(roster_dir, file))

        for _, row in df.iterrows():
            pos = row["Position"]
            name = row["Player"]
            pts = get_player_points(name)
            position_points.setdefault(pos, []).append(pts)

# === Create DataFrame of Stats ===
stats = []
for pos, scores in position_points.items():
    stats.append(
        {
            "Position": pos,
            "Count": len(scores),
            "Mean Points": round(sum(scores) / len(scores), 1),
            "Median Points": round(pd.Series(scores).median(), 1),
            "Max Points": max(scores),
            "Min Points": min(scores),
        }
    )

summary_df = pd.DataFrame(stats).sort_values("Position")
print(summary_df)

# === Optional: Plot bar chart of mean points ===
plt.figure(figsize=(8, 5))
sns.barplot(x="Position", y="Mean Points", data=summary_df, palette="coolwarm")
plt.title("Average Fantasy Points by Position Across All Drafts")
plt.ylabel("Mean Points")
plt.tight_layout()
plt.savefig("draft_results/position_mean_points_summary.png")
# plt.show()
