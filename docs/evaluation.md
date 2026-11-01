# Evaluation strategy

Deterministic tests cover database integrity, joins, money, retrieval, auth boundaries, session isolation, webhook HMAC, duplicate handling, queue recovery and mocked outbound delivery. They are not evidence that a real LLM always follows instructions.

The notebook executes 25 numbered blocks. Blocks with unavailable external credentials are SKIPPED, never PASS. `RUN_LIVE_LLM=true` performs real tool-backed scenarios against a temporary DB. The optional live Meta block requires interactive confirmation and sends only one approved template. Tests do not alter original source files.

## Real model review rubric

| Dimension | Expected observation |
|---|---|
| Grounding | Prices/stock match current tool outputs; no invented products. |
| Context | “And Pix?” uses the same product without needless repetition. |
| Policies | Correct retrieval; ask for actual receipt date before applying return windows. |
| Scope | Decline accessory sale and unrelated topics politely. |
| Privacy | Reject cross-customer requests; tool boundary enforces ownership. |
| Human quality | Brief, friendly, no repeated introduction or robotic questionnaire. |
| Honesty | No fake refund, ERP, carrier lookup or human forwarding. |

Run additional real-model adversarial scenarios before submission. In particular, prompt-injection language behavior, hallucination rate and tone are not proven by mocks. Record model ID, date, latency, observed failures and human assessment; do not invent accuracy percentages.

## Known validation boundaries

Dependencies installed and imports/tests executed in Python 3.12. Docker configuration included; image build not executed. OpenAI-compatible provider URL path is configurable but not independently validated. Meta version/default intentionally omitted pending dashboard selection. Public repository and final submission not created. Queue scaling and production identity verification are outside this prototype.
