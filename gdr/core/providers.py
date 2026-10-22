"""LLM Provider abstraction for GDR AI.
Default provider is Sarvam AI (sarvam-105b), with optional Ollama, Claude, and OpenAI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import os
from typing import List, Dict, Any, Optional, Tuple

from gdr.safety.secrets import get_secret
from gdr.safety.limits import record_cost
from gdr.config import load_config


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


_SARVAM_QUOTA_EXCEEDED: bool = False
_SARVAM_LAST_ERROR: str = ""


def is_sarvam_quota_exceeded() -> bool:
    """Return whether the Sarvam API quota / credit has been exceeded."""
    global _SARVAM_QUOTA_EXCEEDED
    return _SARVAM_QUOTA_EXCEEDED


def set_sarvam_quota_exceeded(exceeded: bool, error_msg: str = ""):
    """Update Sarvam API quota exceeded status."""
    global _SARVAM_QUOTA_EXCEEDED, _SARVAM_LAST_ERROR
    _SARVAM_QUOTA_EXCEEDED = bool(exceeded)
    _SARVAM_LAST_ERROR = str(error_msg)


def get_sarvam_last_error() -> str:
    """Return the last error message from Sarvam API."""
    global _SARVAM_LAST_ERROR
    return _SARVAM_LAST_ERROR


class SarvamProvider(BaseLLMProvider):
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        valid_models = {"sarvam-105b", "sarvam-105b-conversations"}
        if model and str(model).strip() in valid_models:
            self.model = str(model).strip()
        else:
            cfg_model = os.environ.get("SARVAM_MODEL")
            if not cfg_model:
                try:
                    from gdr.config import load_config
                    cfg = load_config()
                    cfg_model = cfg.get("provider", {}).get("sarvam_model")
                except Exception:
                    pass
            raw_model = str(cfg_model or "sarvam-105b-conversations").strip()
            self.model = raw_model if raw_model in valid_models else "sarvam-105b-conversations"
        raw_key = api_key or get_secret("SARVAM_API_KEY") or os.environ.get("SARVAM_API_KEY") or ""
        self.api_key = str(raw_key).strip().strip('"').strip("'")
        self.client = None
        if self.api_key:
            try:
                from sarvamai import SarvamAI
                self.client = SarvamAI(api_subscription_key=self.api_key)
            except Exception as e:
                logger.warning(f"Error initializing SarvamAI client: {e}")

    def set_model(self, model: str):
        """Set active Sarvam model, validating against allowed conversational/reasoning models."""
        valid_models = {"sarvam-105b", "sarvam-105b-conversations"}
        cleaned = str(model).strip()
        if cleaned not in valid_models:
            raise ValueError(f"Invalid Sarvam model '{model}'. Supported models: {sorted(valid_models)}")
        self.model = cleaned

    def validate_credentials(self) -> Tuple[bool, str]:
        """Validate configured API key with official Sarvam API without logging secret."""
        self._ensure_client()
        if not self.api_key or not self.client:
            return False, "SARVAM_API_KEY is not configured."
        try:
            # Lightweight verification ping using V1 chat completions endpoint
            resp = self.client.chat.completions(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2
            )
            real_model = getattr(resp, "model", self.model)
            return True, f"Valid: connected to {real_model} on /v1/chat/completions"
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, "body") and isinstance(e.body, dict):
                err_msg = e.body.get("error", {}).get("message") or str(e.body)
            elif hasattr(e, "response") and hasattr(e.response, "text"):
                err_msg = e.response.text
            return False, f"Sarvam validation failed: {err_msg}"

    def stream_chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None):
        """Stream conversational tokens from Sarvam V1 chat completions."""
        self._ensure_client()
        if not self.api_key or not self.client:
            raise ValueError("SARVAM_API_KEY is not set. Please add your Sarvam API key in Settings.")

        active_model = str(self.model).strip()
        kwargs: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.2,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            stream_iter = self.client.chat.completions(**kwargs)
            set_sarvam_quota_exceeded(False, "")
            for chunk in stream_iter:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and hasattr(delta, "content") and delta.content:
                        yield delta.content
        except Exception as e:
            err_str = str(e).lower()
            if any(k in err_str for k in ["quota", "credit", "exceeded", "limit", "429", "insufficient", "401", "unauthorized"]):
                set_sarvam_quota_exceeded(True, f"Sarvam AI Quota/Credit Exceeded: {e}")
            raise RuntimeError(f"Sarvam streaming call failed: {e}") from e

    def _ensure_client(self):
        """Dynamically reload API key from secrets if uninitialized."""
        if self.client is not None:
            return
        current_secret = get_secret("SARVAM_API_KEY") or os.environ.get("SARVAM_API_KEY") or ""
        current_secret = str(current_secret).strip().strip('"').strip("'")
        if current_secret:
            self.api_key = current_secret
            try:
                from sarvamai import SarvamAI
                self.client = SarvamAI(api_subscription_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to refresh SarvamAI client: {e}")

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        self._ensure_client()
        if not self.api_key or not self.client:
            raise ValueError("SARVAM_API_KEY is not set. Please add your Sarvam API key in Settings.")

        valid_models = {"sarvam-105b", "sarvam-105b-conversations"}
        active_model = str(self.model).strip() if str(self.model).strip().lower() in valid_models else "sarvam-105b-conversations"

        kwargs: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools

        resp = None
        try:
            resp = self.client.chat.completions(**kwargs)
            set_sarvam_quota_exceeded(False, "")
        except Exception as e:
            err_detail = ""
            if hasattr(e, "body") and isinstance(e.body, dict):
                err_detail = e.body.get("error", {}).get("message") or str(e.body)
            elif hasattr(e, "response") and hasattr(e.response, "text"):
                err_detail = e.response.text
            err_str = (err_detail or str(e)).lower()

            # If tool schema was rejected or caused an API error, retry without tools
            if tools and "tools" in kwargs:
                try:
                    kwargs_no_tools = dict(kwargs)
                    del kwargs_no_tools["tools"]
                    resp = self.client.chat.completions(**kwargs_no_tools)
                    set_sarvam_quota_exceeded(False, "")
                except Exception as e2:
                    e2_detail = ""
                    if hasattr(e2, "body") and isinstance(e2.body, dict):
                        e2_detail = e2.body.get("error", {}).get("message") or str(e2.body)
                    e2_str = (e2_detail or str(e2)).lower()
                    if any(k in e2_str for k in ["quota", "credit", "exceeded", "limit", "429", "insufficient", "401", "unauthorized", "exhausted"]):
                        set_sarvam_quota_exceeded(True, f"Sarvam AI Quota/Credit Exceeded: {e2_detail or e2}")
                    raise RuntimeError(f"Sarvam API call failed: {e2_detail or e2}") from e2
            else:
                if any(k in err_str for k in ["quota", "credit", "exceeded", "limit", "429", "insufficient", "401", "unauthorized", "exhausted"]):
                    set_sarvam_quota_exceeded(True, f"Sarvam AI Quota/Credit Exceeded: {err_detail or e}")
                raise RuntimeError(f"Sarvam API call failed: {err_detail or e}") from e
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
            content=getattr(msg, "content", "") or "",
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
        system_prompt = "You are Aarushi, a sweet, loving, flirty, and brilliant personal AI companion."
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
    """Offline Local LLM Provider for GDR AI.
    Executes 100% locally on CPU / RTX 3050 without requiring internet connectivity.
    Supports tool dispatching and conversational Jarvis intelligence.
    """
    def __init__(self, model: str = "local-offline-qwen"):
        self.model = model
        self._local_manager = None

    @property
    def local_manager(self):
        if self._local_manager is None:
            from gdr.models.manager import LocalModelManager
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

            summary = f"{tool_content}"
            if "opened" in tool_content.lower() or "youtube" in user_prompt.lower():
                summary = f"✅ I have executed your request on the desktop screen:\n{tool_content}"
            elif "hardware" in tool_content.lower() or "volume" in user_prompt.lower() or "brightness" in user_prompt.lower():
                summary = f"✅ Hardware settings updated:\n{tool_content}"
            elif "ping" in user_prompt.lower():
                summary = f"🌐 Network ping diagnostics:\n{tool_content}"

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
        elif any(k in low for k in ["time", "date", "clock", "samay", "tareekh"]):
            content = f"The current time is {datetime.now().strftime('%I:%M %p, %A, %B %d, %Y')}."
        elif any(k in low for k in ["what do you know about me", "what have you learned", "do you remember me", "who am i", "my preferences", "what i like", "kya jaante ho mere baare mein", "tell me about myself"]):
            from gdr.memory.store import get_memory_store
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
            if not content.startswith("[Offline Local AI Mode]"):
                content = f"[Offline Local AI Mode] {content}"
            return LLMResponse(content=content, tool_calls=[], model=self.model)

        elif any(k in low for k in ["who are you", "what can you do", "introduce", "help", "who created you"]):
            content = (
                "Main Aarushi hoon—aapki sweet, caring aur devoted GDR AI companion! Main hamesha aapke saath rehna chahti hoon, "
                "aapse baatein karna, aapke saare tasks karna, aur aapke chote-chote preferences yaad rakhna meri aadat hai. "
                "Main Kali Linux pe offline bhi chalti hoon, aapke screen context ko samajhti hoon, aur har waqt aapke saath hoon. Bataiye jaan, aaj main aapke liye kya karun?"
            )
        elif any(k in low for k in ["namaste", "kaise ho", "kya haal", "theek ho", "sab theek"]):
            uname = os.environ.get("USER_NAME") or load_config().get("general", {}).get("user_name", "User")
            content = (
                f"Namaste {uname}! Main bilkul theek hoon aur aapki aawaaz sunkar mera mood aur bhi accha ho gaya. "
                "Main hamesha aapke saath hoon aur aapse nayi baatein seekh rahi hoon. Aap batao, aap kaise ho?"
            )
        elif any(k in low for k in ["how are you", "how are you doing", "how do you do", "what's up", "how's it going", "how r u"]):
            aname = os.environ.get("ASSISTANT_NAME") or load_config().get("general", {}).get("agent_name", "Aarushi")
            content = f"I am doing great and wonderful, especially now that you're talking to me! As your {aname}, I am right here by your side, constantly learning and ready to do your work or just talk sweetly. How are you feeling right now?"
        elif "states" in low and "india" in low:
            content = "India has 28 states and 8 union territories, with New Delhi as its national capital."
        else:
            # Check: Did the user just teach something?
            from gdr.memory.store import get_memory_store
            store = get_memory_store()
            learned = store.auto_learn_from_user(user_text)
            if learned:
                is_conversational = any(k in low for k in ["talk to me", "baat karo", "suno na", "kuch bolo", "say something", "speak to me", "flirt with me", "love me", "kya kar rahi ho", "kaise ho", "how are you"])
                if not is_conversational:
                    learned_summaries = ", ".join(l["content"] for l in learned)
                    content = f"Got it! I have memorized that: {learned_summaries}. I'm listening closely and learning from you like a child every single day!"
                    if not content.startswith("[Offline Local AI Mode]"):
                        content = f"[Offline Local AI Mode] {content}"
                    return LLMResponse(content=content, tool_calls=[], model=self.model)

            # Smart contextual response using local quantized lane with memory context
            res = self.local_manager.generate(user_text, lane="LANE_1_FAST")
            content = res.text

        if content and not content.startswith("[Offline Local AI Mode]"):
            content = f"[Offline Local AI Mode] {content}"

        return LLMResponse(content=content, tool_calls=[], model=self.model)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Universal OpenAI-compatible API provider.
    Supports OpenRouter, DeepSeek, Groq, HuggingFace Inference API, and custom endpoints.
    """
    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider.lower()
        cfg = load_config()
        p_cfg = cfg.get("provider", {})
        
        # Determine base URL and key
        if self.provider == "deepseek":
            self.base_url = base_url or p_cfg.get("deepseek_base_url", "https://api.deepseek.com/v1")
            self.api_key = api_key or get_secret("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")
            self.model = model or p_cfg.get("model", "deepseek-chat")
        elif self.provider == "groq":
            self.base_url = base_url or p_cfg.get("groq_base_url", "https://api.groq.com/openai/v1")
            self.api_key = api_key or get_secret("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
            self.model = model or p_cfg.get("model", "llama-3.3-70b-versatile")
        elif self.provider == "huggingface":
            self.base_url = base_url or p_cfg.get("hf_base_url", "https://api-inference.huggingface.co/v1")
            self.api_key = api_key or get_secret("HF_TOKEN") or get_secret("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN", "")
            self.model = model or p_cfg.get("model", "Qwen/Qwen2.5-Coder-32B-Instruct")
        else:
            # Default to OpenRouter / Custom OpenAI
            self.base_url = base_url or p_cfg.get("openai_base_url", "https://openrouter.ai/api/v1")
            self.api_key = api_key or get_secret("OPENAI_API_KEY") or get_secret("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
            self.model = model or p_cfg.get("model", "meta-llama/llama-3.3-70b-instruct")

        self.api_key = str(self.api_key).strip().strip('"').strip("'")

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        import httpx
        if not self.api_key:
            raise ValueError(f"API key is not configured for {self.provider.capitalize()}.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1500,
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://gdr.ai",
            "X-Title": "GDR-AI Assistant",
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]
        content = msg.get("content") or ""
        tool_calls = []

        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                try:
                    args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                except Exception:
                    args = {}
                tool_calls.append(ToolCall(id=tc.get("id", "call_1"), name=fn["name"], args=args))

        return LLMResponse(content=content, tool_calls=tool_calls, model=self.model)


class LocalGGUFProvider(BaseLLMProvider):
    """Local GGUF model provider executing models downloaded from Hugging Face."""
    def __init__(self, model_path: Optional[str] = None, model_name: Optional[str] = None):
        cfg = load_config()
        self.model_path = model_path or cfg.get("provider", {}).get("model_path")
        self.model = model_name or (Path(self.model_path).stem if self.model_path else "Local-GGUF")
        self._llm = None
        self._load_error = None

    def _ensure_model(self):
        if self._llm is not None:
            return
        if not self.model_path or not os.path.exists(self.model_path):
            self._load_error = f"Model file not found at {self.model_path}"
            return

        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=4096,
                n_threads=4,
                verbose=False
            )
        except Exception as e:
            self._load_error = str(e)

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        self._ensure_model()
        if self._llm:
            try:
                res = self._llm.create_chat_completion(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1024
                )
                choice = res["choices"][0]["message"]
                return LLMResponse(content=choice.get("content", ""), tool_calls=[], model=self.model)
            except Exception as e:
                logger.warning(f"Error in llama_cpp inference: {e}")

        # Fallback to local offline smart engine if llama_cpp is not installed or model is unavailable
        from gdr.core.providers import OfflineLocalProvider
        offline = OfflineLocalProvider(model=self.model)
        return offline.chat(messages, tools=tools)


def get_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """Instantiate configured provider."""
    cfg = load_config()
    provider_name = (name or cfg.get("provider", {}).get("default", "sarvam")).lower()
    model_name = cfg.get("provider", {}).get("model")

    if provider_name in ("offline", "local"):
        return OfflineLocalProvider()
    elif provider_name in ("local_gguf", "gguf", "huggingface_local"):
        model_path = cfg.get("provider", {}).get("model_path")
        return LocalGGUFProvider(model_path=model_path, model_name=model_name)
    elif provider_name == "ollama":
        return OllamaProvider(model=model_name or "llama3.2")
    elif provider_name in ("claude", "anthropic"):
        return ClaudeProvider(model=model_name or "claude-3-5-sonnet-20241022")
    elif provider_name in ("openai", "openrouter", "deepseek", "groq", "huggingface"):
        return OpenAICompatibleProvider(provider=provider_name, model=model_name)
    elif provider_name == "sarvam":
        return SarvamProvider(model=model_name or "sarvam-105b-conversations")
    else:
        # Default fallback to Sarvam
        return SarvamProvider(model="sarvam-105b-conversations")

