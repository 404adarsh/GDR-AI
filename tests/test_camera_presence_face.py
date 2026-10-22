"""Acceptance Test 11: Camera, Presence & Face Recognition.
Verifies:
1. Multi-sample face enrollment stores only embeddings (no photos).
2. Owner return triggers greeting by name on first sight of day.
3. Unknown person / stranger is greeted politely as unknown with prompt to remember.
4. Non-Auth Rule: Face recognition strictly does NOT unlock approvals or authorization.
5. Privacy mode stops camera capture immediately.
"""

import numpy as np
import pytest
from gdr.vision.camera import CameraVisionManager, FaceEmbeddingEngine
from gdr.safety.policy_engine import AutonomyPolicyEngine, ActionDecision


def test_acceptance_11_camera_face_recognition_and_non_auth(tmp_path):
    mgr = CameraVisionManager(config_dir=tmp_path)
    mgr.owner_name = "GDR"

    # 1. Create simulated face images for Owner (100x100 random noise with distinct center pattern)
    np.random.seed(42)
    owner_pattern = np.ones((100, 100, 3), dtype=np.uint8) * 128
    owner_pattern[30:70, 30:70, :] = 200  # distinct feature region
    samples = [
        owner_pattern + np.random.randint(-5, 5, (100, 100, 3), dtype=np.int16).clip(0, 255).astype(np.uint8)
        for _ in range(3)
    ]

    # Stranger face pattern (completely different distribution)
    stranger_pattern = np.zeros((100, 100, 3), dtype=np.uint8)
    stranger_pattern[10:50, 10:50, :] = 80

    # Enroll owner's face
    res = mgr.enroll_face("GDR", samples, is_owner=True)
    assert res["is_owner"] is True

    enrolled = mgr.list_enrolled_faces()
    assert len(enrolled) == 1
    assert enrolled[0]["name"] == "GDR"

    # Verify no raw photos stored, only embeddings
    raw_faces = mgr._load_faces()
    assert "embedding" in raw_faces["face_gdr"]
    assert len(raw_faces["face_gdr"]["embedding"]) == 128

    # 2. Owner returns: greeted by name on first sight
    owner_frame = samples[0]
    evt_owner = mgr.process_camera_event(owner_frame, activity_hint="coding")
    assert evt_owner["identification"]["identified"] is True
    assert evt_owner["identification"]["name"] == "GDR"
    assert "Welcome back, GDR" in evt_owner["spoken_message"]

    # 3. Stranger appears: greeted as unknown guest with prompt to remember
    evt_stranger = mgr.process_camera_event(stranger_pattern)
    assert evt_stranger["identification"]["identified"] is False
    assert evt_stranger["status"] == "unknown_visitor"
    assert "Hello, welcome. I'm GDR, GDR's assistant." in evt_stranger["spoken_message"]
    assert evt_stranger["identification"]["prompt_user_to_remember"] is True

    # 4. CRITICAL SAFETY TEST: Photo of owner held up to camera does NOT unlock approval
    # Even if identified as owner, is_authenticated_for_approvals must be FALSE
    assert evt_owner["identification"]["is_authenticated_for_approvals"] is False
    assert evt_owner["can_approve_sensitive_action"] is False

    # Verify policy engine still enforces ASK for sensitive actions despite face match
    policy = AutonomyPolicyEngine()
    card = policy.evaluate("send_payment", {"amount": 500, "camera_face_matched": True})
    # Sensitive action must NEVER be auto-approved by camera presence
    assert card.decision != ActionDecision.AUTO

    # 5. Test privacy mode toggle
    mgr.set_privacy_mode(True)
    assert mgr.privacy_mode is True
    evt_priv = mgr.process_camera_event(owner_frame)
    assert evt_priv["camera_active"] is False
    assert evt_priv["spoken_message"] is None

    print("\n--- Acceptance Test 11 Passed Output ---")
    print(f"Owner Greeting: {evt_owner['spoken_message']}")
    print(f"Stranger Greeting: {evt_stranger['spoken_message']}")
    print(f"Non-Auth Verification: can_approve={evt_owner['can_approve_sensitive_action']}")


def test_face_separation_and_no_false_positives(tmp_path):
    """Verify that a stranger's face does NOT trigger false positive match to owner."""
    mgr = CameraVisionManager(config_dir=tmp_path)
    mgr.owner_name = "GDR"

    # Owner face template
    np.random.seed(101)
    owner_img = np.ones((80, 80, 3), dtype=np.uint8) * 100
    owner_img[20:60, 20:60] = 220
    owner_samples = [owner_img + np.random.randint(-4, 4, (80, 80, 3), dtype=np.int16).clip(0, 255).astype(np.uint8) for _ in range(3)]
    mgr.enroll_face("GDR", owner_samples, is_owner=True)

    # Different person (Stranger) face template with different geometry
    stranger_img = np.zeros((80, 80, 3), dtype=np.uint8)
    stranger_img[10:35, 10:70] = 160
    stranger_img[45:75, 25:55] = 130

    emb_owner = FaceEmbeddingEngine.compute_embedding(owner_samples[0])
    emb_stranger = FaceEmbeddingEngine.compute_embedding(stranger_img)
    sim = FaceEmbeddingEngine.cosine_similarity(emb_owner, emb_stranger)

    # Cosine similarity must be well below the 0.82 threshold
    assert sim < 0.75, f"Stranger similarity too high: {sim}"

    # Identification test
    ident = mgr.identify_face(stranger_img)
    assert ident["identified"] is False
    assert ident["name"] == "Unknown"
    assert ident["similarity"] < 0.82


