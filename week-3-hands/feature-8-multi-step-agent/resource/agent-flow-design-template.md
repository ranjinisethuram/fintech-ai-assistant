# Resource 8: Agent Flow Design Template

**AI Engineering Bootcamp · BlockseBlock · Week 3, Feature 8**

---

## What Is an Agent Flow?

An agent flow maps out a multi-step process so that an AI agent can execute it reliably. Think of it as a recipe: a trigger starts the process, steps describe what to do in order, tools are the ingredients, and the output is what the user receives at the end.

Designing flows explicitly — before writing code — prevents the most common agent failure: losing track of the goal halfway through execution.

---

## The Template

Use this template for any multi-step process you want your agent to handle:

```
FLOW NAME: [Short name for this flow]

TRIGGER: [What user input or event starts this flow?]
Example: "User says they can't log in to their account"

STEPS:
  Step 1: [What does the agent do first?]
    Tool needed: [tool_name]
    Input to tool: [what data is passed in]
    Output: [what comes back]

  Step 2: [What does the agent do next?]
    Tool needed: [tool_name]
    Input to tool: [what data is passed in — may depend on Step 1 result]
    Output: [what comes back]

  Step 3: [Optional: synthesis or follow-up action]
    Tool needed: [tool_name or "none — LLM synthesis"]
    Input to tool: [if needed]
    Output: [the final answer or action]

EXPECTED OUTPUT: [What does the user receive at the end?]
  Format: [plain text / JSON / confirmation message]
  Key information included: [bullet list of what the user needs to know]

FAILURE MODES TO HANDLE:
  - What if Step 1 tool returns an error? [fallback behaviour]
  - What if no results are found? [fallback behaviour]
  - What if Step 2 depends on Step 1's result but Step 1 returned nothing? [fallback]
```

---

## Worked Example: Process a New Customer Inquiry

```
FLOW NAME: Process Customer Inquiry

TRIGGER: User sends a message describing a problem or question (any topic)

STEPS:
  Step 1: Classify and check records
    Tool needed: lookup_info(topic="support categories")
    Input to tool: the user's message keywords
    Output: matching support category + standard response template

  Step 2: Check relevant records
    Tool needed: check_availability(date=None, time=None)
    Input to tool: service area from Step 1 classification
    Output: current status / availability of relevant service

  Step 3: Create a follow-up ticket
    Tool needed: create_ticket(subject, description, priority)
    Input to tool:
      - subject: short summary of the inquiry
      - description: full user message + Step 1 classification + Step 2 status
      - priority: "high" if Step 2 shows an active outage, "normal" otherwise
    Output: ticket ID and estimated response time

EXPECTED OUTPUT:
  Format: Plain text summary
  Key information included:
    - Acknowledgement of the issue
    - Current status (from Step 2)
    - Ticket reference number (from Step 3)
    - Expected response time

FAILURE MODES TO HANDLE:
  - Step 1 returns unknown category → use "general" category, continue
  - Step 2 returns error → skip status mention, proceed to Step 3
  - Step 3 (ticket creation) fails → tell user to call support directly
```

---

## Your Worksheet

Design ONE multi-step process from your domain using the template above.

### Hints

Choose a process that:
- Requires 2–4 tools in sequence (not just one lookup)
- Produces something the user can act on (a ticket, a booking, a report)
- Has at least one step where the result of Step N feeds into Step N+1

### Domain examples to spark your thinking

**Healthcare:** Classify symptom → check doctor availability → book appointment → create pre-visit notes

**E-commerce:** Check order status → look up return policy → initiate return → email confirmation

**HR:** Look up leave balance → check team calendar → submit leave request → notify manager

**Real estate:** Search listings by criteria → schedule viewing → create follow-up note → send confirmation

**Education:** Identify weak topic from quiz → find relevant document chunk → generate practice questions → log progress

---

Fill in the template for your domain:

```
FLOW NAME: Fixed Deposit enquiry.

TRIGGER: User says to provide info on opening an fixed deposit.

STEPS:
  Step 1:
    Tool needed: get_balance(accountId)
    Input to tool: savings account id of the logged in customer.
    Output: returns json object containing accountId, available balance, currency

  Step 2:
    Tool needed: lookup_info(topic)
    Input to tool: user message containing enquiry on a specific topic.
    Output: returns the json object containing info on the enquired topic.

  Step 3 (optional): This comes up only if user proceeds to open a FD after reviewing the FD details.
    Tool needed: create_fixed_deposit(deposit_amount,deposit_tenure,interest_payout_frequency,auto_renewal)
    Input to tool: deposit_amount, deposit_tenure,interest_payout_frequency,auto_renewal
    Output: returns json object containing the success/failure. If success, deposited_anount, deposited_tenure, payout_frequency,auto_renewal or reason for failure.

EXPECTED OUTPUT:
  Format: Combines the response of all the steps and returns a synthesized response conataing bullet points.
  Key information included: The available balance from the savings account and the details on opening a FD account, that includes types of FD, rate of interest and min tenure for each FD type.

FAILURE MODES TO HANDLE:
```
If get_balance() returns error, provide user friendly message to try again and proceed to next stpe to provide info on enquired topic.
If lookup_info() returns error, provide user friendly message to try again. If the enquired topic not found, provide the list of topics for which it can provide info.
---

## Choosing a Framework

Once you understand the pattern, here's when to reach for a framework:

| Situation | Recommended approach |
|---|---|
| Learning the fundamentals | Hand-rolled (what this course builds) — maximum visibility, no magic |
| Rapid prototyping with standard components | **LangChain** — chains, memory, retrievers already packaged |
| Agent needs conditional branching or retry logic | **LangGraph** — models flows as graphs; edges can branch and loop |
| Building multi-agent systems or need native MCP support | **Google ADK** — orchestrator/subagent pattern, native MCP client |
| Production agent with tool calling and streaming | Any of the above; choose based on your team's stack |

**The rule of thumb:** use the simplest thing that handles your branching requirements. A linear plan-and-execute loop (what we built here) handles 80% of use cases. Add LangGraph when you need `if condition: go to this node` — i.e., when your flow has meaningful decision points mid-execution.

Feature 9 shows how Google ADK connects to MCP servers natively — the same MCP servers you'll build in that feature work equally well with ADK, LangChain, or our hand-rolled client.
