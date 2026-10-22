"""Cross-Device Task Router and LLM Tools for GDR-AI Mesh."""

import asyncio
from typing import Dict, Any, List, Optional
from gdr.mesh.coordinator import get_mesh_coordinator
from gdr.tools.registry import tool


class MeshRouter:
    """Routes natural language queries and AI actions to appropriate mesh devices."""

    def __init__(self):
        self.coordinator = get_mesh_coordinator()

    def resolve_device_id(self, name_or_id: str) -> Optional[str]:
        """Resolve a device name, partial match, or alias to a canonical device ID."""
        target = name_or_id.lower().strip()
        if target in ("local", "laptop", "primary", "localhost", "this device", "host"):
            return "local_primary"

        devices = self.coordinator.list_devices()
        # Exact ID match
        for d in devices:
            if d["id"].lower() == target:
                return d["id"]

        # Exact Name match
        for d in devices:
            if d["name"].lower() == target:
                return d["id"]

        # Partial Name or Platform match
        for d in devices:
            if target in d["name"].lower() or target in d["platform"].lower():
                return d["id"]

        return None

    async def search_all_devices(self, query: str, target_device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search approved folders across all online devices simultaneously."""
        devices = self.coordinator.list_devices()
        targets = []
        if target_device_id:
            resolved = self.resolve_device_id(target_device_id)
            if resolved:
                targets = [d for d in devices if d["id"] == resolved]
        else:
            targets = [d for d in devices if d["status"] == "online"]

        if not targets:
            return []

        coros = [
            self.coordinator.dispatch_task(d["id"], "file_search", {"query": query})
            for d in targets
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        combined: List[Dict[str, Any]] = []
        for d, res in zip(targets, results):
            if isinstance(res, dict) and res.get("success"):
                files = res.get("result") or []
                for f in files:
                    f["device_id"] = d["id"]
                    f["device_name"] = d["name"]
                    f["device_platform"] = d["platform"]
                    combined.append(f)
        return combined


_ROUTER: Optional[MeshRouter] = None


def get_mesh_router() -> MeshRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = MeshRouter()
    return _ROUTER


# ==============================================================================
# Registered Tools for GDR-AI Agent
# ==============================================================================

@tool(
    name="mesh_list_devices",
    description="List all devices connected to your GDR-AI Multi-Device Mesh (Android phones via Termux, Linux laptops, Windows/Mac PCs) with live status, battery, and platform info.",
    category="system",
    tier="AUTO"
)
def mesh_list_devices() -> str:
    """Return formatted list of all enrolled mesh devices."""
    coord = get_mesh_coordinator()
    devices = coord.list_devices()
    if not devices:
        return "No devices currently enrolled in Device Mesh."

    lines = ["📱 Connected Mesh Devices:"]
    for d in devices:
        st_icon = "🟢" if d["status"] == "online" else "⚪"
        bat = d.get("battery", {})
        bat_str = f" | Battery: {bat.get('percentage')}%" if bat.get("percentage") is not None else ""
        lines.append(f"• {st_icon} {d['name']} ({d['platform'].capitalize()}) [ID: {d['id']}] — {d['status'].upper()}{bat_str}")
    return "\n".join(lines)


@tool(
    name="mesh_get_device_status",
    description="Get CPU, RAM, disk space, battery, and uptime diagnostics for a specific mesh device (e.g. 'laptop', 'phone', or device ID).",
    category="system",
    tier="AUTO"
)
def mesh_get_device_status(device_name_or_id: str = "local_primary") -> str:
    """Retrieve system diagnostics from target device."""
    router = get_mesh_router()
    dev_id = router.resolve_device_id(device_name_or_id)
    if not dev_id:
        return f"Device '{device_name_or_id}' was not found in the mesh. Run mesh_list_devices to see available nodes."

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(
        router.coordinator.dispatch_task(dev_id, "sys_info", {})
    )

    if not res.get("success"):
        return f"Failed to retrieve status from {device_name_or_id}: {res.get('error')}"

    info = res.get("result", {})
    return (
        f"📊 Diagnostics for {device_name_or_id} ({info.get('platform', '').capitalize()}):\n"
        f"• CPU Usage   : {info.get('cpu_percent', 0)}%\n"
        f"• RAM Usage   : {info.get('ram_percent', 0)}% ({info.get('ram_free_gb', 0)} GB available of {info.get('ram_total_gb', 0)} GB)\n"
        f"• Disk Free   : {info.get('disk_free_gb', 0)} GB (Total {info.get('disk_total_gb', 0)} GB)\n"
        f"• Hostname    : {info.get('hostname')}\n"
        f"• Architecture: {info.get('architecture')}"
    )


@tool(
    name="mesh_search_files",
    description="Search approved files (Documents, Downloads) across one or all connected devices in your mesh.",
    category="files",
    tier="AUTO"
)
def mesh_search_files(query: str, device_name_or_id: Optional[str] = None) -> str:
    """Search files across connected mesh nodes."""
    router = get_mesh_router()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    files = loop.run_until_complete(
        router.search_all_devices(query, target_device_id=device_name_or_id)
    )

    if not files:
        target_str = f" on '{device_name_or_id}'" if device_name_or_id else " across all connected devices"
        return f"No files matching '{query}' found{target_str}."

    lines = [f"🔍 Found {len(files)} matching file(s):"]
    for f in files[:15]:
        size_kb = round(f.get("size_bytes", 0) / 1024, 1)
        lines.append(f"• [{f['device_name']}] {f['filename']} ({size_kb} KB) — Path: {f['path']}")
    return "\n".join(lines)


@tool(
    name="mesh_read_file",
    description="Read content of an approved text file from a specific device in the mesh.",
    category="files",
    tier="APPROVAL"
)
def mesh_read_file(device_name_or_id: str, file_path: str) -> str:
    """Read a document from a remote or local mesh device."""
    router = get_mesh_router()
    dev_id = router.resolve_device_id(device_name_or_id)
    if not dev_id:
        return f"Device '{device_name_or_id}' not found."

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(
        router.coordinator.dispatch_task(dev_id, "file_read", {"path": file_path})
    )

    if not res.get("success"):
        return f"Failed to read file from {device_name_or_id}: {res.get('error')}"

    content = res.get("result", "")
    preview = content[:2500]
    suffix = f"\n\n... [Truncated {len(content) - 2500} bytes]" if len(content) > 2500 else ""
    return f"📄 Content of '{file_path}' from {device_name_or_id}:\n\n{preview}{suffix}"


@tool(
    name="mesh_execute_command",
    description="Execute an authorized command or script on a remote mesh device (e.g. Termux, remote Linux/Mac/Windows PC). Requires APPROVAL.",
    category="system",
    tier="APPROVAL",
    requires_approval=True
)
def mesh_execute_command(device_name_or_id: str, command: str) -> str:
    """Execute command on a target device with safety checks and timeout."""
    router = get_mesh_router()
    dev_id = router.resolve_device_id(device_name_or_id)
    if not dev_id:
        return f"Device '{device_name_or_id}' was not found in the mesh."

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(
        router.coordinator.dispatch_task(dev_id, "terminal.execute", {"command": command}, approved=True)
    )

    if not res.get("success"):
        return f"❌ Execution failed on {device_name_or_id}: {res.get('error')}"

    output = res.get("result", "")
    return f"💻 Output from {device_name_or_id}:\n```\n{output}\n```"


@tool(
    name="mesh_send_notification",
    description="Display a notification toast or alert on a connected mesh device (e.g. phone via Termux or remote laptop).",
    category="system",
    tier="AUTO"
)
def mesh_send_notification(device_name_or_id: str, title: str, message: str) -> str:
    """Send notification to target mesh device."""
    router = get_mesh_router()
    dev_id = router.resolve_device_id(device_name_or_id)
    if not dev_id:
        return f"Device '{device_name_or_id}' was not found in the mesh."

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(
        router.coordinator.dispatch_task(dev_id, "notifications.send", {"title": title, "message": message})
    )

    if not res.get("success"):
        return f"Failed to send notification: {res.get('error')}"
    return f"✅ Notification sent to {device_name_or_id}: '{title}: {message}'"


@tool(
    name="mesh_panic_kill",
    description="Emergency Stop: Immediately abort all in-flight cross-device mesh tasks and broadcast emergency kill to all connected nodes.",
    category="system",
    tier="AUTO"
)
def mesh_panic_kill() -> str:
    """Trigger emergency stop across all devices in the mesh."""
    coord = get_mesh_coordinator()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    res = loop.run_until_complete(coord.panic_kill_all())
    return f"🚨 {res['message']}"

