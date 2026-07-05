#Github.com/Vasusen-code
import os, base64, mimetypes, itertools, time, httpx
from decouple import config

GEMINI_KEYS = [k.strip() for k in config("GEMINI_KEYS", default="").split(",") if k.strip()]
_key_cycle = itertools.cycle(GEMINI_KEYS) if GEMINI_KEYS else None

# key -> unix timestamp until which it's considered dead (quota exceeded)
_dead_until = {}
_COOLDOWN = 3600  # 1 hour before retrying a quota-exceeded key

IDENTITY_TEXT = (
    "Amir Hamza Rafi\n"
    "MBBS 4th Year (SOMC)\n"
    "Founder, ATLAS"
)

def _next_key():
    if not _key_cycle:
        raise RuntimeError("No GEMINI_KEYS configured.")
    return next(_key_cycle)

def _mark_dead(key):
    _dead_until[key] = time.time() + _COOLDOWN

def _is_dead(key):
    until = _dead_until.get(key)
    return until is not None and time.time() < until

def _file_to_part(path):
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "image/jpeg"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"inline_data": {"mime_type": mime, "data": data}}

async def generate_thumbnail(sample_paths, photo_paths, prompt_text, topic_name, out_path):
    """
    sample_paths: reference thumbnail images (style/font/bg reference only)
    photo_paths: user's own photos (always used as the subject)
    prompt_text: extra instructions set via /prompt
    topic_name: topic given with /new
    """
    parts = [{
        "text": (
            "You are an expert YouTube/course thumbnail designer. "
            "Analyze the following reference thumbnail images for their font style, "
            "font color, background style, layout and visual details. "
            "Then create ONE brand-new thumbnail that follows the same visual style "
            "(font, font color, background, layout) but uses the provided person photo "
            "as the subject. Do not copy any text from the references verbatim; use the "
            "new topic and identity text provided below instead.\n\n"
            f"Topic: {topic_name}\n\n"
            f"Identity text to include on the thumbnail:\n{IDENTITY_TEXT}\n\n"
            + (f"Extra instructions: {prompt_text}\n\n" if prompt_text else "")
            + "Reference thumbnails (style guide only, do not reuse their text):"
        )
    }]
    for p in sample_paths:
        parts.append(_file_to_part(p))

    parts.append({"text": "Person photo to use as the subject (always use this real photo, keep the face accurate):"})
    for p in photo_paths:
        parts.append(_file_to_part(p))

    parts.append({"text": "Now generate the final thumbnail image."})

    last_err = None
    attempts = len(GEMINI_KEYS) or 1
    tried = 0
    for _ in range(attempts):
        key = _next_key()
        if _is_dead(key):
            continue
        tried += 1
        model_names = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
        got_429 = False
        for model_name in model_names:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={key}"
            )
            payload = {"contents": [{"parts": parts}]}
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    r = await client.post(url, json=payload)
                if r.status_code == 404:
                    continue
                if r.status_code == 429:
                    last_err = f"429: {r.text[:500]}"
                    got_429 = True
                    continue
                if r.status_code == 403:
                    last_err = f"403: {r.text[:300]}"
                    continue
                if r.status_code != 200:
                    last_err = f"{r.status_code}: {r.text[:300]}"
                    continue
                data = r.json()
                cands = data.get("candidates", [])
                if not cands:
                    last_err = "No candidates returned."
                    continue
                out_parts = cands[0].get("content", {}).get("parts", [])
                for part in out_parts:
                    inline = part.get("inline_data") or part.get("inlineData")
                    if inline and inline.get("data"):
                        img_bytes = base64.b64decode(inline["data"])
                        with open(out_path, "wb") as f:
                            f.write(img_bytes)
                        return out_path
                last_err = "No image data in response."
            except Exception as e:
                last_err = str(e)
                continue
        if got_429:
            _mark_dead(key)
    if tried == 0:
        return await _generate_with_pollinations(prompt_text, topic_name, out_path)
    raise_err = f"Thumbnail generation failed: {last_err}"
    try:
        return await _generate_with_pollinations(prompt_text, topic_name, out_path)
    except Exception:
        raise RuntimeError(raise_err)

async def _generate_with_pollinations(prompt_text, topic_name, out_path):
    prompt = (
        f"Professional YouTube course thumbnail, topic: {topic_name}, "
        f"bold text, high contrast, modern education style. {prompt_text or ''}"
    ).strip()
    url = f"https://image.pollinations.ai/prompt/{httpx.QueryParams({'p': prompt})['p']}"
    params = {"width": 1920, "height": 1080, "nologo": "true"}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200 or not r.content:
            raise RuntimeError("Pollinations fallback also failed.")
        with open(out_path, "wb") as f:
            f.write(r.content)
    return out_path
