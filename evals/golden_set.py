"""A small, hand-picked set of texts with expected minimum critic scores.
Not exhaustive -- just enough to catch an obvious regression if the
rewriter/critic model or prompts change later."""

GOLDEN_SET = [
    {
        "name": "simple_factual",
        "text": "The meeting is scheduled for 3 PM on Tuesday in Conference Room B.",
        "tone": "neutral",
        "min_meaning": 8,
        "min_tone": 6,
    },
    {
        "name": "dramatic_source",
        "text": "The storm raged fiercely, lightning cracking across the sky as the "
        "ancient forest whispered secrets through the rustling leaves.",
        "tone": "suspenseful",
        "min_meaning": 7,
        "min_tone": 7,
    },
    {
        "name": "motivational_target",
        "text": "She studied every night for a month before the exam and passed with the highest score in her class.",
        "tone": "inspiring",
        "min_meaning": 7,
        "min_tone": 7,
    },
    {
        "name": "dialogue_heavy",
        "text": '"Where are you going?" she asked. "Somewhere far from here," he replied, not looking back.',
        "tone": "suspenseful",
        "min_meaning": 7,
        "min_tone": 6,
    },
    {
        "name": "numbers_and_names",
        "text": "Dr. Sarah Chen published 12 papers in 2023, a 40% increase over the previous year.",
        "tone": "neutral",
        "min_meaning": 8,
        "min_tone": 5,
    },
]
