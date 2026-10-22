"""macOS Platform Adapter for GDR-AI Device Mesh."""

from gdr.mesh.platform.base import BasePlatformAdapter


class MacOSPlatformAdapter(BasePlatformAdapter):
    """Adapter for Apple macOS systems."""

    def get_platform_name(self) -> str:
        return "macos"

