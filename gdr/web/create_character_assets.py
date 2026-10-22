"""Generate rich SVG character illustrations for Aarushi, Aoi, and Kenji with full expression packs.
All characters are custom designed vector illustrations released under Creative Commons Zero (CC0).
"""

from pathlib import Path
import json

STATIC_DIR = Path(__file__).resolve().parent / "static" / "characters"

def get_aarushi_svg(expression: str) -> str:
    # Common features for Aarushi
    mouths = {
        "neutral": '<path d="M 188 285 Q 200 292 212 285" stroke="#be123c" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "listening": '<path d="M 190 286 Q 200 294 210 286" stroke="#be123c" stroke-width="3" fill="none" stroke-linecap="round"/><circle cx="200" cy="304" r="2" fill="#be123c" opacity="0.6"/>',
        "speaking": '<path d="M 186 280 Q 200 305 214 280 Z" fill="#e11d48"/><path d="M 191 292 Q 200 298 209 292 Z" fill="#fda4af"/><path d="M 186 280 Q 200 284 214 280" stroke="#be123c" stroke-width="2.5" fill="none"/>',
        "happy": '<path d="M 184 280 Q 200 308 216 280 Z" fill="#f43f5e"/><path d="M 190 294 Q 200 304 210 294 Z" fill="#fda4af"/>',
        "thinking": '<path d="M 192 285 Q 200 280 208 285" stroke="#be123c" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "curious": '<path d="M 193 283 Q 203 293 213 283" stroke="#be123c" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "surprised": '<ellipse cx="200" cy="285" rx="7" ry="11" fill="#be123c"/><ellipse cx="200" cy="286" rx="4" ry="7" fill="#fda4af"/>',
        "comforting": '<path d="M 188 283 Q 200 295 212 283" stroke="#be123c" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
        "teasing": '<path d="M 188 282 Q 196 292 200 285 Q 204 292 212 282" stroke="#be123c" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "sleepy": '<path d="M 192 288 Q 200 282 208 288" stroke="#be123c" stroke-width="2.5" fill="none" stroke-linecap="round"/><ellipse cx="200" cy="292" rx="4" ry="2" fill="#be123c" opacity="0.4"/>',
    }

    eyes_left = {
        "neutral": '''
            <ellipse cx="160" cy="225" rx="15" ry="22" fill="#78350f"/>
            <ellipse cx="160" cy="228" rx="13" ry="18" fill="url(#eyeGradAarushi)"/>
            <circle cx="155" cy="217" r="5" fill="#ffffff"/>
            <circle cx="166" cy="233" r="2.5" fill="#ffffff" opacity="0.9"/>
            <path d="M 143 205 Q 160 195 178 205" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="160" cy="225" rx="16" ry="23" fill="#78350f"/>
            <ellipse cx="160" cy="227" rx="14" ry="19" fill="url(#eyeGradAarushi)"/>
            <circle cx="155" cy="217" r="6" fill="#ffffff"/>
            <circle cx="167" cy="233" r="3" fill="#ffffff"/>
            <path d="M 143 202 Q 160 192 178 202" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '''
            <path d="M 145 228 Q 160 210 176 228" stroke="#451a03" stroke-width="5" fill="none" stroke-linecap="round"/>
            <path d="M 142 203 Q 160 192 178 205" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "thinking": '''
            <ellipse cx="163" cy="220" rx="14" ry="20" fill="#78350f"/>
            <ellipse cx="163" cy="222" rx="12" ry="16" fill="url(#eyeGradAarushi)"/>
            <circle cx="159" cy="213" r="4.5" fill="#ffffff"/>
            <path d="M 143 198 Q 160 196 178 204" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "curious": '''
            <ellipse cx="160" cy="223" rx="16" ry="23" fill="#78350f"/>
            <ellipse cx="160" cy="225" rx="14" ry="19" fill="url(#eyeGradAarushi)"/>
            <circle cx="155" cy="215" r="5.5" fill="#ffffff"/>
            <path d="M 141 198 Q 160 188 178 200" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "surprised": '''
            <ellipse cx="160" cy="222" rx="18" ry="25" fill="#78350f"/>
            <ellipse cx="160" cy="224" rx="16" ry="21" fill="url(#eyeGradAarushi)"/>
            <circle cx="154" cy="213" r="6" fill="#ffffff"/>
            <circle cx="168" cy="231" r="3.5" fill="#ffffff"/>
            <path d="M 141 192 Q 160 182 179 194" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "comforting": '''
            <path d="M 145 226 Q 160 212 176 226" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
            <path d="M 143 205 Q 160 197 178 207" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "teasing": '''
            <path d="M 144 225 Q 160 236 176 225" stroke="#451a03" stroke-width="5" fill="none" stroke-linecap="round"/>
            <path d="M 143 200 Q 160 192 178 204" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "sleepy": '''
            <path d="M 145 227 Q 160 232 175 227" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
            <path d="M 143 208 Q 160 205 178 212" stroke="#451a03" stroke-width="3.5" fill="none" stroke-linecap="round"/>
        ''',
    }

    eyes_right = {
        "neutral": '''
            <ellipse cx="240" cy="225" rx="15" ry="22" fill="#78350f"/>
            <ellipse cx="240" cy="228" rx="13" ry="18" fill="url(#eyeGradAarushi)"/>
            <circle cx="235" cy="217" r="5" fill="#ffffff"/>
            <circle cx="246" cy="233" r="2.5" fill="#ffffff" opacity="0.9"/>
            <path d="M 222 205 Q 240 195 257 205" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="240" cy="225" rx="16" ry="23" fill="#78350f"/>
            <ellipse cx="240" cy="227" rx="14" ry="19" fill="url(#eyeGradAarushi)"/>
            <circle cx="235" cy="217" r="6" fill="#ffffff"/>
            <circle cx="247" cy="233" r="3" fill="#ffffff"/>
            <path d="M 222 202 Q 240 192 257 202" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '''
            <path d="M 224 228 Q 240 210 256 228" stroke="#451a03" stroke-width="5" fill="none" stroke-linecap="round"/>
            <path d="M 222 205 Q 240 192 258 203" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "thinking": '''
            <ellipse cx="243" cy="220" rx="14" ry="20" fill="#78350f"/>
            <ellipse cx="243" cy="222" rx="12" ry="16" fill="url(#eyeGradAarushi)"/>
            <circle cx="239" cy="213" r="4.5" fill="#ffffff"/>
            <path d="M 222 204 Q 240 196 257 198" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "curious": '''
            <ellipse cx="240" cy="223" rx="16" ry="23" fill="#78350f"/>
            <ellipse cx="240" cy="225" rx="14" ry="19" fill="url(#eyeGradAarushi)"/>
            <circle cx="235" cy="215" r="5.5" fill="#ffffff"/>
            <path d="M 222 200 Q 240 188 259 198" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "surprised": '''
            <ellipse cx="240" cy="222" rx="18" ry="25" fill="#78350f"/>
            <ellipse cx="240" cy="224" rx="16" ry="21" fill="url(#eyeGradAarushi)"/>
            <circle cx="234" cy="213" r="6" fill="#ffffff"/>
            <circle cx="248" cy="231" r="3.5" fill="#ffffff"/>
            <path d="M 221 194 Q 240 182 259 192" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "comforting": '''
            <path d="M 224 226 Q 240 212 256 226" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
            <path d="M 222 207 Q 240 197 257 205" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "teasing": '''
            <ellipse cx="240" cy="225" rx="15" ry="22" fill="#78350f"/>
            <ellipse cx="240" cy="228" rx="13" ry="18" fill="url(#eyeGradAarushi)"/>
            <circle cx="235" cy="217" r="5" fill="#ffffff"/>
            <circle cx="246" cy="233" r="2.5" fill="#ffffff" opacity="0.9"/>
            <path d="M 222 202 Q 240 192 257 202" stroke="#451a03" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "sleepy": '''
            <path d="M 225 227 Q 240 232 255 227" stroke="#451a03" stroke-width="4" fill="none" stroke-linecap="round"/>
            <path d="M 222 212 Q 240 205 257 208" stroke="#451a03" stroke-width="3.5" fill="none" stroke-linecap="round"/>
        ''',
    }

    m_code = mouths.get(expression, mouths["neutral"])
    el_code = eyes_left.get(expression, eyes_left["neutral"])
    er_code = eyes_right.get(expression, eyes_right["neutral"])

    # Extra sparkle or blush adjustment
    blush_opacity = "0.7" if expression in ("happy", "teasing", "comforting") else "0.4"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 480" width="100%" height="100%">
  <defs>
    <radialGradient id="eyeGradAarushi" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="50%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#b45309"/>
    </radialGradient>
    <linearGradient id="hairGradAarushi" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#5a2e1d"/>
      <stop offset="40%" stop-color="#451a03"/>
      <stop offset="100%" stop-color="#2c1002"/>
    </linearGradient>
    <linearGradient id="skinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fff5ed"/>
      <stop offset="100%" stop-color="#fde8d7"/>
    </linearGradient>
    <linearGradient id="clothGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f43f5e"/>
      <stop offset="100%" stop-color="#be123c"/>
    </linearGradient>
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Ambient Character Soft Halo -->
  <circle cx="200" cy="220" r="160" fill="url(#skinGrad)" opacity="0.08"/>

  <!-- Back Hair -->
  <path d="M 120 160 C 90 230, 80 340, 95 400 C 120 370, 135 320, 140 280 L 260 280 C 265 320, 280 370, 305 400 C 320 340, 310 230, 280 160 Z" fill="url(#hairGradAarushi)"/>

  <!-- Neck & Shoulders -->
  <path d="M 175 290 L 175 330 C 130 345, 90 380, 70 440 L 330 440 C 310 380, 270 345, 225 330 L 225 290 Z" fill="url(#clothGrad)"/>
  <!-- Cardigan Collar & Ribbon -->
  <path d="M 175 290 L 200 340 L 225 290 Z" fill="url(#skinGrad)"/>
  <path d="M 180 340 C 185 360, 175 380, 165 395 C 190 385, 200 365, 200 350 C 200 365, 210 385, 235 395 C 225 380, 215 360, 220 340 Z" fill="#ffffff" opacity="0.95"/>
  <circle cx="200" cy="345" r="7" fill="#fbbf24"/>

  <!-- Head Base -->
  <path d="M 130 200 C 125 260, 160 315, 200 315 C 240 315, 275 260, 270 200 C 268 140, 132 140, 130 200 Z" fill="url(#skinGrad)"/>

  <!-- Cute Ears -->
  <ellipse cx="128" cy="235" rx="9" ry="15" fill="#fde8d7"/>
  <ellipse cx="272" cy="235" rx="9" ry="15" fill="#fde8d7"/>

  <!-- Soft Blush Cheeks -->
  <ellipse cx="148" cy="254" rx="14" ry="7" fill="#fb7185" opacity="{blush_opacity}" filter="url(#softGlow)"/>
  <ellipse cx="252" cy="254" rx="14" ry="7" fill="#fb7185" opacity="{blush_opacity}" filter="url(#softGlow)"/>

  <!-- Tiny Cute Nose -->
  <circle cx="200" cy="265" r="2" fill="#be123c" opacity="0.4"/>

  <!-- Dynamic Eyes -->
  <g id="aarushi-eyes-left">
    {el_code}
  </g>
  <g id="aarushi-eyes-right">
    {er_code}
  </g>

  <!-- Dynamic Mouth -->
  <g id="aarushi-mouth">
    {m_code}
  </g>

  <!-- Front Hair & Bangs -->
  <path d="M 125 185 C 135 150, 165 130, 200 130 C 235 130, 265 150, 275 185 C 285 220, 280 260, 278 280 C 270 240, 260 210, 255 200 C 245 225, 230 245, 220 250 C 215 220, 205 200, 200 200 C 195 200, 185 220, 180 250 C 170 245, 155 225, 145 200 C 140 210, 130 240, 122 280 C 120 260, 115 220, 125 185 Z" fill="url(#hairGradAarushi)"/>

  <!-- Sakura Hairpin Accessory -->
  <g transform="translate(252, 175) scale(0.75)">
    <circle cx="0" cy="-12" r="8" fill="#fda4af"/>
    <circle cx="11" cy="-4" r="8" fill="#fda4af"/>
    <circle cx="7" cy="10" r="8" fill="#fda4af"/>
    <circle cx="-7" cy="10" r="8" fill="#fda4af"/>
    <circle cx="-11" cy="-4" r="8" fill="#fda4af"/>
    <circle cx="0" cy="0" r="5" fill="#fef08a"/>
  </g>
