from datasets import load_dataset
import pandas as pd

# Load dataset
dataset = load_dataset("dair-ai/emotion")

# Take examples from train split
df = dataset["train"].to_pandas()

# Map labels to names (for your reference only)
label_map = {
    0: "anger",
    1: "fear",
    2: "joy",
    3: "love",
    4: "sadness",
    5: "surprise"
}

df["label_name"] = df["label"].map(label_map)

# Sample 10 tweets covering multiple emotions
sampled = (
    df.groupby("label_name", group_keys=False)
      .apply(lambda x: x.sample(2, random_state=42))
      .sample(10, random_state=42)
)

# Keep only text column for MTurk
mturk_df = sampled[["text"]]

# Save CSV
mturk_df.to_csv("emotion_mturk_input.csv", index=False)

