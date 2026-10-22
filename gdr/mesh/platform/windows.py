"""Windows Platform Adapter for GDR-AI Device Mesh."""

from gdr.mesh.platform.base import BasePlatformAdapter


class WindowsPlatformAdapter(BasePlatformAdapter):
    """Adapter for Microsoft Windows 10/11 desktops and laptops."""

    def get_platform_name(self) -> str:
        return "windows"

