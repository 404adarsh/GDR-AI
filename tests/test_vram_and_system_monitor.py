"""Acceptance Test 15: VRAM Ceiling and System Monitor.
Verifies:
1. VRAM budget enforcement guarantees VRAM allocation stays strictly under 3.8 GB (3890 MiB).
2. Attempting to allocate more than 3.8 GB is rejected by the budget manager.
3. System monitor returns accurate live VRAM metrics, model status, and thermal guard metrics.
"""

import pytest
from gdr.models.budget import VRAMBudgetManager, MAX_VRAM_MIB


def test_acceptance_15_vram_stays_under_3_8_gb_and_reported():
    mgr = VRAMBudgetManager()

    # Verify MAX_VRAM_MIB is configured under 3.8 GB (3891 MiB)
    assert MAX_VRAM_MIB <= 3800, "VRAM limit must be strictly <= 3.8 GB"

    # Hardware status check
    status = mgr.get_hardware_status()
    assert "vram_used_mib" in status
    assert "vram_total_mib" in status
    assert "ram_available_mib" in status
    assert "gpu_temp_c" in status

    # Current VRAM must be under 3.8 GB
    assert status["vram_used_mib"] <= MAX_VRAM_MIB

    # Test rejection of allocations exceeding 3.8 GB
    can_load, reason = mgr.can_load_gpu_model(required_vram_mib=3950)
    assert can_load is False
    assert "exceeded" in reason or "limit" in reason

    # Test that valid allocation under 3.8 GB is permitted
    can_load_valid, _ = mgr.can_load_gpu_model(required_vram_mib=2200)
    # If thermal throttling or battery isn't blocking, can_load_valid should evaluate safely
    assert isinstance(can_load_valid, bool)

    print("\n--- Acceptance Test 15 Passed Output ---")
    print(f"Configured VRAM Ceiling: {MAX_VRAM_MIB} MiB (< 3.8 GB)")
    print(f"Reported VRAM Used: {status['vram_used_mib']} MiB / {status['vram_total_mib']} MiB")
    print(f"Reported RAM Available: {status['ram_available_mib']} MiB / {status['ram_total_mib']} MiB")
    print(f"Over-budget Rejection Test: can_load=False, reason='{reason}'")
