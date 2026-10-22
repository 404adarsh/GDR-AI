"""Acceptance tests for Phase 8 & Phase 8B:
- 8b-1: Heavy-Interactive 30B MoE generation with VRAM < 3.8 GB.
- 8b-2: Slow-Lane checkpointing and resume.
- 8b-3: Hardware guards prevent VRAM/RAM exhaustion.
- Privacy Router classification & failover to lite mode.
"""

import json
from pathlib import Path
import pytest

from gdr.models.budget import get_budget_manager, MAX_VRAM_MIB, MIN_FREE_RAM_MIB
from gdr.models.manager import LocalModelManager, CHECKPOINT_DIR
from gdr.models.router import PrivacyRouter, ModelRouter
from gdr.models.benchmark import run_model_benchmarks


def test_8b1_heavy_moe_lane_vram_limit(monkeypatch):
    psutil = pytest.importorskip("psutil", reason="psutil not installed")
    from unittest.mock import MagicMock
    monkeypatch.setattr(psutil, "virtual_memory", lambda: MagicMock(available=8 * 1024 * 1024 * 1024))

    mgr = LocalModelManager()
    res = mgr.generate("Analyze the system architecture in detail", lane="LANE_2_HEAVY_INTERACTIVE")
    assert res.lane == "LANE_2_HEAVY_INTERACTIVE"
    assert res.peak_vram_mib < MAX_VRAM_MIB, f"VRAM exceeded limit: {res.peak_vram_mib} >= {MAX_VRAM_MIB}"
    assert "Heavy MoE" in res.text
    print(f"\n[8B-1] Heavy MoE TPS: {res.tokens_per_second:.1f}, VRAM: {res.peak_vram_mib} MiB")


def test_8b2_slow_lane_checkpoint_and_resume(tmp_path, monkeypatch):
    import gdr.models.manager as mgr_mod
    test_ckpt_dir = tmp_path / "layer_checkpoints"
    monkeypatch.setattr(mgr_mod, "CHECKPOINT_DIR", test_ckpt_dir)

    mgr = LocalModelManager()
    cid = f"test_resume_job_{int(time_now := 123456)}"
    ckpt_file = test_ckpt_dir / f"{cid}.json"

    # 1. Create artificial mid-run checkpoint at layer 24 of 48
    test_ckpt_dir.mkdir(parents=True, exist_ok=True)
    with open(ckpt_file, "w") as f:
        json.dump({"checkpoint_id": cid, "prompt": "test dense job", "current_layer": 24, "total_layers": 48}, f)

    assert ckpt_file.exists()

    # 2. Resume job
    res = mgr.generate("test dense job", lane="LANE_3_SLOW_BATCH", resume_checkpoint_id=cid)
    assert res.lane == "LANE_3_SLOW_BATCH"
    assert "Dense-30B" in res.text
    # Verify completed job cleaned up checkpoint
    assert not ckpt_file.exists()
    print(f"\n[8B-2] Resumed and completed layer streaming job '{cid}' successfully.")


def test_8b3_memory_and_thermal_guards(monkeypatch):
    psutil = pytest.importorskip("psutil", reason="psutil not installed")
    from unittest.mock import MagicMock
    monkeypatch.setattr(psutil, "virtual_memory", lambda: MagicMock(available=8 * 1024 * 1024 * 1024))

    budget = get_budget_manager()

    # 1. Test VRAM ceiling rejection
    can_load, reason = budget.can_load_gpu_model(required_vram_mib=5000)
    assert not can_load
    assert "budget exceeded" in reason.lower()

    # 2. Test Single Heavy Model GPU lock
    budget.register_loaded_model("Model_A", "LANE_2")
    can_load_second, second_reason = budget.can_load_gpu_model(required_vram_mib=1000)
    assert not can_load_second
    assert "Single-model constraint" in second_reason

    # Clean up lock
    budget.unload_active_model()
    assert budget.active_gpu_model is None


def test_privacy_router_and_failover():
    # 1. Test private classification
    is_priv, r1 = PrivacyRouter.is_private_content("Here is my secret bank balance and email password")
    assert is_priv

    is_pub, r2 = PrivacyRouter.is_private_content("What is the speed of light in vacuum?")
    assert not is_pub

    # 2. Test failover on cloud error
    router = ModelRouter()

    def failing_cloud_call(p):
        raise RuntimeError("HTTP 429: Rate limit quota exceeded")

    reply, meta = router.route_and_generate("General search query", failing_cloud_call)
    assert "lite mode" in reply.lower()
    assert meta["provider"] == "local_failover"
    assert meta["lane"] == "LANE_1_FAST"
    print(f"\n[Privacy Router] Successfully triggered failover to lite mode: '{reply[:60]}...'")


def test_bench_models():
    results = run_model_benchmarks()
    assert len(results) == 4
    for r in results:
        assert r.peak_vram_mib <= MAX_VRAM_MIB
        assert r.gen_tps > 0
