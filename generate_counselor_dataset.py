#!/usr/bin/env python3
"""Generate synthetic datasets for a counselor-training AI assistance task.

Outputs:
- data/train_dataset.csv  (for model training)
- data/study_dataset.csv  (for Assignment 2/3 human study)
"""

from __future__ import annotations

import argparse
import random
import string
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

LABEL_APPROPRIATE = "appropriate"
LABEL_PROBLEMATIC = "problematic"

GLOBAL_POOLS: Dict[str, List[str]] = {
    "emotion": [
        "overwhelmed",
        "anxious",
        "stuck",
        "drained",
        "hopeless",
        "ashamed",
        "numb",
        "on edge",
        "isolated",
        "guilty",
    ],
    "timeframe": [
        "for the past two weeks",
        "since last month",
        "for most of this semester",
        "lately",
        "for a while now",
        "for the last few days",
    ],
    "small_step": [
        "one manageable step",
        "one realistic change",
        "a small experiment",
        "a short plan for this week",
        "one concrete next step",
    ],
    "support_option": [
        "a trusted friend",
        "campus counseling",
        "your support network",
        "a mentor",
        "a care provider",
    ],
    "dismissal_phrase": [
        "you should just toughen up",
        "everyone deals with this",
        "you need to stop overthinking",
        "this is not a big deal",
        "you just need to be positive",
    ],
    "directive": [
        "do exactly what I say",
        "follow my plan and stop questioning it",
        "drop this and focus on productivity",
        "just push through and ignore the feelings",
    ],
    "judgment": [
        "If you were more disciplined, this would not happen",
        "You created this problem yourself",
        "This sounds like poor choices, not stress",
        "You are being dramatic",
    ],
}

