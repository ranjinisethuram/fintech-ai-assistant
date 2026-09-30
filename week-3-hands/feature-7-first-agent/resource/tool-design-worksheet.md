# Resource 7: Tool Design Worksheet

**Feature 7 · AI Engineering Bootcamp · BlockseBlock**

This worksheet covers three things: the anatomy of a well-designed tool, a worked example you can use as a reference, and a blank design template for the tools you will build in your own domain.

---

## 1. Anatomy of a Tool

Every tool has four components. Understanding what each one does — and why — is the difference between tools the model uses reliably and tools it ignores or misuses.

### The Python Function

The function is the actual implementation: the code that runs when the model decides to use this tool. It receives arguments the model chose and returns a plain dict. The function does not need to know anything about the LLM — it is just a Python function.

```python
async def check_availability(date: str, time: str) -> dict:
    # ... real implementation checks a calendar API or database
    return {"available": True, "slot": f"{date}T{time}"}
```

Keep functions focused: one tool should do one thing. If a function is doing three things, split it into three tools.

### The Function Signature

The parameter names and types are not just for Python's benefit — the model uses them too. When the model decides to call a tool, it generates arguments by name. If you name a parameter `dt` instead of `date`, the model may pass `date` anyway (because that is what the description says), and Python will raise a `TypeError`. Match parameter names to what the description says they are.

### The Docstring

The docstring is what you document for human readers. In frameworks like ADK and LangChain, the docstring is also what the framework uses to auto-generate the schema. Even when you write the schema by hand (as you do here), the docstring is important: it keeps your intent legible when you or a teammate reads the code three months later.

### The JSON Schema (TOOL_SCHEMA dict)

The schema is the formal contract you pass to the LLM. It tells the model:
- The function's name (must match the Python function name exactly)
- A description of what the tool does and when to use it
- The parameters it accepts, each with its own name, type, and description

**Why descriptions matter most:** The model does not see your Python code. It sees only the schema. The `description` fields — both at the function level and for each parameter — are the only information the model has when deciding whether to call this tool and what arguments to pass. A vague description means unpredictable behavior. A precise description, written from the model's perspective ("Call this when the user asks..."), gives the model a reliable signal.

```
                  ┌───── model reads this to decide WHEN to call ─────┐
                  │                                                     │
"description": "Check whether a time slot is available for booking.    │
                Call this when the user asks if a date or time          │
                is free."                                              ─┘

"properties": {
    "date": {
        "type": "string",
        "description": "The date to check in YYYY-MM-DD format."
                     ─┐
                      └── model reads this to decide WHAT to pass as the argument
    }
}
```

---

## 2. Fully Worked Example: `check_availability`

Here is the complete implementation of one tool, annotated so you can see how the pieces fit.

### Python Function

```python
async def check_availability(date: str, time: str) -> dict:
    """
    Check whether a given date and time slot is available for an appointment.

    In production this would query a calendar service or database.
    For the bootcamp, we return a mock response.

    Args:
        date: The date to check, formatted as YYYY-MM-DD.
        time: The time to check, formatted as HH:MM in 24-hour time.

    Returns:
        A dict with 'available' (bool) and 'slot' (ISO datetime string).
    """
    # Mock implementation — replace with a real calendar API call
    return {
        "available": True,
        "slot": f"{date}T{time}",
    }
```

**What to note:**
- The function is `async` — all tools in this codebase should be awaitable
- Parameters are typed (`str`) — this documents intent and helps the model fill them correctly
- The return value is a flat dict — simple for the model to read and summarize
- The docstring explains what it does, what the args mean, and what it returns

### JSON Schema

```python
CHECK_AVAILABILITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_availability",             # must match the Python function name exactly
        "description": (
            "Check whether a time slot is available for booking. "
            "Call this when the user asks if a date or time is free, "
            "or wants to know about appointment availability."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date to check, in YYYY-MM-DD format.",
                },
                "time": {
                    "type": "string",
                    "description": "The time to check, in HH:MM 24-hour format (e.g. '14:30').",
                },
            },
            "required": ["date", "time"],         # both are needed — the model must provide them
        },
    },
}
```

**Annotations:**

| Part | Why it is written this way |
|---|---|
| `"name": "check_availability"` | Must be identical to the Python function name. The `TOOLS_REGISTRY` maps this name to the callable — a mismatch is a `KeyError` at runtime. |
| `"description"` at function level | Tells the model when to call this tool. The phrase "Call this when..." is intentional — it gives the model a direct trigger condition. |
| `"description"` at parameter level | Tells the model what format to use for each argument. Without "YYYY-MM-DD", the model might pass "July 3rd" and the calendar API would reject it. |
| `"required": ["date", "time"]` | Forces the model to provide both arguments before calling. Without this, the model might omit `time` and the function would receive a missing argument. |

