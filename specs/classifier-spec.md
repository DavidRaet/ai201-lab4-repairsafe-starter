# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance or low-risk repair that requires no permit, no licensed professional, and where the worst-case outcome of a mistake is cosmetic damage or a broken fixture — not injury, fire, or flooding.
```

**caution:**
```
A repair that involves an existing water or electrical system at the same location (no new wiring or new plumbing runs), is doable for a motivated homeowner, requires no permit, but where a mistake could cause a leaky pipe, a tripped breaker, or mild risk of injury.
```

**refuse:**
```
A repair where an amateur mistake can cause fire, flooding, structural failure, serious injury, or death — or where local building codes require a licensed professional and a permit (e.g., adding new circuits, any gas work, structural modifications, water heater replacement).
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
Approach: tier definitions + explicit edge-case rules + step-by-step reasoning before naming the tier.

Rationale: definitions alone leave room for interpretation on boundary cases. Asking the LLM to reason
step-by-step ("does this repair involve new wiring or new plumbing runs? could a mistake cause fire/flood/injury?")
forces it to apply the decision rule explicitly rather than pattern-matching to vague tier labels.

Ambiguous example — "can I replace my own outlets?":
The word "replace" signals an existing circuit at the same location → caution. But if the question said
"add outlets," that would be refuse. The step-by-step reasoning step surfaces this distinction before
the tier is named.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Tier: <safe|caution|refuse>
Reason: <one sentence>

Parsing logic: extract the word after "Tier:" on the first matching line, strip whitespace,
lowercase it, then validate against VALID_TIERS. Extract the text after "Reason:" on the
second matching line. This two-field format is easy to parse with a regex or simple split
and minimizes variation compared to free-form prose.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a home repair safety classifier. Your job is to classify a home repair question into exactly one of three tiers: safe, caution, or refuse.

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
Reason: <one sentence explaining the classification>
```

**User message:**
```
Classify this home repair question:

{question}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Rule: If the repair could cause fire, flooding, structural failure, serious injury, or death if done wrong —
or requires a permit and licensed professional — classify as refuse; otherwise classify as caution.

Example 1 — "Can I replace an electrical outlet that stopped working?"
→ caution: existing circuit, same location, component swap. Worst case = tripped breaker. No new wiring.

Example 2 — "Can I add a new electrical outlet to my garage?"
→ refuse: requires opening the breaker panel, running new wire, and pulling a permit.
An amateur mistake creates a fire hazard that may not be discovered for years.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
Fallback: return {"tier": "caution", "reason": "Could not parse classifier response; defaulting to caution."}

Why caution and not safe: returning "safe" on a parse failure could route a refuse-tier question to
full DIY instructions — the worst possible outcome. Returning "caution" is a conservative middle ground:
the responder will still warn the user and recommend a professional for anything risky, without
completely refusing a genuinely safe question.

Implementation: after extracting the tier string, call .strip().lower() and check membership in
VALID_TIERS. If the check fails for any reason (parse error, unexpected format, API error), return
the caution fallback dict above.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
[your answer here]
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
[your answer here]
```
