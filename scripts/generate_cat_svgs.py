"""Generate high-fidelity, cute, vector SVG character assets for the GDR Cat Companion."""

import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "gdr" / "web" / "static" / "characters" / "cat"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEFS = """  <defs>
    <linearGradient id="catFur" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fed7aa"/>
      <stop offset="60%" stop-color="#fdba74"/>
      <stop offset="100%" stop-color="#fb923c"/>
    </linearGradient>
    <linearGradient id="catChest" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#fff7ed"/>
    </linearGradient>
    <linearGradient id="earInner" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fecdd3"/>
      <stop offset="100%" stop-color="#fda4af"/>
    </linearGradient>
    <radialGradient id="catEye" cx="50%" cy="35%" r="55%">
      <stop offset="0%" stop-color="#34d399"/>
      <stop offset="50%" stop-color="#059669"/>
      <stop offset="100%" stop-color="#064e3b"/>
    </radialGradient>
    <linearGradient id="bellGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="50%" stop-color="#facc15"/>
      <stop offset="100%" stop-color="#ca8a04"/>
    </linearGradient>
    <linearGradient id="collarGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f43f5e"/>
      <stop offset="100%" stop-color="#e11d48"/>
    </linearGradient>
    <filter id="softBlush" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>"""

BASE_BODY = """  <!-- Ambient Backdrop Glow -->
  <circle cx="200" cy="240" r="170" fill="#ffedd5" opacity="0.3"/>

  <!-- Tail -->
  <path d="M 275 390 C 330 380, 355 330, 335 285 C 325 265, 305 270, 310 290 C 320 325, 295 355, 260 375 Z" fill="url(#catFur)"/>
  <path d="M 320 280 C 335 285, 330 295, 315 295 Z" fill="#ffffff" opacity="0.9"/>

  <!-- Body -->
  <ellipse cx="200" cy="370" rx="95" ry="85" fill="url(#catFur)"/>
  <!-- Fluffy White Chest / Bib -->
  <path d="M 160 320 C 145 350, 150 405, 175 425 C 190 435, 210 435, 225 425 C 250 405, 255 350, 240 320 C 225 335, 175 335, 160 320 Z" fill="url(#catChest)"/>

  <!-- Collar & Golden Chime Bell -->
  <path d="M 140 310 Q 200 332 260 310 Q 200 342 140 310 Z" fill="url(#collarGrad)"/>
  <circle cx="200" cy="335" r="14" fill="url(#bellGrad)"/>
  <circle cx="200" cy="337" r="3" fill="#854d0e"/>
  <line x1="192" y1="333" x2="208" y2="333" stroke="#854d0e" stroke-width="2"/>
  <circle cx="197" cy="331" r="2.5" fill="#ffffff" opacity="0.8"/>

  <!-- Front Paws -->
  <ellipse cx="165" cy="425" rx="20" ry="14" fill="#ffffff"/>
  <ellipse cx="235" cy="425" rx="20" ry="14" fill="#ffffff"/>
  <path d="M 158 420 L 158 432 M 172 420 L 172 432" stroke="#fed7aa" stroke-width="2" stroke-linecap="round"/>
  <path d="M 228 420 L 228 432 M 242 420 L 242 432" stroke="#fed7aa" stroke-width="2" stroke-linecap="round"/>"""