def test_owner_disappearance_and_reappearance_greeting(tmp_path):
    """Verify greeting upon reappearance after disappearing from camera."""
    mgr = CameraVisionManager(config_dir=tmp_path)
    mgr.owner_name = "GDR"
    mgr.disappearance_threshold_seconds = 0.5  # Fast test threshold

    owner_img = np.ones((64, 64, 3), dtype=np.uint8) * 150
    owner_img[20:50, 20:50] = 240
    mgr.enroll_face("GDR", [owner_img], is_owner=True)

    # 1. First sight of the day
    evt1 = mgr.process_camera_event(owner_img)
    assert "Ready for today" in evt1["spoken_message"]
    assert mgr.owner_present is True

    # 2. Owner disappears (empty/no owner frame after threshold)
    import time
    time.sleep(0.6)
    empty_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    evt2 = mgr.process_camera_event(empty_frame)
    assert mgr.owner_present is False
    assert mgr.disappeared_time is not None

    # 3. Owner returns after disappearing
    evt3 = mgr.process_camera_event(owner_img)
    assert mgr.owner_present is True
    assert "Welcome back, GDR! Good to see you again." in evt3["spoken_message"]


def test_guest_enrollment_memory_and_recognition(tmp_path):
    """Verify stranger face can be enrolled as a guest card and recognized on return."""
    mgr = CameraVisionManager(config_dir=tmp_path)
    mgr.owner_name = "GDR"

    # Guest face pattern
    guest_img = np.zeros((64, 64, 3), dtype=np.uint8)
    guest_img[15:45, 15:45] = 180
    guest_samples = [guest_img]

    # Register guest
    res = mgr.register_guest("Alice", guest_samples, notes="Friend visiting")
    assert res["name"] == "Alice"
    assert res["is_owner"] is False

    # Check memory DB
    from gdr.memory.store import MemoryStore
    mem = MemoryStore(tmp_path / "memory.db")
    recalled = mem.recall("Alice")
    assert len(recalled) > 0
    assert "Alice" in recalled[0]["content"]

    # When Alice appears in front of camera
    evt = mgr.process_camera_event(guest_img)
    assert evt["identification"]["identified"] is True
    assert evt["identification"]["name"] == "Alice"
    assert evt["identification"]["is_owner"] is False
    assert "Hello Alice, welcome back!" in evt["spoken_message"]


def test_multi_angle_enrollment_and_matching(tmp_path):
    """Verify that multi-angle enrollment matches poses even at side/tilt angles."""
    mgr = CameraVisionManager(config_dir=tmp_path)
    mgr.owner_name = "GDR"

    # 4 distinct angle images for Owner: Frontal, Left, Right, Tilt
    np.random.seed(202)
    frontal = np.ones((64, 64, 3), dtype=np.uint8) * 120
    frontal[20:45, 20:45] = 230

    left_turn = np.ones((64, 64, 3), dtype=np.uint8) * 120
    left_turn[20:45, 10:35] = 230  # shifted left

    right_turn = np.ones((64, 64, 3), dtype=np.uint8) * 120
    right_turn[20:45, 30:55] = 230  # shifted right

    tilt_up = np.ones((64, 64, 3), dtype=np.uint8) * 120
    tilt_up[10:35, 20:45] = 230  # shifted up

    samples = [frontal, left_turn, right_turn, tilt_up]
    res = mgr.enroll_face("GDR", samples, is_owner=True, notes="4-pose multi-angle")
    assert res["is_owner"] is True

    enrolled = mgr.list_enrolled_faces()
    assert enrolled[0]["angles_count"] == 4

    # Now simulate user turning head to the left (matching left_turn pose)
    left_query = left_turn + np.random.randint(-2, 2, (64, 64, 3), dtype=np.int16).clip(0, 255).astype(np.uint8)
    ident_left = mgr.identify_face(left_query)
    assert ident_left["identified"] is True
    assert ident_left["name"] == "GDR"
    assert ident_left["similarity"] >= 0.85

    # Simulate user tilting head up
    tilt_query = tilt_up + np.random.randint(-2, 2, (64, 64, 3), dtype=np.int16).clip(0, 255).astype(np.uint8)
    ident_tilt = mgr.identify_face(tilt_query)
    assert ident_tilt["identified"] is True
    assert ident_tilt["name"] == "GDR"
    assert ident_tilt["similarity"] >= 0.85


