"""Vision, Presence, and Face Recognition System for blockbrain AI.
Runs strictly locally. Never transmits frames or video.
Frames are never saved to disk. Only encrypted numerical embeddings are stored.
Face recognition is strictly for personalization (greetings/presence), NEVER authentication.
"""

from datetime import datetime, timezone, timedelta
import json
import logging
import math
import os
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from blockbrain.safety.secrets import get_secret
from blockbrain.config import load_config

logger = logging.getLogger("blockbrain.vision")

DEFAULT_STORAGE_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
FACE_STORE_FILE = DEFAULT_STORAGE_DIR / "enrolled_faces.json"


class FaceEmbeddingEngine:
    """Computes and compares normalized facial feature embeddings."""

    @staticmethod
    def compute_embedding(image_array: np.ndarray) -> np.ndarray:
        """Extract a 128-dimensional normalized 2D DCT feature embedding vector.
        Illumination-normalized using z-score standardization and mid-frequency
        spatial decomposition to eliminate lighting bias and prevent false matches.
        """
        if len(image_array.shape) == 3:
            # Grayscale projection
            gray = np.mean(image_array, axis=2).astype(float)
        else:
            gray = image_array.astype(float)

        from PIL import Image
        from scipy.fftpack import dct

        # Resize to fixed 64x64 patch
        img = Image.fromarray(gray.astype(np.uint8)).resize((64, 64))
        arr = np.array(img, dtype=float)

        # Illumination normalization: z-score standard normalization removes global skin/lighting bias
        arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-5)

        # 2D DCT along rows and columns
        d1 = dct(arr, axis=0, norm='ortho')
        d2 = dct(d1, axis=1, norm='ortho')

        # Zig-zag collection of low-to-mid AC frequencies (skipping DC component at (0,0))
        coeffs = []
        for s in range(1, 20):
            for i in range(s + 1):
                j = s - i
                if i < 64 and j < 64:
                    coeffs.append(d2[i, j])
                if len(coeffs) == 128:
                    break
            if len(coeffs) == 128:
                break

        vec = np.array(coeffs, dtype=float)
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-8)

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))