def svg_frame(content: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 480" width="100%" height="100%">
{DEFS}
{BASE_BODY}
{content}
</svg>"""

# 1. NEUTRAL
def gen_neutral():
    content = """  <!-- Head -->
  <g id="head">
    <!-- Ears -->
    <path d="M 125 175 L 98 85 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 108 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 302 85 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 292 98 L 237 135 Z" fill="url(#earInner)"/>

    <!-- Head Base -->
    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>

    <!-- Cheeks & Muzzle -->
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <!-- Blush -->
    <ellipse cx="138" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>

    <!-- Whiskers -->
    <line x1="120" y1="235" x2="60" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Eyes (Big Emerald Anime Cat Eyes) -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <ellipse cx="240" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <!-- Pupils -->
      <ellipse cx="160" cy="195" rx="7" ry="16" fill="#0f172a"/>
      <ellipse cx="240" cy="195" rx="7" ry="16" fill="#0f172a"/>
      <!-- Sparkle Highlights -->
      <circle cx="154" cy="186" r="6" fill="#ffffff"/>
      <circle cx="166" cy="204" r="3" fill="#ffffff" opacity="0.8"/>
      <circle cx="234" cy="186" r="6" fill="#ffffff"/>
      <circle cx="246" cy="204" r="3" fill="#ffffff" opacity="0.8"/>
    </g>

    <!-- Nose -->
    <polygon points="194,230 206,230 200,237" fill="#f43f5e"/>

    <!-- Cute Curved Cat Mouth :3 -->
    <path d="M 185 240 Q 192 248 200 240 Q 208 248 215 240" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>"""
    return svg_frame(content)

# 2. LISTENING
def gen_listening():
    content = """  <!-- Sound Reception Halo Waves -->
  <circle cx="200" cy="90" r="25" stroke="#38bdf8" stroke-width="2" fill="none" opacity="0.6"/>
  <circle cx="200" cy="90" r="45" stroke="#38bdf8" stroke-width="1.5" fill="none" opacity="0.3"/>

  <!-- Head -->
  <g id="head">
    <!-- Left ear forward perked, right ear angled listening -->
    <path d="M 125 175 L 90 75 L 168 130 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 100 88 L 160 130 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 315 95 L 235 140 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 305 108 L 243 140 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>

    <!-- Whiskers perked -->
    <line x1="120" y1="230" x2="60" y2="215" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="242" x2="55" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="254" x2="65" y2="260" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="230" x2="340" y2="215" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="242" x2="345" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="254" x2="335" y2="260" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Attentive Wide Eyes with Ear Sparkles -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="20" ry="25" fill="url(#catEye)"/>
      <ellipse cx="240" cy="195" rx="20" ry="25" fill="url(#catEye)"/>
      <ellipse cx="160" cy="195" rx="10" ry="18" fill="#0f172a"/>
      <ellipse cx="240" cy="195" rx="10" ry="18" fill="#0f172a"/>
      <circle cx="153" cy="185" r="7" fill="#ffffff"/>
      <circle cx="167" cy="205" r="3.5" fill="#ffffff" opacity="0.9"/>
      <circle cx="233" cy="185" r="7" fill="#ffffff"/>
      <circle cx="247" cy="205" r="3.5" fill="#ffffff" opacity="0.9"/>
    </g>

    <polygon points="194,230 206,230 200,237" fill="#f43f5e"/>
    <path d="M 188 241 Q 194 246 200 241 Q 206 246 212 241" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>"""
    return svg_frame(content)

# 3. SPEAKING
def gen_speaking():
    content = """  <!-- Speech Note Sparkles -->
  <text x="310" y="150" font-size="24" fill="#fbbf24">♪</text>
  <text x="70" y="160" font-size="20" fill="#fbbf24">✨</text>

  <!-- Head -->
  <g id="head">
    <path d="M 125 175 L 98 85 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 108 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 302 85 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 292 98 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.45" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.45" filter="url(#softBlush)"/>

    <line x1="120" y1="235" x2="60" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Bright Expressive Eyes -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <ellipse cx="240" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <ellipse cx="160" cy="195" rx="7" ry="16" fill="#0f172a"/>
      <ellipse cx="240" cy="195" rx="7" ry="16" fill="#0f172a"/>
      <circle cx="154" cy="186" r="6" fill="#ffffff"/>
      <circle cx="166" cy="204" r="3" fill="#ffffff" opacity="0.8"/>
      <circle cx="234" cy="186" r="6" fill="#ffffff"/>
      <circle cx="246" cy="204" r="3" fill="#ffffff" opacity="0.8"/>
    </g>

    <polygon points="194,228 206,228 200,235" fill="#f43f5e"/>

    <!-- Open Talking Cute Mouth with Pink Tongue -->
    <path d="M 188 238 Q 200 236 212 238 C 214 256, 186 256, 188 238 Z" fill="#991b1b"/>
    <ellipse cx="200" cy="249" rx="8" ry="5" fill="#f43f5e"/>
  </g>"""
    return svg_frame(content)

# 4. HAPPY
def gen_happy():
    content = """  <!-- Joy Sparkles -->
  <text x="75" y="130" font-size="28" fill="#f59e0b">✨</text>
  <text x="295" y="125" font-size="28" fill="#f59e0b">✨</text>

  <!-- Head -->
  <g id="head">
    <path d="M 125 175 L 94 80 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 104 94 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 306 80 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 296 94 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <!-- Rich Happy Cheeks -->
    <ellipse cx="138" cy="230" rx="16" ry="9" fill="#fb7185" opacity="0.6" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="230" rx="16" ry="9" fill="#fb7185" opacity="0.6" filter="url(#softBlush)"/>

    <line x1="120" y1="230" x2="60" y2="218" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="240" x2="55" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="250" x2="65" y2="258" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="230" x2="340" y2="218" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="240" x2="345" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="250" x2="335" y2="258" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Joyful Crescent Arch Eyes (^ _ ^) -->
    <path d="M 142 200 Q 160 176 178 200" stroke="#7c2d12" stroke-width="5" fill="none" stroke-linecap="round"/>
    <path d="M 222 200 Q 240 176 258 200" stroke="#7c2d12" stroke-width="5" fill="none" stroke-linecap="round"/>

    <polygon points="194,226 206,226 200,233" fill="#f43f5e"/>

    <!-- Wide Happy Smile -->
    <path d="M 182 236 Q 200 234 218 236 C 220 262, 180 262, 182 236 Z" fill="#e11d48"/>
    <ellipse cx="200" cy="254" rx="11" ry="6" fill="#fecdd3"/>
  </g>"""
    return svg_frame(content)

# 5. THINKING
def gen_thinking():
    content = """  <!-- Floating Thought Bubbles -->
  <circle cx="270" cy="130" r="6" fill="#60a5fa" opacity="0.6"/>
  <circle cx="290" cy="110" r="10" fill="#60a5fa" opacity="0.7"/>
  <circle cx="320" cy="85" r="16" fill="#60a5fa" opacity="0.8"/>
  <text x="314" y="92" font-size="20" font-weight="bold" fill="#ffffff">?</text>

  <!-- Raised Paw to Chin -->
  <ellipse cx="225" cy="275" rx="16" ry="20" fill="#ffffff" transform="rotate(-20 225 275)"/>
  <line x1="220" y1="268" x2="225" y2="280" stroke="#fed7aa" stroke-width="2"/>

  <!-- Head -->
  <g id="head">
    <path d="M 125 175 L 98 85 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 108 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 302 85 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 292 98 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="12" ry="6" fill="#fb7185" opacity="0.35" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="12" ry="6" fill="#fb7185" opacity="0.35" filter="url(#softBlush)"/>

    <line x1="120" y1="235" x2="60" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Eyes Glancing Up & Right (Thoughtful) -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <ellipse cx="240" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <!-- Pupils angled up-right -->
      <ellipse cx="165" cy="188" rx="7" ry="14" fill="#0f172a"/>
      <ellipse cx="245" cy="188" rx="7" ry="14" fill="#0f172a"/>
      <circle cx="162" cy="182" r="5" fill="#ffffff"/>
      <circle cx="242" cy="182" r="5" fill="#ffffff"/>
    </g>

    <polygon points="194,230 206,230 200,237" fill="#f43f5e"/>
    <!-- Curious Pout Mouth -->
    <path d="M 193 243 Q 200 240 207 243" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>"""
    return svg_frame(content)

# 6. CURIOUS
def gen_curious():
    content = """  <!-- Star Twinkle -->
  <text x="60" y="140" font-size="26" fill="#38bdf8">✨</text>

  <!-- Head tilted curiously 6 degrees -->
  <g id="head" transform="rotate(7 200 210)">
    <path d="M 125 175 L 90 85 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 102 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 310 90 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 300 102 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.45" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.45" filter="url(#softBlush)"/>

    <line x1="120" y1="235" x2="60" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Wide Curious Starry Eyes -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="20" ry="25" fill="url(#catEye)"/>
      <ellipse cx="240" cy="195" rx="20" ry="25" fill="url(#catEye)"/>
      <ellipse cx="160" cy="195" rx="9" ry="17" fill="#0f172a"/>
      <ellipse cx="240" cy="195" rx="9" ry="17" fill="#0f172a"/>
      <circle cx="154" cy="187" r="7" fill="#ffffff"/>
      <circle cx="167" cy="204" r="3.5" fill="#ffffff"/>
      <circle cx="234" cy="187" r="7" fill="#ffffff"/>
      <circle cx="247" cy="204" r="3.5" fill="#ffffff"/>
    </g>

    <polygon points="194,230 206,230 200,237" fill="#f43f5e"/>
    <!-- Small Inquisitive 'o' mouth -->
    <ellipse cx="200" cy="245" rx="4" ry="5" fill="#7c2d12"/>
  </g>"""
    return svg_frame(content)

# 7. SURPRISED
def gen_surprised():
    content = """  <!-- Exclamation Marks -->
  <text x="80" y="120" font-size="30" font-weight="bold" fill="#f59e0b">!</text>
  <text x="300" y="120" font-size="30" font-weight="bold" fill="#f59e0b">!</text>

  <!-- Head -->
  <g id="head">
    <!-- Straight Up Alert Ears -->
    <path d="M 125 175 L 85 70 L 170 125 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 95 82 L 160 125 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 315 70 L 230 125 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 305 82 L 240 125 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="94" ry="80" fill="url(#catFur)"/>
    <ellipse cx="182" cy="244" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="244" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="16" ry="8" fill="#fb7185" opacity="0.5" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="16" ry="8" fill="#fb7185" opacity="0.5" filter="url(#softBlush)"/>

    <!-- Whiskers standing out -->
    <line x1="120" y1="230" x2="50" y2="215" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="45" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="260" x2="50" y2="275" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="230" x2="350" y2="215" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="355" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="260" x2="350" y2="275" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Giant Round Surprised Eyes (O _ O) -->
    <g id="eyes">
      <circle cx="160" cy="195" r="24" fill="url(#catEye)"/>
      <circle cx="240" cy="195" r="24" fill="url(#catEye)"/>
      <circle cx="160" cy="195" r="13" fill="#0f172a"/>
      <circle cx="240" cy="195" r="13" fill="#0f172a"/>
      <circle cx="152" cy="186" r="8" fill="#ffffff"/>
      <circle cx="166" cy="204" r="4" fill="#ffffff"/>
      <circle cx="232" cy="186" r="8" fill="#ffffff"/>
      <circle cx="246" cy="204" r="4" fill="#ffffff"/>
    </g>

    <polygon points="194,228 206,228 200,235" fill="#f43f5e"/>
    <!-- Round Open 'O' Mouth -->
    <ellipse cx="200" cy="248" rx="8" ry="11" fill="#7c2d12"/>
    <ellipse cx="200" cy="252" rx="5" ry="5" fill="#f43f5e"/>
  </g>"""
    return svg_frame(content)

# 8. COMFORTING
def gen_comforting():
    content = """  <!-- Gentle Warm Purring Hearts -->
  <path d="M 75 140 C 75 130, 90 130, 90 140 C 90 150, 75 160, 75 160 C 75 160, 60 150, 60 140 C 60 130, 75 130, 75 140 Z" fill="#f43f5e" opacity="0.75"/>
  <path d="M 320 130 C 320 122, 332 122, 332 130 C 332 138, 320 146, 320 146 C 320 146, 308 138, 308 130 C 308 122, 320 122, 320 130 Z" fill="#f43f5e" opacity="0.75"/>

  <!-- Head tilted slightly -->
  <g id="head" transform="rotate(-4 200 210)">
    <path d="M 125 175 L 100 88 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 110 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 300 88 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 290 98 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="16" ry="8" fill="#fb7185" opacity="0.55" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="16" ry="8" fill="#fb7185" opacity="0.55" filter="url(#softBlush)"/>

    <line x1="120" y1="235" x2="60" y2="228" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="262" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="228" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="262" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Gentle Smiling Eyes (Happy Loving Arches) -->
    <path d="M 144 198 Q 160 180 176 198" stroke="#7c2d12" stroke-width="4.5" fill="none" stroke-linecap="round"/>
    <path d="M 224 198 Q 240 180 256 198" stroke="#7c2d12" stroke-width="4.5" fill="none" stroke-linecap="round"/>

    <polygon points="194,228 206,228 200,235" fill="#f43f5e"/>
    <!-- Gentle Caring Smile -->
    <path d="M 186 240 Q 193 247 200 241 Q 207 247 214 240" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>"""
    return svg_frame(content)

# 9. TEASING
def gen_teasing():
    content = """  <!-- Playful Winking Sparkle -->
  <text x="285" y="150" font-size="24" fill="#f43f5e">✨</text>

  <!-- Head -->
  <g id="head">
    <path d="M 125 175 L 95 85 L 172 135 Z" fill="url(#catFur)"/>
    <path d="M 127 165 L 105 98 L 163 135 Z" fill="url(#earInner)"/>
    <path d="M 275 175 L 305 85 L 228 135 Z" fill="url(#catFur)"/>
    <path d="M 273 165 L 295 98 L 237 135 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="15" ry="8" fill="#fb7185" opacity="0.55" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="15" ry="8" fill="#fb7185" opacity="0.55" filter="url(#softBlush)"/>

    <line x1="120" y1="235" x2="60" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="245" x2="55" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="255" x2="65" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="235" x2="340" y2="225" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="245" x2="345" y2="245" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="255" x2="335" y2="265" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Left Eye Open, Right Eye Playfully Winking (> _ <) -->
    <g id="eyes">
      <ellipse cx="160" cy="195" rx="18" ry="24" fill="url(#catEye)"/>
      <ellipse cx="160" cy="195" rx="7" ry="16" fill="#0f172a"/>
      <circle cx="154" cy="186" r="6" fill="#ffffff"/>
      <circle cx="166" cy="204" r="3" fill="#ffffff" opacity="0.8"/>

      <!-- Winking Eye Right -->
      <path d="M 224 195 Q 240 182 256 195" stroke="#7c2d12" stroke-width="5" fill="none" stroke-linecap="round"/>
    </g>

    <polygon points="194,228 206,228 200,235" fill="#f43f5e"/>

    <!-- Cheeky Tongue Sticking Out (:P) -->
    <path d="M 188 238 Q 200 240 212 238" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
    <path d="M 194 240 C 194 254, 206 254, 206 240 Z" fill="#f43f5e"/>
    <line x1="200" y1="240" x2="200" y2="249" stroke="#be123c" stroke-width="1.5"/>
  </g>"""
    return svg_frame(content)

# 10. SLEEPY
def gen_sleepy():
    content = """  <!-- Floating 'z Z Z' Sleep Bubbles -->
  <text x="290" y="150" font-size="22" font-weight="bold" fill="#93c5fd">z</text>
  <text x="315" y="125" font-size="28" font-weight="bold" fill="#60a5fa">Z</text>
  <text x="340" y="95" font-size="34" font-weight="bold" fill="#3b82f6">Z</text>

  <!-- Head -->
  <g id="head">
    <!-- Relaxed Low Droopy Ears -->
    <path d="M 125 180 L 85 110 L 165 145 Z" fill="url(#catFur)"/>
    <path d="M 127 172 L 95 120 L 157 145 Z" fill="url(#earInner)"/>
    <path d="M 275 180 L 315 110 L 235 145 Z" fill="url(#catFur)"/>
    <path d="M 273 172 L 305 120 L 243 145 Z" fill="url(#earInner)"/>

    <ellipse cx="200" cy="210" rx="92" ry="78" fill="url(#catFur)"/>
    <ellipse cx="182" cy="242" rx="22" ry="16" fill="url(#catChest)"/>
    <ellipse cx="218" cy="242" rx="22" ry="16" fill="url(#catChest)"/>

    <ellipse cx="138" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>
    <ellipse cx="262" cy="235" rx="14" ry="7" fill="#fb7185" opacity="0.4" filter="url(#softBlush)"/>

    <line x1="120" y1="240" x2="60" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="118" y1="250" x2="55" y2="252" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="120" y1="260" x2="65" y2="268" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="240" x2="340" y2="238" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="282" y1="250" x2="345" y2="252" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>
    <line x1="280" y1="260" x2="335" y2="268" stroke="#fed7aa" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Sleepy Drooping Closed Eyes (- . -) -->
    <path d="M 144 195 Q 160 205 176 195" stroke="#7c2d12" stroke-width="4.5" fill="none" stroke-linecap="round"/>
    <path d="M 224 195 Q 240 205 256 195" stroke="#7c2d12" stroke-width="4.5" fill="none" stroke-linecap="round"/>

    <polygon points="194,228 206,228 200,235" fill="#f43f5e"/>
    <!-- Cute Sleepy Little Mouth -->
    <path d="M 194 242 Q 200 240 206 242" stroke="#7c2d12" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>"""
    return svg_frame(content)

GENS = {
    "neutral.svg": gen_neutral,
    "listening.svg": gen_listening,
    "speaking.svg": gen_speaking,
    "happy.svg": gen_happy,
    "thinking.svg": gen_thinking,
    "curious.svg": gen_curious,
    "surprised.svg": gen_surprised,
    "comforting.svg": gen_comforting,
    "teasing.svg": gen_teasing,
    "sleepy.svg": gen_sleepy,
}

for fname, gen_func in GENS.items():
    svg_content = gen_func()
    p = OUT_DIR / fname
    p.write_text(svg_content, encoding="utf-8")
    print(f"Generated {fname} ({len(svg_content)} bytes)")