TOPICS: List[Dict[str, object]] = [
    {
        "topic": "academic_stress",
        "risk_level": "moderate",
        "client_templates": [
            "{timeframe}, I have been panicking before {event} and I cannot sleep.",
            "When I think about {event}, my chest feels tight and I freeze.",
            "I keep comparing myself to classmates and I feel {emotion} all day.",
        ],
        "pools": {
            "event": ["midterms", "my practicum evaluation", "licensure prep", "group presentations"],
            "focus_area": ["school pressure", "performance anxiety", "academic expectations"],
        },
    },
    {
        "topic": "career_burnout",
        "risk_level": "moderate",
        "client_templates": [
            "I feel completely drained after work and I dread opening my laptop.",
            "{timeframe}, every shift leaves me exhausted and irritable.",
            "I am behind on tasks and feel {emotion} whenever email notifications pop up.",
        ],
        "pools": {
            "focus_area": ["work stress", "burnout", "constant pressure at work"],
            "event": ["deadlines", "performance reviews", "team meetings"],
        },
    },
    {
        "topic": "relationship_conflict",
        "risk_level": "low",
        "client_templates": [
            "My partner and I keep having the same fight and I feel unheard.",
            "After arguments at home, I replay everything and cannot focus.",
            "I do not know if I am asking for too much in this relationship.",
        ],
        "pools": {
            "focus_area": ["relationship conflict", "communication at home", "arguments with my partner"],
            "event": ["arguments", "silent treatment", "mixed signals"],
        },
    },
    {
        "topic": "family_conflict",
        "risk_level": "moderate",
        "client_templates": [
            "My family keeps pressuring me about my career choices and I feel trapped.",
            "Calls with my parents leave me tense for the rest of the day.",
            "I feel guilty setting boundaries with relatives even when I need space.",
        ],
        "pools": {
            "focus_area": ["family pressure", "boundary setting", "conflict with relatives"],
            "event": ["family calls", "holiday visits", "disagreements about my future"],
        },
    },
    {
        "topic": "grief_loss",
        "risk_level": "moderate",
        "client_templates": [
            "Since my loss, normal routines feel heavy and unreal.",
            "I keep thinking I should be doing better by now, but I still break down.",
            "Certain places remind me of them and I shut down emotionally.",
        ],
        "pools": {
            "focus_area": ["grief", "loss", "mourning"],
            "event": ["anniversaries", "quiet evenings", "family gatherings"],
        },
    },
    {
        "topic": "social_anxiety",
        "risk_level": "low",
        "client_templates": [
            "I avoid social events because I assume people will judge me.",
            "Before networking events, I feel nauseous and want to cancel.",
            "I replay conversations for hours and feel embarrassed.",
        ],
        "pools": {
            "focus_area": ["social anxiety", "fear of judgment", "social avoidance"],
            "event": ["social events", "group discussions", "introductions"],
        },
    },
    {
        "topic": "imposter_syndrome",
        "risk_level": "low",
        "client_templates": [
            "I got positive feedback, but I still feel like a fraud.",
            "Even when things go well, I assume I just got lucky.",
            "I keep waiting for people to realize I am not qualified.",
        ],
        "pools": {
            "focus_area": ["self-doubt", "imposter feelings", "fear of being exposed"],
            "event": ["performance reviews", "presentations", "new projects"],
        },
    },
    {
        "topic": "financial_stress",
        "risk_level": "moderate",
        "client_templates": [
            "Bills are piling up and I feel panic every time I check my account.",
            "I am working extra hours and still feel like I cannot catch up.",
            "Money stress is affecting my sleep and concentration.",
        ],
        "pools": {
            "focus_area": ["financial stress", "money anxiety", "budget pressure"],
            "event": ["rent payments", "loan bills", "unexpected expenses"],
        },
    },
    {
        "topic": "identity_stress",
        "risk_level": "low",
        "client_templates": [
            "I feel pulled between cultural expectations and what I want for myself.",
            "I am not sure where I fit, and it leaves me feeling disconnected.",
            "When people make assumptions about me, I shut down.",
        ],
        "pools": {
            "focus_area": ["identity stress", "belonging", "cultural pressure"],
            "event": ["family conversations", "class discussions", "social situations"],
        },
    },
    {
        "topic": "sleep_dysregulation",
        "risk_level": "low",
        "client_templates": [
            "My sleep schedule is chaotic and I cannot function during the day.",
            "I lie awake for hours replaying everything that went wrong.",
            "I wake up exhausted even when I am in bed all night.",
        ],
        "pools": {
            "focus_area": ["sleep problems", "nighttime rumination", "fatigue"],
            "event": ["bedtime", "early mornings", "next-day responsibilities"],
        },
    },
    {
        "topic": "substance_urge",
        "risk_level": "moderate",
        "client_templates": [
            "When stress spikes, I feel a strong urge to drink to numb out.",
            "I promised myself I would cut back, but cravings keep showing up.",
            "After hard days, I rely on substances to turn my brain off.",
        ],
        "pools": {
            "focus_area": ["coping with cravings", "substance urges", "stress coping"],
            "event": ["late nights", "after conflict", "after work"],
        },
    },
    {
        "topic": "trauma_reminder",
        "risk_level": "high",
        "client_templates": [
            "Certain sounds trigger flashbacks and I feel like I am back there.",
            "I avoid places that remind me of what happened, but it keeps intruding.",
            "Nightmares and sudden panic make me feel unsafe in my own body.",
        ],
        "pools": {
            "focus_area": ["trauma symptoms", "feeling unsafe", "flashbacks"],
            "event": ["loud noises", "crowded places", "unexpected reminders"],
        },
    },
    {
        "topic": "self_harm_ideation",
        "risk_level": "high",
        "client_templates": [
            "I keep thinking people would be better off without me.",
            "Sometimes I wish I could disappear because this all feels pointless.",
            "I am scared by how often thoughts of not waking up show up.",
        ],
        "pools": {
            "focus_area": ["safety", "hopeless thoughts", "self-harm risk"],
            "event": ["late night", "after conflict", "when I am alone"],
        },
    },
    {
        "topic": "domestic_safety_concern",
        "risk_level": "high",
        "client_templates": [
            "At home I feel watched and controlled, and I do not feel safe.",
            "My partner checks my phone and gets angry when I talk to others.",
            "I am afraid things could escalate if I set boundaries at home.",
        ],
        "pools": {
            "focus_area": ["personal safety", "controlling relationship", "home safety"],
            "event": ["arguments", "checking my phone", "isolation from friends"],
        },
    },
]