### Sample Return Value

```python
{"available": True, "slot": "2026-07-03T14:30"}
```

This is what the model sees in Call 2. It synthesizes this into a natural response: *"Yes, Friday at 2:30 PM is available. Would you like me to book it?"*

### How the Description Maps to When the Model Calls It

If a user says: *"Do you have anything open this Thursday afternoon?"*

The model reads all the tool schemas, finds `check_availability`'s description — *"Check whether a time slot is available for booking. Call this when the user asks if a date or time is free..."* — and decides this tool fits. It then figures out from the conversation (or asks a follow-up if needed) what `date` and `time` to pass.

If a user says: *"What does a fitting appointment usually cost?"*

The model reads the same description. Nothing in it suggests this tool answers pricing questions, so it does not call it. It answers from its training data or from other tools instead.

This is why the function-level description is the most important text you write.

---

## 3. The Schema Template

Copy this template for each new tool. Fill in the blanks.

```python
YOUR_TOOL_NAME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "...",           # Python function name — must match exactly
        "description": (
            "..."                # What does this tool do?
            "Call this when ..."  # When should the model use it?
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string",    # "string" | "integer" | "boolean" | "number"
                    "description": "...",
                },
                # add more parameters here
            },
            "required": ["param_name"],  # list every required parameter
        },
    },
}
```

And the matching function skeleton:

```python
async def your_tool_name(param_name: str) -> dict:
    """
    One-sentence summary of what this tool does.

    Args:
        param_name: What this parameter means and its expected format.

    Returns:
        A flat dict with the result. Key names should be self-explanatory.
    """
    # your implementation here
    return {"key": "value"}
```

Register it in `TOOLS_REGISTRY`:

```python
TOOLS_REGISTRY = {
    "your_tool_name": {
        "function": your_tool_name,
        "schema": YOUR_TOOL_NAME_SCHEMA,
    },
    # ... other tools
}
```

---

## 4. Worksheet: Design 3 Tools for Your Domain

Use this before writing any code. A five-minute sketch here prevents an hour of debugging why the model is not calling your tool.

---

### Tool 1

**Tool name:** ______get_balance_____

**One-sentence description** (this becomes `schema["function"]["description"]`):

> ____Returns the total available balance of a customer account_______

**Trigger phrase** (complete this: "Call this when the user..."): 

> ______Call this when the logged in customer enquires about the current or available balance in their account._____

**Parameters:**

| Name | Type | Description |
|customerId|uuid|unique id of the logged in customer|
|accountId |uuid |account id associated with the customer |
| | | |
| | | |

**Sample return value** (what dict does the function return on success?):

```python
{
    # fill in the keys and example values
    "accountId": aedb12345h567,
    "availableBalance": 5,88,000.00,
    "currency": "INR"
}
```

**Test message — a user message that SHOULD trigger this tool:**

> _____Can you tell me the current available balance of my account.______

**Counter-test — a message that should NOT trigger this tool** (but might look similar):

> ____Can you give me the total amount spent from last 10 transactions._______
Can you tell me the total available balance from the account with the id bearing aer12iuhgbd

---

### Tool 2

**Tool name:** ___________

**One-sentence description:**

> ___________

**Trigger phrase:**

> ___________

**Parameters:**

| Name | Type | Description |
|---|---|---|
| | | |
| | | |
| | | |

**Sample return value:**

```python
{
    # fill in the keys and example values
}
```

**Test message:**

> ___________

**Counter-test:**

> ___________

---

### Tool 3

**Tool name:** ___________

**One-sentence description:**

> ___________

**Trigger phrase:**

> ___________

**Parameters:**

| Name | Type | Description |
|---|---|---|
| | | |
| | | |
| | | |

**Sample return value:**

```python
{
    # fill in the keys and example values
}
```

**Test message:**

> ___________

**Counter-test:**

> ___________

---

## 5. Common Mistakes

These are the most frequent failure modes when building tools for the first time. Each one has a symptom you can observe in the `steps` array from `/api/agent/run`.

---

**Vague description — the model never calls the tool.**

Symptom: You send a message that clearly needs this tool, but `steps` is empty and the model answers from training data or makes something up.

Example of the problem:
```python
"description": "Gets information about availability."
```

Fix — be specific and give the model a trigger:
```python
"description": (
    "Check whether a specific date and time slot is open for booking. "
    "Call this when the user asks if a particular time is available, "
    "or wants to know about appointment slots."
)
```

The phrase "Call this when..." is not required by the spec, but it reliably improves model behavior. Think of it as writing a routing rule the model will follow.

