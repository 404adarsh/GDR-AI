"""Acceptance Test 14: Workflows and Automation Builder.
Verifies:
1. Natural language compilation of spoken workflow prompt into structured steps.
2. Presentation of workflow policy approval card (decision=ASK).
3. Dry run execution simulating triggers, policy checks, and safe outputs without side-effects.
4. Workflow approval and activation state transition.
"""

from pathlib import Path
import pytest
from gdr.workflows.engine import WorkflowBuilder
from gdr.safety.policy_engine import ActionDecision


def test_acceptance_14_spoken_workflow_approval_and_dry_run(tmp_path):
    builder = WorkflowBuilder(config_dir=tmp_path)

    # 1. User says workflow out loud
    spoken_prompt = (
        "Every morning at 7, check all my Gmail accounts, summarize anything urgent, "
        "add deadlines to my calendar as drafts, and read me the briefing"
    )

    result = builder.compile_natural_language(spoken_prompt)

    # Verify workflow compilation
    workflow = result["workflow"]
    assert workflow["status"] == "pending_approval"
    assert workflow["trigger"]["type"] == "time"
    assert "7" in workflow["trigger"]["schedule"]

    # Verify steps decomposition
    steps = workflow["steps"]
    assert len(steps) >= 3
    tool_names = [s["tool"] for s in steps]
    assert "google_unified_inbox" in tool_names
    assert "google_urgent_check" in tool_names

    # 2. Verify GDR shows workflow for approval via PolicyCard
    policy_card = result["policy_card"]
    assert policy_card.decision == ActionDecision.ASK
    assert "Workflow" in policy_card.summary
    assert result["status"] == "waiting_for_approval"

    # 3. Dry run works cleanly
    wf_id = workflow["workflow_id"]
    dry_run_res = builder.dry_run(wf_id)

    assert dry_run_res["success"] is True
    assert dry_run_res["dry_run_passed"] is True
    assert len(dry_run_res["step_results"]) == len(steps)
    for sr in dry_run_res["step_results"]:
        assert sr["status"] == "simulated_success"

    # 4. User approves the workflow
    approved = builder.approve_workflow(wf_id)
    assert approved is True

    # Verify workflow is now active
    active_workflows = builder.list_workflows()
    target_wf = next(w for w in active_workflows if w["workflow_id"] == wf_id)
    assert target_wf["status"] == "active"

    print("\n--- Acceptance Test 14 Passed Output ---")
    print(f"Spoken Prompt: {spoken_prompt}")
    print(f"Compiled Workflow: {workflow['title']} (Trigger: {workflow['trigger']['description']})")
    print(f"Policy Decision: {policy_card.decision}")
    print(f"Dry Run Result: {dry_run_res['dry_run_passed']} across {len(steps)} simulated steps")