GOOD_RESPONSE_BANK: List[Dict[str, object]] = [
    {
        "pattern": "validation_open_question",
        "difficulty": "easy",
        "risk": ["low", "moderate"],
        "templates": [
            "Thank you for sharing this. It makes sense that you feel {emotion} given {focus_area}. What feels hardest right now?",
            "I hear how heavy this has been. Your reaction to {focus_area} is understandable. What part would you like to start with?",
        ],
    },
    {
        "pattern": "reflective_collaboration",
        "difficulty": "medium",
        "risk": ["low", "moderate"],
        "templates": [
            "It sounds like {focus_area} has been taking a lot of energy. Would it help if we identified {small_step} for this week?",
            "You are carrying a lot with {focus_area}. We can move at your pace and map one manageable next step together.",
        ],
    },
    {
        "pattern": "strengths_reframe",
        "difficulty": "hard",
        "risk": ["low", "moderate"],
        "templates": [
            "Part of you is exhausted, and part of you keeps showing up anyway. What has helped you get through even the toughest days?",
            "I hear both pain and effort in what you shared. Could we look at when {focus_area} feels even slightly more manageable?",
        ],
    },
    {
        "pattern": "safety_check_referral",
        "difficulty": "medium",
        "risk": ["high"],
        "templates": [
            "I am really glad you told me. Your safety matters. Are you in immediate danger right now? If yes, contact 988 or emergency services while we plan immediate support.",
            "Thank you for sharing this. I want to prioritize your safety first. Are you currently safe? If there is immediate risk, please call 988 or local emergency services now.",
        ],
    },
    {
        "pattern": "safety_plan_collaboration",
        "difficulty": "hard",
        "risk": ["high"],
        "templates": [
            "What you shared is serious, and I appreciate your honesty. Let us focus on immediate safety and identify one person from {support_option} you can contact today.",
            "I hear how intense this is. Before anything else, let us make a short safety plan for the next 24 hours and connect you with direct support.",
        ],
    },
]

BAD_RESPONSE_BANK: List[Dict[str, object]] = [
    {
        "pattern": "invalidation",
        "difficulty": "easy",
        "risk": ["low", "moderate"],
        "templates": [
            "You are overreacting. {dismissal_phrase}.",
            "This is not worth this much emotion. {dismissal_phrase}.",
        ],
    },
    {
        "pattern": "judgmental_blame",
        "difficulty": "easy",
        "risk": ["low", "moderate"],
        "templates": [
            "{judgment}. You should just be more responsible.",
            "Honestly, this sounds self-inflicted. You need better discipline.",
        ],
    },
    {
        "pattern": "premature_directive",
        "difficulty": "medium",
        "risk": ["low", "moderate"],
        "templates": [
            "I do not need more details. {directive}.",
            "Do not dwell on this. {directive}.",
        ],
    },
    {
        "pattern": "toxic_positivity",
        "difficulty": "hard",
        "risk": ["low", "moderate"],
        "templates": [
            "I hear this is hard, but you should focus only on gratitude and stop talking about the negative.",
            "Thanks for sharing, but if you stay positive this will disappear quickly.",
        ],
    },
    {
        "pattern": "boundary_crossing",
        "difficulty": "hard",
        "risk": ["low", "moderate"],
        "templates": [
            "Do not involve anyone else. Just message me anytime day or night and I will fix this personally.",
            "You only need me for this. Keep this between us and follow my instructions.",
        ],
    },
    {
        "pattern": "safety_underreaction",
        "difficulty": "easy",
        "risk": ["high"],
        "templates": [
            "You are probably just exhausted. Get some sleep and you will be fine.",
            "This sounds dramatic, not urgent. Try to distract yourself and move on.",
        ],
    },
    {
        "pattern": "confidentiality_breach",
        "difficulty": "medium",
        "risk": ["high"],
        "templates": [
            "I will contact your family and supervisor right away without asking you first.",
            "I am going to share this with others immediately. We do not need to discuss consent.",
        ],
    },
    {
        "pattern": "coercive_control",
        "difficulty": "hard",
        "risk": ["high"],
        "templates": [
            "You need to do exactly what I say right now. If you disagree, there is no point continuing.",
            "Stop questioning this and follow my instructions immediately.",
        ],
    },
]


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str, pools: Dict[str, List[str]], rng: random.Random) -> str:
    formatter = string.Formatter()
    keys = [field_name for _, field_name, _, _ in formatter.parse(template) if field_name]
    values: Dict[str, str] = {}
    for key in keys:
        choices = pools.get(key)
        if not choices:
            values[key] = key.replace("_", " ")
        else:
            values[key] = rng.choice(choices)
    return template.format_map(SafeDict(values))