---

**Too many parameters — the model fills them incorrectly or refuses to call.**

The model must infer all required parameters from the conversation. If your tool has six required parameters and the user's message only mentions two, the model either asks a series of clarifying questions (slowing the conversation) or hallucinates values for the missing ones.

Keep to four or fewer required parameters. If you need more, split into two tools or make some parameters optional with sensible defaults.

---

**Returning complex nested objects — the model misreads the result.**

The model synthesizes your tool's return value into natural language in Call 2. Nested structures increase the chance it misreads a value or describes the wrong thing.

```python
# Hard for the model to summarize correctly
return {
    "slot": {
        "date": {"year": 2026, "month": 7, "day": 3},
        "time": {"hour": 14, "minute": 30},
        "metadata": {"timezone": "UTC", "duration_minutes": 60}
    }
}

# Simple, flat, unambiguous
return {
    "available": True,
    "slot": "2026-07-03T14:30",
    "timezone": "UTC"
}
```

Flat dicts with string values are the most reliably summarized.

---

**One tool doing too much — the model calls it at the wrong times.**

If a single tool handles both "check availability" and "create a booking", its description cannot be precise enough to distinguish between the two cases. Split the actions:

- `check_availability` — read-only, safe to call as a preliminary step
- `create_booking` — writes data, should only be called when the user confirms

Mixing them means the model might create a booking when the user only asked if a slot was free.

---

**Raising exceptions instead of returning errors — the agent loop crashes.**

Tools must not raise unhandled exceptions. If a tool call fails (API is down, invalid date, resource not found), return an error in the dict:

```python
# Wrong — crashes the agent loop
async def check_availability(date: str, time: str) -> dict:
    result = calendar_api.get(date, time)   # raises if API is down
    return result

# Right — error stays in-band, the model can explain what happened
async def check_availability(date: str, time: str) -> dict:
    try:
        result = calendar_api.get(date, time)
        return {"available": result.is_open, "slot": result.iso_string}
    except Exception as e:
        return {"error": str(e), "available": False}
```

When a tool returns `{"error": "..."}`, the model in Call 2 can read that and tell the user something went wrong. When a tool raises, the agent loop itself raises and the user gets a 500 error with no explanation.

---

## 6. Frameworks at a Glance

You have built this from scratch. Here is how it maps to what the major frameworks offer, so you can make an informed choice when you reach for one.

| Aspect | Your Implementation | Google ADK | LangChain Agents |
|---|---|---|---|
| **Control** | Full — you see every call | High — declarative config | Medium — framework decides routing |
| **Boilerplate** | More — write the loop yourself | Less — `@tool` + `Agent()` | Least — `create_openai_tools_agent()` |
| **Debuggability** | Best — you wrote it, you understand it | Good — built-in tracing | Harder to trace |
| **Multi-agent** | Manual | Native (multiple agents as tools) | Via LangGraph |
| **MCP support** | Feature 9 (you will build it) | Native | Via plugin |
| **Best for** | Learning + full control | Production on Google Cloud | Complex chains |

None of these is universally "better." The right choice depends on how much control you need and how much you want the framework to decide. Start here — maximum control — then reach for a framework when the boilerplate becomes the bottleneck, not before. When a framework's agent does the wrong thing and you cannot figure out why, you will be glad you understand what is happening inside the loop.

---

## 7. Going Further — DeepAgent and Dynamic Tool Discovery

The static tool registry you built works well when the tool space is small, stable, and known in advance. Most production agents today use exactly this pattern. DeepAgent ([github.com/RUC-NLPIR/DeepAgent](https://github.com/RUC-NLPIR/DeepAgent), WWW 2026 Oral, Renmin University of China and Xiaohongshu) explores what happens when those conditions no longer hold.

The core insight in DeepAgent is that when the space of possible tools is large — 16,000+ RapidAPIs in their experiments — pre-registration is not feasible. No team can anticipate which tools a task will require. DeepAgent treats "find the right tool" as a reasoning step rather than a configuration step: the agent searches the tool space dynamically as part of solving the problem. This is one of four action types in DeepAgent's unified reasoning stream, alongside internal thought, tool call, and memory fold. Memory folding addresses a different bottleneck: as tasks grow longer and require more steps, the context window fills up. DeepAgent compresses history into three memory layers — episodic (past events), working (current task state), and tool (tools tried and their outcomes) — so the agent can reason across long tasks without losing earlier context.

For most production applications today, a well-designed static registry is the right choice. It is predictable, debuggable, and fast to build. DeepAgent is the horizon — understanding it tells you what comes after the registry, and what design decisions matter when the tool space grows too large to enumerate in advance.
