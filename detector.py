"""
detector.py — Real AI Detection using 3 FREE sources

NO PAID APIs. Everything here is 100% free forever.

Sources used:
  1. HuggingFace Model 1 — Organika/sdxl-detector
     Detects Stable Diffusion / SDXL generated images

  2. HuggingFace Model 2 — haywoodsloan/autotrain-ai-vs-human-diffusion
     Trained on broader AI vs human image dataset

  3. Local EXIF Metadata Scanner — No API needed at all
     Scans image metadata for AI software signatures
     Works 100% offline, completely free forever

Get your FREE HuggingFace token (one token works for ALL models):
  1. Go to https://huggingface.co/settings/tokens
  2. Click New Token → Read access → Copy it
  3. Paste in .env as HUGGINGFACE_API_KEY=hf_xxxx
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "YOUR_HF_KEY")
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Updated router URLs — correct HuggingFace inference endpoint
MODEL_1 = "https://router.huggingface.co/hf-inference/models/Organika/sdxl-detector"
MODEL_2 = "https://router.huggingface.co/hf-inference/models/umm-maybe/AI-image-detector"


# ──────────────────────────────────────────────
# HELPER — read image or extract video frame
# ──────────────────────────────────────────────
def get_image_bytes(file_path: str, ext: str) -> bytes:
    video_exts = [".mp4", ".mov", ".avi"]
    if ext in video_exts:
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame_path = file_path + "_frame.jpg"
                cv2.imwrite(frame_path, frame)
                with open(frame_path, "rb") as f:
                    return f.read()
            else:
                raise ValueError("Could not read video frame")
        except Exception as e:
            raise ValueError(f"Video frame extraction failed: {e}")
    else:
        with open(file_path, "rb") as f:
            return f.read()


# ──────────────────────────────────────────────
# HELPER — parse HuggingFace classifier response
# ──────────────────────────────────────────────
def parse_hf_response(result) -> float:
    ai_labels   = ["artificial", "ai", "fake", "generated", "sd", "machine"]
    real_labels = ["real", "human", "authentic", "natural"]

    if isinstance(result, list):
        for item in result:
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0))
            if any(al in label for al in ai_labels):
                return round(score * 100, 2)
            if any(rl in label for rl in real_labels):
                return round((1 - score) * 100, 2)
    return 50.0


# ──────────────────────────────────────────────
# HELPER — call HuggingFace with Content-Type + auto-retry
# (models sometimes need warm-up time)
# ──────────────────────────────────────────────
async def call_hf_model(url: str, image_bytes: bytes, wait: int = 20):
    # Content-Type header is required — without it API returns 400 error
    headers = {
        **HF_HEADERS,
        "Content-Type": "image/jpeg"
    }
    for attempt in range(3):  # retry up to 3 times
        async with httpx.AsyncClient(timeout=65) as client:
            resp = await client.post(url, headers=headers, content=image_bytes)

        # Empty response = model still loading
        if resp.content == b"" or len(resp.content) < 5:
            await asyncio.sleep(wait)
            continue

        result = resp.json()

        if isinstance(result, dict) and "error" in result:
            if "loading" in result["error"].lower():
                await asyncio.sleep(wait)
                continue
            else:
                raise ValueError(result["error"])

        return result

    raise ValueError("Model timed out — try again in 65 seconds")


# ──────────────────────────────────────────────
# DETECTOR 1 — SDXL Detector (HuggingFace)
# Organika/sdxl-detector
# Trained specifically on Stable Diffusion XL images
# ──────────────────────────────────────────────
async def api_deepvision(file_path: str, ext: str):
    try:
        if HF_API_KEY == "YOUR_HF_KEY":
            raise ValueError("HuggingFace API key not set — add to .env file")

        image_bytes = get_image_bytes(file_path, ext)
        result      = await call_hf_model(MODEL_1, image_bytes, wait=30)
        ai_score    = parse_hf_response(result)
        status      = "Failed" if ai_score > 50 else "Passed"
        return {"status": status, "confidence": ai_score}

    except Exception as e:
        return {"status": "Error", "confidence": 0.0, "_error": str(e)}


# ──────────────────────────────────────────────
# DETECTOR 2 — EXIF Metadata Forensics (local)
# No API key needed — works completely offline
# Checks for AI software signatures in metadata
# ──────────────────────────────────────────────
async def api_metadata(file_path: str, ext: str):
    try:
        ai_signatures = [
            "stable diffusion", "midjourney", "dall-e", "dalle",
            "firefly", "dreamstudio", "novelai", "automatic1111",
            "comfyui", "runway", "pika", "sora", "kling",
            "adobe firefly", "canva ai", "nightcafe", "artbreeder",
            "deepdream", "wombo", "jasper art", "fotor"
        ]

        score  = 100.0
        flags  = []
        status = "Verified"

        image_exts = [".jpg", ".jpeg", ".png", ".webp"]

        if ext in image_exts:
            from PIL import Image
            img  = Image.open(file_path)
            info = img.info or {}
            exif_data = {}

            try:
                raw_exif = img._getexif()
                if raw_exif:
                    from PIL.ExifTags import TAGS
                    exif_data = {TAGS.get(k, k): str(v) for k, v in raw_exif.items()}
            except Exception:
                pass

            # Check EXIF Software tag
            software = exif_data.get("Software", "").lower()
            if software and any(sig in software for sig in ai_signatures):
                flags.append(f"AI software in EXIF: {software}")
                score -= 70

            # Check PNG text chunks (SD embeds prompts here)
            for key, val in info.items():
                val_lower = str(val).lower()
                if key.lower() in ["parameters", "prompt", "workflow", "comment"]:
                    if any(sig in val_lower for sig in ai_signatures):
                        flags.append(f"AI prompt in metadata: '{key}'")
                        score -= 60
                        break
                    elif len(str(val)) > 100:
                        flags.append("Long embedded text (possible AI prompt)")
                        score -= 30
                        break

            # Missing camera info in JPEG = suspicious
            if ext in [".jpg", ".jpeg"]:
                if not exif_data.get("Make") and not exif_data.get("Model"):
                    flags.append("No camera info in EXIF")
                    score -= 15
                if not exif_data.get("DateTimeOriginal"):
                    flags.append("Missing capture timestamp")
                    score -= 10

        else:
            # Video basic check
            ai_confidence = 20.0
            if os.path.getsize(file_path) < 500_000:
                ai_confidence = 40.0
            return {"status": "Verified", "confidence": ai_confidence}

        score         = max(0.0, round(score, 2))
        ai_confidence = round(100 - score, 2)
        status        = "Failed" if ai_confidence > 50 else "Verified"

        return {"status": status, "confidence": ai_confidence, "_flags": flags}

    except Exception as e:
        return {"status": "Error", "confidence": 0.0, "_error": str(e)}


# ──────────────────────────────────────────────
# DETECTOR 3 — AI vs Human Diffusion (HuggingFace)
# haywoodsloan/autotrain-ai-vs-human-diffusion
# Trained on broader dataset of AI vs real images
# ──────────────────────────────────────────────
async def api_neural(file_path: str, ext: str):
    try:
        if HF_API_KEY == "YOUR_HF_KEY":
            raise ValueError("HuggingFace API key not set — add to .env file")

        image_bytes = get_image_bytes(file_path, ext)
        result      = await call_hf_model(MODEL_2, image_bytes, wait=30)
        ai_score    = parse_hf_response(result)
        status      = "Failed" if ai_score > 50 else "Passed"
        return {"status": status, "confidence": ai_score}

    except Exception as e:
        return {"status": "Error", "confidence": 0.0, "_error": str(e)}


# ──────────────────────────────────────────────
# AGGREGATOR — fires all 3 in parallel
# ──────────────────────────────────────────────
async def analyze_media_concurrently(file_path: str, ext: str = ".jpg"):
    """
    Runs all 3 detectors at the SAME TIME using asyncio.gather().

    Sequential would take: 20s + 0.1s + 20s = ~40 seconds
    Concurrent takes:      max(20s, 0.1s, 20s) = ~20 seconds

    This is the key technical concept to mention in interviews.
    """
    results = await asyncio.gather(
        api_deepvision(file_path, ext),
        api_metadata(file_path, ext),
        api_neural(file_path, ext),
        return_exceptions=True
    )

    def safe(r):
        if isinstance(r, Exception):
            return {"status": "Error", "confidence": 0.0, "_error": str(r)}
        return r

    report = {
        "DeepVision": safe(results[0]),
        "Metadata":   safe(results[1]),
        "Neural":     safe(results[2]),
    }

    errors = {
        key: val.get("_error", "")
        for key, val in report.items()
        if val.get("_error")
    }

    # ── WEIGHTED SCORING ──────────────────────────────
    # DeepVision is most accurate → 50% weight
    # Neural is second → 30% weight
    # Metadata is supporting evidence → 20% weight
    weights = {"DeepVision": 0.5, "Metadata": 0.2, "Neural": 0.3}

    weighted_sum  = 0.0
    weight_total  = 0.0

    for key, val in report.items():
        if val["status"] not in ["Error"] and val["confidence"] > 0:
            w             = weights.get(key, 0.33)
            weighted_sum += val["confidence"] * w
            weight_total += w

    avg_score = round(weighted_sum / weight_total, 2) if weight_total > 0 else 0.0

    # If ANY detector flags it → mark as AI-Generated
    is_ai = any(
        v["status"] in ["Failed", "AI-Generated"]
        for v in report.values()
        if v["status"] != "Error"
    )

    return {
        "overall_prediction": "AI-Generated" if is_ai else "Authentic",
        "overall_score":      avg_score,
        "details":            report,
        "errors":             errors,
    }