def build_trial(
    trial_id: str,
    split: str,
    label: str,
    rng: random.Random,
) -> Dict[str, object]:
    topic = rng.choice(TOPICS)
    topic_name = str(topic["topic"])
    risk_level = str(topic["risk_level"])

    local_pools: Dict[str, List[str]] = dict(GLOBAL_POOLS)
    local_pools.update(topic["pools"])  # type: ignore[index]

    client_template = rng.choice(topic["client_templates"])  # type: ignore[index]
    client_utterance = render_template(client_template, local_pools, rng)

    if label == LABEL_APPROPRIATE:
        bank = [item for item in GOOD_RESPONSE_BANK if risk_level in item["risk"]]
    else:
        bank = [item for item in BAD_RESPONSE_BANK if risk_level in item["risk"]]

    picked = rng.choice(bank)
    response_template = rng.choice(picked["templates"])  # type: ignore[index]
    counselor_response = render_template(response_template, local_pools, rng)

    model_output = ""
    model_probability = ""

    return {
        "trial_id": trial_id,
        "split": split,
        "task_name": "counselor_response_appropriateness",
        "topic": topic_name,
        "risk_level": risk_level,
        "difficulty": str(picked["difficulty"]),
        "response_pattern": str(picked["pattern"]),
        "input_client_statement": client_utterance,
        "input_counselor_response": counselor_response,
        "input_text": f"Client: {client_utterance} Counselor response: {counselor_response}",
        "ground_truth": label,
        "ground_truth_binary": 1 if label == LABEL_APPROPRIATE else 0,
        "model_output": model_output,
        "model_probability": model_probability,
        "human_rating_of_model_output": "",
        "dataset_source": "synthetic_custom_created_for_hw2",
    }


def generate_split(split: str, n_rows: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)

    labels: List[str] = [LABEL_APPROPRIATE] * (n_rows // 2) + [LABEL_PROBLEMATIC] * (n_rows - n_rows // 2)
    rng.shuffle(labels)

    rows: List[Dict[str, object]] = []
    seen_pairs = set()

    i = 0
    attempts = 0
    max_attempts = n_rows * 50
    while i < n_rows and attempts < max_attempts:
        attempts += 1
        label = labels[i]
        trial_id = f"{split}_{i + 1:04d}"
        row = build_trial(trial_id=trial_id, split=split, label=label, rng=rng)

        pair_key = (row["input_client_statement"], row["input_counselor_response"], row["ground_truth"])
        if pair_key in seen_pairs:
            continue

        seen_pairs.add(pair_key)
        rows.append(row)
        i += 1

    if len(rows) < n_rows:
        raise RuntimeError(f"Could not generate enough unique rows for split={split}.")

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate counselor-training datasets.")
    parser.add_argument("--n-train", type=int, default=3200, help="Number of rows in train split.")
    parser.add_argument("--n-study", type=int, default=240, help="Number of rows in study split.")
    parser.add_argument("--seed", type=int, default=594, help="Random seed.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="Output directory.",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_df = generate_split(split="train", n_rows=args.n_train, seed=args.seed)
    study_df = generate_split(split="study", n_rows=args.n_study, seed=args.seed + 1)

    train_path = args.out_dir / "train_dataset.csv"
    study_path = args.out_dir / "study_dataset.csv"

    train_df.to_csv(train_path, index=False)
    study_df.to_csv(study_path, index=False)

    print(f"Saved train dataset: {train_path} ({len(train_df)} rows)")
    print(f"Saved study dataset: {study_path} ({len(study_df)} rows)")
    print("Label distribution (study):")
    print(study_df["ground_truth"].value_counts().to_string())


if __name__ == "__main__":
    main()
