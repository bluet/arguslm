"""Prompt packs for benchmarking and monitoring.

Each pack is designed to elicit different response lengths and styles,
enabling consistent and comparable metrics across runs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPack:
    id: str
    name: str
    prompt: str
    expected_tokens: int


PROMPT_PACKS: dict[str, PromptPack] = {
    "health_check": PromptPack(
        id="health_check",
        name="Health Check",
        prompt="Count from 1 to 20, each number on a new line.",
        expected_tokens=30,
    ),
    "shakespeare": PromptPack(
        id="shakespeare",
        name="Shakespeare",
        prompt=(
            "Write a short soliloquy in the style of Shakespeare about the nature of time. "
            "Use iambic pentameter and include at least one metaphor."
        ),
        expected_tokens=150,
    ),
    "synthetic_short": PromptPack(
        id="synthetic_short",
        name="Synthetic Short",
        prompt="Explain what an API is in exactly 3 sentences.",
        expected_tokens=50,
    ),
    "synthetic_medium": PromptPack(
        id="synthetic_medium",
        name="Synthetic Medium",
        prompt=(
            "Describe the process of photosynthesis in plants. Include the key molecules involved, "
            "the two main stages (light-dependent and light-independent reactions), and explain "
            "why this process is essential for life on Earth."
        ),
        expected_tokens=200,
    ),
    "synthetic_long": PromptPack(
        id="synthetic_long",
        name="Synthetic Long",
        prompt=(
            "Write a comprehensive guide on how to start a small business. Cover the following topics:\n"
            "1. Identifying a business idea and validating market demand\n"
            "2. Creating a business plan\n"
            "3. Legal structure and registration\n"
            "4. Funding options\n"
            "5. Setting up operations\n"
            "6. Marketing strategies\n"
            "7. Common mistakes to avoid\n\n"
            "Provide practical advice for each section."
        ),
        expected_tokens=500,
    ),
    "code_generation": PromptPack(
        id="code_generation",
        name="Code Generation",
        prompt=(
            "Write a Python function that implements a binary search algorithm. "
            "Include docstring, type hints, and handle edge cases. "
            "Then show an example of how to use it."
        ),
        expected_tokens=150,
    ),
    "reasoning": PromptPack(
        id="reasoning",
        name="Reasoning",
        prompt=(
            "A farmer has 17 sheep. All but 9 run away. How many sheep does the farmer have left? "
            "Explain your reasoning step by step."
        ),
        expected_tokens=100,
    ),
}

VALID_PROMPT_PACK_IDS: set[str] = set(PROMPT_PACKS.keys())


def get_prompt_pack(pack_id: str) -> PromptPack:
    """Get a prompt pack by ID."""
    if pack_id not in PROMPT_PACKS:
        raise ValueError(
            f"Unknown prompt pack: {pack_id}. Valid options: {', '.join(sorted(VALID_PROMPT_PACK_IDS))}"
        )
    return PROMPT_PACKS[pack_id]


def get_prompt(pack_id: str) -> str:
    """Get the prompt text for a pack ID."""
    return get_prompt_pack(pack_id).prompt


def list_prompt_packs() -> list[PromptPack]:
    """List all available prompt packs."""
    return list(PROMPT_PACKS.values())
