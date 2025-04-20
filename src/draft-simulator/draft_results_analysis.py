import os
import pandas as pd

ranking_dir = "draft_results"
output_csv = os.path.join(ranking_dir, "draft_results_analysis.csv")

results = []

for file in sorted(os.listdir(ranking_dir)):
    if file.startswith("rankings_") and file.endswith(".csv"):
        df = pd.read_csv(os.path.join(ranking_dir, file))

        max_score = df["Points"].max()
        min_score = df["Points"].min()
        mean_score = df["Points"].mean()
        median_score = df["Points"].median()

        ai_row = df[df["Team"] == "AI_General_Manager"]
        ai_score = ai_row.iloc[0]["Points"] if not ai_row.empty else None
        ai_rank = ai_row.iloc[0]["Rank"] if not ai_row.empty else None

        results.append(
            {
                "Filename": file,
                "Max": max_score,
                "Min": min_score,
                "AI_General_Manager": ai_score,
                "AI_Rank": ai_rank,
            }
        )

# Save summary
summary_df = pd.DataFrame(results)
summary_df.to_csv(output_csv, index=False)
print(f"✅ Summary with AI rank saved to {output_csv}")

# Compute stats
numeric_cols = summary_df.drop(columns=["Filename"]).select_dtypes(include="number")
mean_stats = numeric_cols.mean()
median_stats = numeric_cols.median()

# Print header
print("\n📊 Overall Averages Across All Drafts:\n")
print(f"{'Stat':<22} | {'Mean':>8} | {'Median':>8}")
print("-" * 45)

# Print each row
for col in numeric_cols.columns:
    mean_val = f"{mean_stats[col]:.2f}" if pd.notnull(mean_stats[col]) else "N/A"
    median_val = f"{median_stats[col]:.2f}" if pd.notnull(median_stats[col]) else "N/A"
    print(f"{col:<22} | {mean_val:>8} | {median_val:>8}")
