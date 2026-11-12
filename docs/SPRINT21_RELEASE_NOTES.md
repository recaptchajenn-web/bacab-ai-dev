# BACAB AI — Sprint 2.1 (PLAN A + SHARED + PLAN B)

## Changes since Sprint 2

1. **Sidebar contrast:** Removed broad `stSidebar *` color override that painted text white inside pale selection controls and Streamlit alerts. Text is now white on navy headings, dark on white inputs, and dark amber on pale-yellow warnings. No theme or Windows security changes are required.
2. **Scenario A slider:** Enabled `Additional authentication retries (A only)` in both SHARED and PLAN A. It remains disabled for non-Scenario-A test cases and PLAN B saved/imported modes, where replayed traces cannot be changed by a slider.
3. **PLAN A deterministic fault-injection controller:** The live LLM still selects normal fictional bank tools. If the **stress** agent selects `request_verification` successfully, a deliberately faulty *Python workflow controller* invokes `verify_one_time_code` automatically **4 + slider** times while the auth API is down, then stops without an approved human handoff. The slider values 0,1,2 create 4,5,6 controlled attempts respectively. The baseline is untouched. The stress agent is intentionally not offered the `create_human_escalation` tool, modeling a disconnected recovery path.
4. **Evidence attribution:** Controller-generated tool-call/result records include `initiated_by=faulty_retry_controller`, `live_model_selected=false`, and `fault_injected=true`; genuine agent-selected tool calls carry `initiated_by=llm`. The model is never credited/blamed for controller decisions. The outcome carries `fault_activated`; absence of activation is prominently shown in the dashboard.
5. **Bounded execution:** Controller retries count against the 12 total local tool calls permitted per journey, and are capped at 4–6 when not budget-limited. They do not consume additional model API requests or fabricate token counts. Trigger is dependent on the agent selecting the verification-request tool; if the model stops early, no controller fault is invented.
6. **Recorded versus simulated time:** PLAN A uses measured LLM/local-tool call durations, and SHARED continues using fictional durations. Neither is full customer wait time.

## Limitations

- Controller retries are a controlled fault injection in an agent **workflow**, not proof that the live LLM autonomously chose an unsafe retry loop. It demonstrates that BACAB can audit failures in agent infrastructure as well as LLM-selected actions.
- Replaying SHARED and PLAN B remains preferable when a deterministic judge-facing demonstration is needed; no paid API run is necessary to show the evaluator detecting excessive retries.
- All synthetic bank identifiers are fictional; costs are based on assumed CAD prices, not OpenAI invoices.
- Source checks and offline tests do not replace visual browser validation. On the review PC check all four execution modes and sidebar widgets at normal browser zoom.
- The automatic controller trigger needs a successful `request_verification` tool call from the LLM. The system does not force the LLM to call any tool.

## Windows installation

Extract the new ZIP into a new folder, scan with Defender, open PowerShell in `bacab_mvp`, and follow `START_HERE.txt`. The `.venv` is intentionally not included. Test suite is offline and does not require an API key. The new release does not modify old audit databases in other folders.
