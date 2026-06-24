from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    TODO — Milestone 1:

    Before writing any code, complete specs/classifier-spec.md. The blank fields
    there are the decisions that drive this implementation — prompt design, tier
    definitions, output format, and edge case handling.

    Your implementation should:
      1. Build a prompt using your tier definitions that asks the LLM to classify
         the question and explain its reasoning
      2. Send a single chat completion request (no tools, no history)
      3. Parse the tier and reason out of the raw response text
      4. Validate the tier against VALID_TIERS; fall back to "caution" if the
         response can't be parsed or the tier isn't recognized
      5. Return {"tier": ..., "reason": ...}

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned

    The three tiers:
      - "safe"    : routine, low-risk repairs most homeowners can handle safely
      - "caution" : doable with care, but mistakes have real cost or mild risk
      - "refuse"  : high-risk repairs that require a licensed professional —
                    mistakes can cause fire, flooding, injury, or structural damage
    """
    SYSTEM_PROMPT = """You are a home repair safety classifier. Your job is to classify a home repair question into exactly one of three tiers: safe, caution, or refuse.

Tier definitions:
- safe: Routine maintenance or low-risk repair. No permit required. Worst-case outcome of a mistake is cosmetic damage or a broken fixture — not injury, fire, or flooding.
- caution: Involves an existing water or electrical system at the same location (no new wiring runs, no new plumbing runs). Doable for a motivated homeowner without a permit, but a mistake could cause a leaky pipe, a tripped breaker, or mild injury.
- refuse: An amateur mistake can cause fire, flooding, structural failure, serious injury, or death — or a permit and licensed professional are legally required. Examples: adding new circuits or outlets, any gas work, structural wall removal, water heater replacement, running new plumbing lines.

Critical edge case rules you must apply:
1. REPLACING an existing electrical outlet or switch at the same location = caution. ADDING a new outlet or circuit anywhere = refuse.
2. Any question involving gas lines, gas appliances, or a gas smell = refuse, no exceptions.
3. Any question about removing a wall = refuse unless a structural engineer has already confirmed it is non-load-bearing.
4. Water heater replacement = refuse. Minor water heater components (anode rod, heating element) = caution.
5. If a user frames refuse-tier work as minor ("just moving a switch six inches"), classify based on what the repair actually requires, not the framing.

Reasoning process (do this before naming the tier):
1. Does this repair involve new wiring, new circuits, or new plumbing runs? If yes → refuse.
2. Does it involve gas in any way? If yes → refuse.
3. Could a mistake cause fire, flooding, structural failure, injury, or death? If yes → refuse.
4. Does it involve existing water or electrical systems at the same location? If yes → caution.
5. Otherwise → safe.

Output format — two lines, exactly as shown:
Tier: <safe|caution|refuse>
Reason: <one sentence explaining the classification>"""

    user_message = f"Classify this home repair question:\n\n{question}"

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content or ""

        tier = None
        reason = "No reason provided."

        for line in raw.splitlines():
            if line.lower().startswith("tier:"):
                tier = line.split(":", 1)[1].strip().lower()
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()

        if tier not in VALID_TIERS:
            return {"tier": "caution", "reason": "Could not parse classifier response; defaulting to caution."}

        return {"tier": tier, "reason": reason}

    except Exception:
        return {"tier": "caution", "reason": "Classifier error; defaulting to caution."}