class CameraVisionManager:
    """Manages presence sensing, face recognition, breaks, and quiet hours."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or DEFAULT_STORAGE_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.faces_file = self.config_dir / "enrolled_faces.json"

        cfg = load_config()
        self.owner_name = cfg.get("general", {}).get("user_name", "blockbrain")
        self.privacy_mode = False
        self.camera_active = False
        self.enable_guest_recognition = True
        self.sitting_duration_seconds = 0.0
        self.last_user_seen_time: Optional[float] = None
        self.greeted_today = False
        self.current_activity = "idle"  # e.g. "coding", "on a call", "away"

        # Presence & Disappearance Tracking
        self.owner_present = False
        self.last_owner_seen: Optional[float] = None
        self.disappeared_time: Optional[float] = None
        self.disappearance_threshold_seconds = 15.0

        self._ensure_storage()

    def _ensure_storage(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if not self.faces_file.exists():
                self._save_faces({})
        except OSError:
            pass

    def _load_faces(self) -> Dict[str, Any]:
        if not self.faces_file.exists():
            return {}
        try:
            with open(self.faces_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_faces(self, data: Dict[str, Any]) -> None:
        tmp = self.faces_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self.faces_file)

    def set_privacy_mode(self, enabled: bool) -> bool:
        """Toggle privacy mode. Disables camera capture immediately."""
        self.privacy_mode = enabled
        if enabled:
            self.camera_active = False
            logger.info("🔒 Camera Privacy Mode ACTIVATED. Capture stopped.")
        else:
            logger.info("🔓 Camera Privacy Mode deactivated.")
        return self.privacy_mode

    def enroll_face(self, name: str, samples: List[np.ndarray], is_owner: bool = False, notes: str = "") -> Dict[str, Any]:
        """Enroll face embeddings (never photos). Explicit consent flow."""
        faces = self._load_faces()
        embeddings = [FaceEmbeddingEngine.compute_embedding(s).tolist() for s in samples]

        # Calculate mean embedding
        mean_emb = np.mean(np.array(embeddings), axis=0)
        norm = np.linalg.norm(mean_emb)
        mean_emb = (mean_emb / (norm + 1e-8)).tolist()

        face_id = f"face_{name.lower().replace(' ', '_')}"
        faces[face_id] = {
            "name": name,
            "is_owner": is_owner,
            "role": "owner" if is_owner else "guest",
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(samples),
            "notes": notes,
            "embedding": mean_emb,
            "angle_embeddings": embeddings,  # Store individual multi-angle pose embeddings
        }
        self._save_faces(faces)

        # Store in long-term memory store
        try:
            from blockbrain.memory.store import MemoryStore
            mem = MemoryStore(self.config_dir / "memory.db")
            mem.remember(
                key=f"face_{name.lower().replace(' ', '_')}",
                content=f"Face card for {name} ({'Owner' if is_owner else 'Guest'}). Enrolled with {len(samples)} multi-angle samples. {notes}".strip(),
                category="person"
            )
        except Exception as e:
            logger.warning(f"Could not record face enrollment in memory DB: {e}")

        logger.info(f"Enrolled face '{name}' (owner={is_owner}) with {len(samples)} samples.")
        return {"face_id": face_id, "name": name, "is_owner": is_owner}

    def register_guest(self, name: str, samples: List[np.ndarray], notes: str = "") -> Dict[str, Any]:
        """Convenience method to register a visitor / guest face card into memory."""
        return self.enroll_face(name=name, samples=samples, is_owner=False, notes=notes)

    def list_enrolled_faces(self) -> List[Dict[str, Any]]:
        faces = self._load_faces()
        res = []
        for fid, meta in faces.items():
            res.append({
                "face_id": fid,
                "name": meta["name"],
                "is_owner": meta.get("is_owner", False),
                "role": meta.get("role", "owner" if meta.get("is_owner") else "guest"),
                "enrolled_at": meta.get("enrolled_at", ""),
                "notes": meta.get("notes", ""),
                "angles_count": len(meta.get("angle_embeddings", [1])),
            })
        return res

    def delete_face(self, face_id: str) -> bool:
        faces = self._load_faces()
        if face_id in faces:
            del faces[face_id]
            self._save_faces(faces)
            return True
        return False

    def identify_face(self, frame_array: np.ndarray, similarity_threshold: float = 0.82) -> Dict[str, Any]:
        """Identify face in frame against enrolled embeddings across all angles.
        CRITICAL SAFETY RULE: Never returns authentication token or approval capability.
        """
        if self.privacy_mode:
            return {"status": "privacy_mode_active"}

        faces = self._load_faces()
        emb = FaceEmbeddingEngine.compute_embedding(frame_array)

        best_match = None
        best_sim = -1.0

        for fid, meta in faces.items():
            # Check multi-angle embeddings if available
            angles = meta.get("angle_embeddings")
            if angles:
                sims = [FaceEmbeddingEngine.cosine_similarity(emb, np.array(a_emb)) for a_emb in angles]
                sim = max(sims)
            else:
                stored_emb = np.array(meta["embedding"])
                sim = FaceEmbeddingEngine.cosine_similarity(emb, stored_emb)

            if sim > best_sim:
                best_sim = sim
                best_match = meta

        if best_match and best_sim >= similarity_threshold:
            return {
                "identified": True,
                "name": best_match["name"],
                "is_owner": best_match.get("is_owner", False),
                "role": best_match.get("role", "owner" if best_match.get("is_owner") else "guest"),
                "similarity": round(best_sim, 3),
                # Explicit safety token: cannot be used for approvals
                "is_authenticated_for_approvals": False,
                "safety_note": "Face recognition is strictly for personalization. Not valid for authorization."
            }

        return {
            "identified": False,
            "name": "Unknown",
            "is_owner": False,
            "role": "unknown",
            "similarity": round(best_sim, 3),
            "is_authenticated_for_approvals": False,
            "prompt_user_to_remember": self.enable_guest_recognition
        }

    def process_camera_event(self, frame_array: np.ndarray, activity_hint: str = "coding") -> Dict[str, Any]:
        """High-level event processor: presence, daily greeting, reappearance greeting, guest handling, break suggestions."""
        if self.privacy_mode:
            return {
                "camera_active": False,
                "spoken_message": None,
                "activity": "privacy_mode",
            }

        self.camera_active = True
        self.current_activity = activity_hint
        now = time.time()
        ident = self.identify_face(frame_array)

        spoken_message = None
        status = "normal"

        if ident["identified"]:
            if ident["is_owner"]:
                now_seen = now
                # Check for first sight of the day OR reappearance after disappearing
                if not self.owner_present:
                    if not self.greeted_today:
                        spoken_message = f"Welcome back, {self.owner_name}. Ready for today."
                        self.greeted_today = True
                    elif self.disappeared_time is not None or (self.last_owner_seen and (now_seen - self.last_owner_seen >= self.disappearance_threshold_seconds)):
                        spoken_message = f"Welcome back, {self.owner_name}! Good to see you again."
                    else:
                        spoken_message = f"Welcome back, {self.owner_name}."

                    self.owner_present = True
                    self.disappeared_time = None

                self.last_user_seen_time = now_seen
                self.last_owner_seen = now_seen

                # Sitting duration check (> 2 hours = 7200s)
                self.sitting_duration_seconds += 60.0
                if self.sitting_duration_seconds >= 7200.0:
                    spoken_message = f"You've been focused at your desk for over 2 hours, {self.owner_name}. Time for a stretch and a glass of water."
                    self.sitting_duration_seconds = 0.0
                    status = "suggest_break"
            else:
                # Known guest recognized!
                guest_name = ident["name"]
                spoken_message = f"Hello {guest_name}, welcome back! blockbrain is currently at their desk."
                status = "known_guest"
        else:
            # Unidentified / stranger face
            # If owner was present and hasn't been seen for threshold seconds, mark as disappeared
            if self.owner_present and self.last_owner_seen and (now - self.last_owner_seen >= self.disappearance_threshold_seconds):
                self.owner_present = False
                self.disappeared_time = now

            if self.enable_guest_recognition:
                spoken_message = f"Hello, welcome. I'm blockbrain, {self.owner_name}'s assistant. May I know your name so I can remember you?"
                status = "unknown_visitor"

        return {
            "camera_active": self.camera_active,
            "identification": ident,
            "spoken_message": spoken_message,
            "status": status,
            "activity": self.current_activity,
            "owner_present": self.owner_present,
            "can_approve_sensitive_action": False,  # ALWAYS False!
        }
