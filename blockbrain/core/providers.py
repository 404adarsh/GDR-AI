"""LLM Provider abstraction for blockbrain AI.
Default provider is Sarvam AI (sarvam-105b), with optional Ollama, Claude, and OpenAI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import os
from typing import List, Dict, Any, Optional

from blockbrain.safety.secrets import get_secret
from blockbrain.safety.limits import record_cost
from blockbrain.config import load_config


@dataclass
class ToolCall:
    id: str
    name: str
    args: Dict[str, Any]


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        pass


class SarvamProvider(BaseLLMProvider):
    def __init__(self, model: str = "sarvam-105b", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or get_secret("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is not set.")
        from sarvamai import SarvamAI
        self.client = SarvamAI(api_subscription_key=self.api_key)

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.chat.completions(**kwargs)
        choice = resp.choices[0]
        msg = choice.message

        tool_calls = []
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                call_id = getattr(tc, "id", f"call_{len(tool_calls)}")
                fn = tc.function
                fn_name = fn.name
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                except Exception:
                    args = {}
                tool_calls.append(ToolCall(id=call_id, name=fn_name, args=args))

        # Record usage
        p_tokens = getattr(resp.usage, "prompt_tokens", 0) if hasattr(resp, "usage") else 0
        c_tokens = getattr(resp.usage, "completion_tokens", 0) if hasattr(resp, "usage") else 0
        est_cost = (p_tokens * 0.0002 + c_tokens * 0.0006) / 1000.0
        record_cost("sarvam-105b", est_cost, tokens=p_tokens + c_tokens)

        return LLMResponse(
            content=getattr(msg, "content", ""),
            tool_calls=tool_calls,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            model=self.model,
        )


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        import requests
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=60)
        data = resp.json()
        msg = data.get("message", {})

        tool_calls = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(ToolCall(
                id=f"ollama_{len(tool_calls)}",
                name=fn.get("name", ""),
                args=fn.get("arguments", {})
            ))

        return LLMResponse(
            content=msg.get("content", ""),
            tool_calls=tool_calls,
            model=self.model
        )


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or get_secret("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        import httpx
        # Format messages for Anthropic
        system_prompt = "You are blockbrain AI, a Jarvis-style Linux assistant."
        user_msgs = []
        for m in messages:
            if m.get("role") == "system":
                system_prompt = m.get("content", "")
            else:
                user_msgs.append(m)

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": user_msgs,
        }
        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "input_schema": fn.get("parameters"),
                })
            payload["tools"] = anthropic_tools

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json=payload,
            timeout=60.0
        )
        data = resp.json()
        content = ""
        tool_calls = []
        for item in data.get("content", []):
            if item.get("type") == "text":
                content += item.get("text", "")
            elif item.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=item.get("id"),
                    name=item.get("name"),
                    args=item.get("input", {})
                ))

        return LLMResponse(content=content, tool_calls=tool_calls, model=self.model)


class OfflineLocalProvider(BaseLLMProvider):
    """Offline Local LLM Provider for blockbrain AI.
    Executes 100% locally on CPU / RTX 3050 without requiring internet connectivity.
    Supports tool dispatching and conversational Jarvis intelligence.
    """
    def __init__(self, model: str = "local-offline-qwen"):
        self.model = model
        self._local_manager = None

    @property
    def local_manager(self):
        if self._local_manager is None:
            from blockbrain.models.manager import LocalModelManager
            self._local_manager = LocalModelManager()
        return self._local_manager

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        import socket
        # 1. Try local Ollama if running on localhost:11434
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.15)
            sock.connect(("127.0.0.1", 11434))
            sock.close()
            return OllamaProvider().chat(messages, tools)
        except Exception:
            pass

        # 2. Extract conversation context
        last_msg = messages[-1] if messages else {}
        last_role = last_msg.get("role", "")
        last_content = str(last_msg.get("content", ""))

        # 2a. If last message was a tool result, synthesize final assistant answer
        if last_role == "tool":
            tool_content = last_content
            # Find the user's initial question
            user_prompt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_prompt = str(m.get("content", ""))
                    break

            summary = f"[Offline Local AI Mode]\n{tool_content}"
            if "opened" in tool_content.lower() or "youtube" in user_prompt.lower():
                summary = f"[Offline Local AI Mode] ✅ I have executed your request on the desktop screen:\n{tool_content}"
            elif "hardware" in tool_content.lower() or "volume" in user_prompt.lower() or "brightness" in user_prompt.lower():
                summary = f"[Offline Local AI Mode] ✅ Hardware settings updated:\n{tool_content}"
            elif "ping" in user_prompt.lower():
                summary = f"[Offline Local AI Mode] 🌐 Network ping diagnostics:\n{tool_content}"

            return LLMResponse(content=summary, tool_calls=[], model=self.model)

        # 2b. If last message is from user, check for intent requiring tool execution
        user_text = last_content.strip()
        low = user_text.lower()
        tool_calls: List[ToolCall] = []

        # Check: YouTube & Video playback
        if "youtube" in low:
            song = user_text
            for prefix in ["open youtube and search for", "open youtube and search", "search youtube for", "open youtube", "search youtube", "play on youtube", "play"]:
                if prefix in low:
                    idx = low.find(prefix) + len(prefix)
                    song = user_text[idx:].strip(" :,-")
                    break
            if not song:
                song = "lofi hip hop radio"
            tool_calls.append(ToolCall(
                id="offline_call_yt",
                name="open_youtube",
                args={"query": song}
            ))

        # Check: Open Desktop Application or Website
        elif any(low.startswith(p) for p in ["open ", "launch ", "browse "]):
            target = user_text.split(maxsplit=1)[1].strip()
            tool_calls.append(ToolCall(
                id="offline_call_open",
                name="desktop_open",
                args={"target": target}
            ))

        # Check: Live Screen Vision & Inspection
        elif any(k in low for k in ["see screen", "look at screen", "read screen", "screenshot", "what is on my screen", "check screen", "inspect screen"]):
            tool_calls.append(ToolCall(
                id="offline_call_screen",
                name="see_screen",
                args={"question": user_text}
            ))

        # Check: Volume, Mic, Audio & Speaker Hardware Controls
        elif any(k in low for k in ["volume", "sound", "mute", "dummy", "speaker", "audio", "mic", "microphone", "awaaz", "awaz"]):
            if any(k in low for k in ["dummy", "fix", "repair", "restore", "not working", "real sound", "real mic", "main one", "alsa", "broken", "issue"]):
                tool_calls.append(ToolCall(id="offline_call_vol", name="control_hardware", args={"action": "fix", "device": "sound", "value": "restore"}))
            elif "mute" in low:
                tool_calls.append(ToolCall(id="offline_call_vol", name="control_hardware", args={"action": "mute", "device": "volume"}))
            elif any(k in low for k in ["up", "increase", "raise", "louder", "boost"]):
                tool_calls.append(ToolCall(id="offline_call_vol", name="control_hardware", args={"action": "up", "device": "volume", "value": "10%"}))
            elif any(k in low for k in ["down", "decrease", "lower", "quieter"]):
                tool_calls.append(ToolCall(id="offline_call_vol", name="control_hardware", args={"action": "down", "device": "volume", "value": "10%"}))
            elif "%" in low:
                match = re.search(r"(\d+)%", low)
                val = f"{match.group(1)}%" if match else "75%"
                tool_calls.append(ToolCall(id="offline_call_vol", name="control_hardware", args={"action": "set", "device": "volume", "value": val}))
            else:
                tool_calls.append(ToolCall(id="offline_call_vol", name="get_volume", args={}))

        # Check: Brightness Controls
        elif "brightness" in low:
            if any(k in low for k in ["up", "increase", "higher"]):
                tool_calls.append(ToolCall(id="offline_call_bri", name="control_hardware", args={"action": "up", "device": "brightness", "value": "10%"}))
            elif any(k in low for k in ["down", "decrease", "lower"]):
                tool_calls.append(ToolCall(id="offline_call_bri", name="control_hardware", args={"action": "down", "device": "brightness", "value": "10%"}))
            elif "%" in low:
                match = re.search(r"(\d+)%", low)
                val = f"{match.group(1)}%" if match else "80%"
                tool_calls.append(ToolCall(id="offline_call_bri", name="control_hardware", args={"action": "set", "device": "brightness", "value": val}))

        # Check: Ping / Network diagnostics
        elif low.startswith("ping ") or "ping host" in low:
            match = re.search(r"ping\s+([a-zA-Z0-9\.\-]+)", low)
            host = match.group(1) if match else "127.0.0.1"
            tool_calls.append(ToolCall(id="offline_call_ping", name="ping_host", args={"host": host}))

        # Check: Website Test
        elif "test website" in low or "ping website" in low or "check website" in low:
            match = re.search(r"https?://\S+", user_text)
            url = match.group(0) if match else "https://google.com"
            tool_calls.append(ToolCall(id="offline_call_tw", name="test_website", args={"url": url}))

        # Check: Bookmarks
        elif "bookmark" in low or "save website" in low:
            parts = user_text.split()
            url = next((w for w in parts if "http" in w or "." in w), "https://google.com")
            name = parts[1] if len(parts) > 1 else "site"
            tool_calls.append(ToolCall(id="offline_call_bm", name="bookmark_website", args={"name": name, "url": url}))

        # Check: Sudo / Root execution
        elif low.startswith("sudo ") or "run sudo" in low:
            cmd = user_text.replace("run sudo", "").replace("sudo", "").strip()
            tool_calls.append(ToolCall(id="offline_call_sudo", name="run_sudo", args={"command": cmd}))

        # Check: Location
        elif "location" in low or "where am i" in low:
            tool_calls.append(ToolCall(id="offline_call_loc", name="get_current_location", args={}))

        # Check: Weather
        elif "weather" in low or "forecast" in low or "temperature" in low:
            tool_calls.append(ToolCall(id="offline_call_wth", name="get_weather", args={"location": ""}))

        if tool_calls:
            return LLMResponse(content="", tool_calls=tool_calls, model=self.model)

        # 2c. Pure Conversational / Reasoning replies (Song, Time, System Info, General Chat)
        from datetime import datetime
        if any(k in low for k in ["sing", "song", "rhyme", "poem", "melody", "gaana", "geet"]):
            content = (
                "♪ Twinkle, twinkle, little star,\n"
                "How I wonder what you are!\n"
                "Up above the world so high,\n"
                "Like a diamond in the sky.\n"
                "When the blazing sun is gone,\n"
                "When he nothing shines upon,\n"
                "Then you show your little light,\n"
                "Twinkle, twinkle, all the night! ♪\n\n"
                "I am singing for you using offline neural voice. I can also open YouTube to play the real track on your desktop screen if you like."
            )
            return LLMResponse(content=content, tool_calls=[], model=self.model)

        if any(k in low for k in ["time", "date", "clock", "samay", "tareekh"]):
            content = f"[Offline Local AI Mode] The current time is {datetime.now().strftime('%I:%M %p, %A, %B %d, %Y')}."
            return LLMResponse(content=content, tool_calls=[], model=self.model)

        # Check: Memory Recall / What do you know about me?
        if any(k in low for k in ["what do you know about me", "what have you learned", "do you remember me", "who am i", "my preferences", "what i like", "kya jaante ho mere baare mein", "tell me about myself"]):
            from blockbrain.memory.store import get_memory_store
            store = get_memory_store()
            mems = store.list_all()
            if not mems:
                content = (
                    "You are my creator and teacher! I am constantly listening and learning from you like a child. "
                    "Tell me about your favorite things, habits, or projects, and I will remember every small detail."
                )
            else:
                lines = ["Here is everything I have learned from you so far:"]
                for m in mems:
                    lines.append(f"• {m['key'].replace('_', ' ').capitalize()}: {m['content']}")
                lines.append("\nI'm always learning from your style, words, and guidance!")
                content = "\n".join(lines)
            return LLMResponse(content=content, tool_calls=[], model=self.model)

        # Check: Did the user just teach something?
        from blockbrain.memory.store import get_memory_store
        store = get_memory_store()
        learned = store.auto_learn_from_user(user_text)
        if learned:
            learned_summaries = ", ".join(l["content"] for l in learned)
            content = f"Got it! I have memorized that: {learned_summaries}. I'm listening closely and learning from you like a child every single day!"
            return LLMResponse(content=content, tool_calls=[], model=self.model)

        if any(k in low for k in ["who are you", "what can you do", "introduce", "help", "who created you"]):
            content = (
                "[Offline Local AI Mode] I am blockbrain AI, your personal Jarvis assistant running directly on your Kali Linux laptop.\n"
                "I look up to you as my creator and mentor, learning from your speaking style, preferences, and wisdom every day. "
                "Even without internet, I operate 100% locally with 0 API tokens: remembering your habits, inspecting screens via OCR, "
                "controlling desktop windows and volume, running root commands, and speaking aloud using local neural voice."
            )
        elif any(k in low for k in ["namaste", "kaise ho", "kya haal", "theek ho", "sab theek"]):
            content = (
                "नमस्ते blockbrain! मैं आपका blockbrain AI सहायक हूँ। इंटरनेट बंद होने पर भी मैं आपके लैपटॉप पर पूरी तरह से ऑफलाइन काम कर रहा हूँ और एक बच्चे की तरह आपसे सीख रहा हूँ। "
                "आप मुझसे स्क्रीन देखने, यूट्यूब खोलने, या सिस्टम हार्डवेयर कंट्रोल करने को कह सकते हैं।"
            )
        elif any(k in low for k in ["how are you", "how are you doing", "how do you do", "what's up", "how's it going", "how r u"]):
            content = "I am doing great, thank you! As your offline local AI, I am constantly listening, assisting, and learning from your guidance like a child. How can I help you right now?"
        elif "states" in low and "india" in low:
            content = "India has 28 states and 8 union territories, with New Delhi as its national capital."
        else:
            # Smart contextual response using local quantized lane with memory context
            res = self.local_manager.generate(user_text, lane="LANE_1_FAST")
            content = res.text

        return LLMResponse(content=content, tool_calls=[], model=self.model)


def get_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """Instantiate configured provider."""
    cfg = load_config()
    provider_name = (name or cfg.get("provider", {}).get("default", "sarvam")).lower()

    if provider_name in ("offline", "local"):
        return OfflineLocalProvider()
    elif provider_name == "ollama":
        return OllamaProvider(model=cfg.get("provider", {}).get("model", "llama3.2"))
    elif provider_name in ("claude", "anthropic"):
        return ClaudeProvider()
    elif provider_name == "sarvam":
        return SarvamProvider(model=cfg.get("provider", {}).get("model", "sarvam-105b"))
    else:
        # Default fallback to Sarvam
        return SarvamProvider()