</svg>'''


def get_aoi_svg(expression: str) -> str:
    # Aoi: Cool, tech-savvy companion with cyan highlights & cyber headset
    mouths = {
        "neutral": '<path d="M 190 286 Q 200 291 210 286" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "listening": '<path d="M 190 286 Q 200 293 210 286" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "speaking": '<path d="M 188 281 Q 200 304 212 281 Z" fill="#0284c7"/><path d="M 192 292 Q 200 298 208 292 Z" fill="#38bdf8"/>',
        "happy": '<path d="M 186 282 Q 200 306 214 282 Z" fill="#0ea5e9"/>',
        "thinking": '<path d="M 191 285 Q 200 281 209 285" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "curious": '<path d="M 192 284 Q 202 292 212 284" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "surprised": '<ellipse cx="200" cy="285" rx="6" ry="10" fill="#0284c7"/>',
        "comforting": '<path d="M 190 284 Q 200 294 210 284" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "teasing": '<path d="M 188 283 Q 196 291 200 285 Q 204 291 212 283" stroke="#0284c7" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "sleepy": '<path d="M 192 288 Q 200 283 208 288" stroke="#0284c7" stroke-width="2.5" fill="none" stroke-linecap="round"/>',
    }

    eyes_left = {
        "neutral": '''
            <ellipse cx="160" cy="225" rx="14" ry="21" fill="#0c4a6e"/>
            <ellipse cx="160" cy="227" rx="12" ry="17" fill="url(#eyeGradAoi)"/>
            <circle cx="156" cy="217" r="5" fill="#ffffff"/>
            <circle cx="166" cy="232" r="2.5" fill="#ffffff"/>
            <path d="M 143 204 Q 160 196 177 204" stroke="#0f172a" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="160" cy="225" rx="15" ry="22" fill="#0c4a6e"/>
            <ellipse cx="160" cy="227" rx="13" ry="18" fill="url(#eyeGradAoi)"/>
            <circle cx="156" cy="217" r="5.5" fill="#ffffff"/>
            <path d="M 143 202 Q 160 193 177 202" stroke="#0f172a" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '<path d="M 146 226 Q 160 211 174 226" stroke="#0f172a" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
        "thinking": '<ellipse cx="163" cy="220" rx="13" ry="19" fill="#0c4a6e"/><ellipse cx="163" cy="222" rx="11" ry="15" fill="url(#eyeGradAoi)"/><circle cx="159" cy="214" r="4.5" fill="#ffffff"/>',
        "curious": '<ellipse cx="160" cy="223" rx="15" ry="22" fill="#0c4a6e"/><ellipse cx="160" cy="225" rx="13" ry="18" fill="url(#eyeGradAoi)"/><circle cx="156" cy="215" r="5" fill="#ffffff"/>',
        "surprised": '<ellipse cx="160" cy="222" rx="17" ry="24" fill="#0c4a6e"/><ellipse cx="160" cy="224" rx="15" ry="20" fill="url(#eyeGradAoi)"/><circle cx="154" cy="214" r="6" fill="#ffffff"/>',
        "comforting": '<path d="M 146 225 Q 160 214 174 225" stroke="#0f172a" stroke-width="4" fill="none" stroke-linecap="round"/>',
        "teasing": '<path d="M 145 224 Q 160 234 175 224" stroke="#0f172a" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
        "sleepy": '<path d="M 146 226 Q 160 230 174 226" stroke="#0f172a" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
    }

    eyes_right = {
        "neutral": '''
            <ellipse cx="240" cy="225" rx="14" ry="21" fill="#0c4a6e"/>
            <ellipse cx="240" cy="227" rx="12" ry="17" fill="url(#eyeGradAoi)"/>
            <circle cx="236" cy="217" r="5" fill="#ffffff"/>
            <circle cx="246" cy="232" r="2.5" fill="#ffffff"/>
            <path d="M 223 204 Q 240 196 257 204" stroke="#0f172a" stroke-width="4" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="240" cy="225" rx="15" ry="22" fill="#0c4a6e"/>
            <ellipse cx="240" cy="227" rx="13" ry="18" fill="url(#eyeGradAoi)"/>
            <circle cx="236" cy="217" r="5.5" fill="#ffffff"/>
            <path d="M 223 202 Q 240 193 257 202" stroke="#0f172a" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '<path d="M 226 226 Q 240 211 254 226" stroke="#0f172a" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
        "thinking": '<ellipse cx="243" cy="220" rx="13" ry="19" fill="#0c4a6e"/><ellipse cx="243" cy="222" rx="11" ry="15" fill="url(#eyeGradAoi)"/><circle cx="239" cy="214" r="4.5" fill="#ffffff"/>',
        "curious": '<ellipse cx="240" cy="223" rx="15" ry="22" fill="#0c4a6e"/><ellipse cx="240" cy="225" rx="13" ry="18" fill="url(#eyeGradAoi)"/><circle cx="236" cy="215" r="5" fill="#ffffff"/>',
        "surprised": '<ellipse cx="240" cy="222" rx="17" ry="24" fill="#0c4a6e"/><ellipse cx="240" cy="224" rx="15" ry="20" fill="url(#eyeGradAoi)"/><circle cx="234" cy="214" r="6" fill="#ffffff"/>',
        "comforting": '<path d="M 226 225 Q 240 214 254 225" stroke="#0f172a" stroke-width="4" fill="none" stroke-linecap="round"/>',
        "teasing": '<ellipse cx="240" cy="225" rx="14" ry="21" fill="#0c4a6e"/><ellipse cx="240" cy="227" rx="12" ry="17" fill="url(#eyeGradAoi)"/><circle cx="236" cy="217" r="5" fill="#ffffff"/>',
        "sleepy": '<path d="M 226 226 Q 240 230 254 226" stroke="#0f172a" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
    }

    m_code = mouths.get(expression, mouths["neutral"])
    el_code = eyes_left.get(expression, eyes_left["neutral"])
    er_code = eyes_right.get(expression, eyes_right["neutral"])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 480" width="100%" height="100%">
  <defs>
    <radialGradient id="eyeGradAoi" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#0369a1"/>
    </radialGradient>
    <linearGradient id="hairGradAoi" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="70%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <linearGradient id="aoiSkin" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e2e8f0"/>
    </linearGradient>
    <linearGradient id="aoiCloth" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>

  <!-- Back Hair -->
  <path d="M 120 160 C 85 240, 75 350, 90 410 C 115 375, 135 320, 140 280 L 260 280 C 265 320, 285 375, 310 410 C 325 350, 315 240, 280 160 Z" fill="url(#hairGradAoi)"/>

  <!-- Tech Cyber Headset Band -->
  <path d="M 120 220 C 115 150, 150 115, 200 115 C 250 115, 285 150, 280 220" stroke="#0ea5e9" stroke-width="7" fill="none"/>

  <!-- Neck & Tech Hoodie -->
  <path d="M 175 290 L 175 330 C 130 345, 90 380, 70 440 L 330 440 C 310 380, 270 345, 225 330 L 225 290 Z" fill="url(#aoiCloth)"/>
  <path d="M 175 290 L 200 335 L 225 290 Z" fill="url(#aoiSkin)"/>
  <path d="M 120 400 L 200 440 L 280 400" stroke="#0ea5e9" stroke-width="3" fill="none" opacity="0.8"/>

  <!-- Head Base -->
  <path d="M 130 200 C 125 260, 160 315, 200 315 C 240 315, 275 260, 270 200 C 268 140, 132 140, 130 200 Z" fill="url(#aoiSkin)"/>

  <!-- Ears & Earpieces -->
  <ellipse cx="128" cy="235" rx="9" ry="15" fill="#e2e8f0"/>
  <ellipse cx="272" cy="235" rx="9" ry="15" fill="#e2e8f0"/>
  <rect x="114" y="215" width="16" height="30" rx="8" fill="#0284c7"/>
  <rect x="270" y="215" width="16" height="30" rx="8" fill="#0284c7"/>
  <circle cx="278" cy="230" r="4" fill="#38bdf8"/>

  <!-- Soft Blush -->
  <ellipse cx="148" cy="254" rx="12" ry="6" fill="#38bdf8" opacity="0.25"/>
  <ellipse cx="252" cy="254" rx="12" ry="6" fill="#38bdf8" opacity="0.25"/>

  <!-- Nose -->
  <circle cx="200" cy="265" r="2" fill="#0284c7" opacity="0.4"/>

  <!-- Dynamic Eyes -->
  <g id="aoi-eyes-left">{el_code}</g>
  <g id="aoi-eyes-right">{er_code}</g>

  <!-- Dynamic Mouth -->
  <g id="aoi-mouth">{m_code}</g>

  <!-- Front Hair -->
  <path d="M 125 185 C 135 150, 165 130, 200 130 C 235 130, 265 150, 275 185 C 285 220, 275 250, 270 270 C 265 235, 255 210, 250 200 C 240 225, 225 240, 215 245 C 210 220, 202 200, 200 200 C 198 200, 190 220, 185 245 C 175 240, 160 225, 150 200 C 145 210, 135 235, 130 270 C 125 250, 115 220, 125 185 Z" fill="url(#hairGradAoi)"/>
  <!-- Cyan Hair Highlight Strand -->
  <path d="M 148 160 Q 155 210 162 235" stroke="#38bdf8" stroke-width="3" fill="none" opacity="0.8"/>
</svg>'''


def get_kenji_svg(expression: str) -> str:
    # Kenji: Friendly anime male companion with energetic green eyes
    mouths = {
        "neutral": '<path d="M 188 286 Q 200 292 212 286" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "listening": '<path d="M 190 286 Q 200 293 210 286" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "speaking": '<path d="M 186 281 Q 200 305 214 281 Z" fill="#047857"/><path d="M 191 292 Q 200 298 209 292 Z" fill="#6ee7b7"/>',
        "happy": '<path d="M 184 280 Q 200 307 216 280 Z" fill="#10b981"/>',
        "thinking": '<path d="M 191 285 Q 200 280 209 285" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "curious": '<path d="M 191 284 Q 202 292 213 284" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "surprised": '<ellipse cx="200" cy="285" rx="7" ry="11" fill="#047857"/>',
        "comforting": '<path d="M 188 284 Q 200 294 212 284" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "teasing": '<path d="M 188 283 Q 196 291 200 285 Q 204 291 212 283" stroke="#065f46" stroke-width="3" fill="none" stroke-linecap="round"/>',
        "sleepy": '<path d="M 192 288 Q 200 283 208 288" stroke="#065f46" stroke-width="2.5" fill="none" stroke-linecap="round"/>',
    }

    eyes_left = {
        "neutral": '''
            <ellipse cx="160" cy="225" rx="14" ry="20" fill="#064e3b"/>
            <ellipse cx="160" cy="227" rx="12" ry="16" fill="url(#eyeGradKenji)"/>
            <circle cx="156" cy="217" r="5" fill="#ffffff"/>
            <path d="M 142 204 Q 160 195 178 204" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="160" cy="225" rx="15" ry="21" fill="#064e3b"/>
            <ellipse cx="160" cy="227" rx="13" ry="17" fill="url(#eyeGradKenji)"/>
            <circle cx="156" cy="217" r="5.5" fill="#ffffff"/>
            <path d="M 142 201 Q 160 192 178 201" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '<path d="M 145 226 Q 160 210 175 226" stroke="#1f2937" stroke-width="5" fill="none" stroke-linecap="round"/>',
        "thinking": '<ellipse cx="163" cy="220" rx="13" ry="18" fill="#064e3b"/><ellipse cx="163" cy="222" rx="11" ry="14" fill="url(#eyeGradKenji)"/><circle cx="159" cy="214" r="4.5" fill="#ffffff"/>',
        "curious": '<ellipse cx="160" cy="223" rx="15" ry="21" fill="#064e3b"/><ellipse cx="160" cy="225" rx="13" ry="17" fill="url(#eyeGradKenji)"/><circle cx="156" cy="215" r="5" fill="#ffffff"/>',
        "surprised": '<ellipse cx="160" cy="222" rx="16" ry="23" fill="#064e3b"/><ellipse cx="160" cy="224" rx="14" ry="19" fill="url(#eyeGradKenji)"/><circle cx="154" cy="214" r="6" fill="#ffffff"/>',
        "comforting": '<path d="M 145 225 Q 160 213 175 225" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
        "teasing": '<path d="M 144 224 Q 160 234 176 224" stroke="#1f2937" stroke-width="5" fill="none" stroke-linecap="round"/>',
        "sleepy": '<path d="M 145 226 Q 160 230 175 226" stroke="#1f2937" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
    }

    eyes_right = {
        "neutral": '''
            <ellipse cx="240" cy="225" rx="14" ry="20" fill="#064e3b"/>
            <ellipse cx="240" cy="227" rx="12" ry="16" fill="url(#eyeGradKenji)"/>
            <circle cx="236" cy="217" r="5" fill="#ffffff"/>
            <path d="M 222 204 Q 240 195 258 204" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "listening": '''
            <ellipse cx="240" cy="225" rx="15" ry="21" fill="#064e3b"/>
            <ellipse cx="240" cy="227" rx="13" ry="17" fill="url(#eyeGradKenji)"/>
            <circle cx="236" cy="217" r="5.5" fill="#ffffff"/>
            <path d="M 222 201 Q 240 192 258 201" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>
        ''',
        "happy": '<path d="M 225 226 Q 240 210 255 226" stroke="#1f2937" stroke-width="5" fill="none" stroke-linecap="round"/>',
        "thinking": '<ellipse cx="243" cy="220" rx="13" ry="18" fill="#064e3b"/><ellipse cx="243" cy="222" rx="11" ry="14" fill="url(#eyeGradKenji)"/><circle cx="239" cy="214" r="4.5" fill="#ffffff"/>',
        "curious": '<ellipse cx="240" cy="223" rx="15" ry="21" fill="#064e3b"/><ellipse cx="240" cy="225" rx="13" ry="17" fill="url(#eyeGradKenji)"/><circle cx="236" cy="215" r="5" fill="#ffffff"/>',
        "surprised": '<ellipse cx="240" cy="222" rx="16" ry="23" fill="#064e3b"/><ellipse cx="240" cy="224" rx="14" ry="19" fill="url(#eyeGradKenji)"/><circle cx="234" cy="214" r="6" fill="#ffffff"/>',
        "comforting": '<path d="M 225 225 Q 240 213 255 225" stroke="#1f2937" stroke-width="4.5" fill="none" stroke-linecap="round"/>',
        "teasing": '<ellipse cx="240" cy="225" rx="14" ry="20" fill="#064e3b"/><ellipse cx="240" cy="227" rx="12" ry="16" fill="url(#eyeGradKenji)"/><circle cx="236" cy="217" r="5" fill="#ffffff"/>',
        "sleepy": '<path d="M 225 226 Q 240 230 255 226" stroke="#1f2937" stroke-width="3.5" fill="none" stroke-linecap="round"/>',
    }

    m_code = mouths.get(expression, mouths["neutral"])
    el_code = eyes_left.get(expression, eyes_left["neutral"])
    er_code = eyes_right.get(expression, eyes_right["neutral"])

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 480" width="100%" height="100%">
  <defs>
    <radialGradient id="eyeGradKenji" cx="50%" cy="40%" r="50%">
      <stop offset="0%" stop-color="#34d399"/>
      <stop offset="50%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#047857"/>
    </radialGradient>
    <linearGradient id="hairGradKenji" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="60%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="kenjiSkin" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fff7ed"/>
      <stop offset="100%" stop-color="#fed7aa"/>
    </linearGradient>
  </defs>

  <!-- Neck & Casual Jacket -->
  <path d="M 175 290 L 175 330 C 130 345, 90 380, 70 440 L 330 440 C 310 380, 270 345, 225 330 L 225 290 Z" fill="#1e293b"/>
  <path d="M 175 290 L 200 335 L 225 290 Z" fill="url(#kenjiSkin)"/>
  <path d="M 195 335 L 195 440 L 205 440 L 205 335 Z" fill="#10b981"/>

  <!-- Head Base -->
  <path d="M 130 195 C 125 260, 160 315, 200 315 C 240 315, 275 260, 270 195 C 268 135, 132 135, 130 195 Z" fill="url(#kenjiSkin)"/>

  <!-- Ears -->
  <ellipse cx="128" cy="235" rx="9" ry="15" fill="#fed7aa"/>
  <ellipse cx="272" cy="235" rx="9" ry="15" fill="#fed7aa"/>

  <!-- Soft Cheek Flush -->
  <ellipse cx="148" cy="254" rx="12" ry="6" fill="#f43f5e" opacity="0.25"/>
  <ellipse cx="252" cy="254" rx="12" ry="6" fill="#f43f5e" opacity="0.25"/>

  <!-- Nose -->
  <circle cx="200" cy="265" r="2.5" fill="#047857" opacity="0.4"/>

  <!-- Dynamic Eyes -->
  <g id="kenji-eyes-left">{el_code}</g>
  <g id="kenji-eyes-right">{er_code}</g>

  <!-- Dynamic Mouth -->
  <g id="kenji-mouth">{m_code}</g>

  <!-- Stylish Short Hair -->
  <path d="M 125 185 C 130 140, 160 120, 200 120 C 240 120, 270 140, 275 185 C 285 205, 280 230, 275 245 C 270 215, 260 195, 255 185 C 245 205, 235 220, 225 225 C 218 200, 205 185, 200 185 C 195 185, 185 200, 178 225 C 170 220, 155 205, 145 185 C 140 195, 130 215, 125 245 C 120 230, 115 205, 125 185 Z" fill="url(#hairGradKenji)"/>
</svg>'''


EXPRESSIONS = [
    "neutral", "listening", "speaking", "happy", "thinking",
    "curious", "surprised", "comforting", "teasing", "sleepy"
]


def generate_all():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    char_defs = [
        ("aarushi", "Aarushi", "female", "Warm, caring, emotionally expressive anime girl companion", get_aarushi_svg),
        ("aoi", "Aoi", "female", "Cool, analytical, tech-savvy anime companion with cyber headset", get_aoi_svg),
        ("kenji", "Kenji", "male", "Friendly, energetic, witty anime male companion", get_kenji_svg),
    ]

    manifest = {"characters": []}

    for char_id, display_name, gender, bio, generator_fn in char_defs:
        char_dir = STATIC_DIR / char_id
        char_dir.mkdir(parents=True, exist_ok=True)
        expr_map = {}

        for expr in EXPRESSIONS:
            svg_content = generator_fn(expr)
            file_name = f"{expr}.svg"
            (char_dir / file_name).write_text(svg_content)
            expr_map[expr] = f"/static/characters/{char_id}/{file_name}"

        # Additional aliases for expression fallback
        expr_map["idle"] = expr_map["neutral"]
        expr_map["excited"] = expr_map["happy"]
        expr_map["blushing"] = expr_map["teasing"]
        expr_map["shy"] = expr_map["teasing"]
        expr_map["confused"] = expr_map["curious"]
        expr_map["sad"] = expr_map["comforting"]
        expr_map["encouraging"] = expr_map["happy"]
        expr_map["interrupted"] = expr_map["listening"]

        manifest["characters"].append({
            "id": char_id,
            "name": display_name,
            "displayName": display_name,
            "role": bio,
            "gender": gender,
            "bio": bio,
            "style": "anime_vector_hd",
            "defaultExpression": "neutral",
            "expressions": expr_map,
            "license": {
                "name": "Creative Commons Zero (CC0) / MIT Permissive Open Asset",
                "source": "GDR-IDE Native Character Art System",
                "attribution": "GDR-IDE Character Design Studio"
            }
        })

    # Write manifest.json
    manifest_file = STATIC_DIR / "characters.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ Generated {len(char_defs)} characters with {len(EXPRESSIONS)} expressions each in {STATIC_DIR}")
    print(f"📄 Manifest written to {manifest_file}")

if __name__ == "__main__":
    generate_all()
