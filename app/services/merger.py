from __future__ import annotations

import re
from collections import Counter
from typing import Any

from langdetect import detect, LangDetectException
from stop_words import get_stop_words

from app.services.utils import seconds_to_tc

def extract_dynamic_keywords(text: str, top_n: int = 15) -> list[str]:
    if not text.strip():
        return []

    try:
        lang_code = detect(text)
    except LangDetectException:
        lang_code = "unknown"

    stop_words_set = set()
    if lang_code != "unknown":
        try:
            stop_words_set = set(get_stop_words(lang_code))
        except Exception:
            pass

    words = re.findall(r'\b[а-яА-ЯіІїЇєЄґҐa-zA-Z]{5,}\b', text.lower())

    filtered_words = [
        w for w in words 
        if w not in stop_words_set
    ]

    counts = Counter(filtered_words)
    return [word for word, count in counts.most_common(top_n)]

def _trim_to_first_sentence(text: str) -> str:
    if not text:
        return text
    dot_index = text.find(".")
    if dot_index == -1:
        return text[0].upper() + text[1:]
    sentence = text[:dot_index + 1].strip()
    return sentence[0].upper() + sentence[1:]

def _label_scene(scene: dict[str, Any], texts: list[str]) -> str:
    joined = " ".join(texts).strip()
    if not joined:
        return f"Сцена {scene['scene_index']}: візуальна подія"
    lowered = joined.lower()
    if any(word in lowered for word in ["завдання", "task", "required"]):
        return f"Сцена {scene['scene_index']}: постановка завдання"
    return f"Сцена {scene['scene_index']}: змістовий фрагмент"


def merge_results(
    meta: dict[str, Any],
    scenes: list[dict[str, Any]],
    transcript_segments: list[dict[str, Any]],
    min_scene_interval: float = 90.0,
) -> list[dict[str, Any]]:
    full_video_text = " ".join([seg.get("text", "") for seg in transcript_segments])
    global_keywords = extract_dynamic_keywords(full_video_text, top_n=15)
    global_kw_set = set(global_keywords)

    meta["global_theme_keywords"] = global_keywords
    print(f"Ключові теми відео: {', '.join(global_keywords)}")

    merged_scenes = []
    last_scene_time: float = -min_scene_interval

    for scene in scenes:
        if scene["start"] - last_scene_time < min_scene_interval:
            continue

        related = [
            seg for seg in transcript_segments
            if seg["end"] >= scene["start"] and seg["start"] <= scene["end"]
        ]
        text_list = [seg["text"] for seg in related if seg.get("text")]
        speech_excerpt = " ".join(text_list).strip()

        scene_keywords = extract_dynamic_keywords(speech_excerpt, top_n=7)

        if speech_excerpt and not any(w in global_kw_set for w in scene_keywords):
            continue

        merged_scenes.append({
            "scene_index": scene["scene_index"],
            "title": _label_scene(scene, text_list),
            "start": scene["start"],
            "end": scene["end"],
            "start_tc": scene["start_tc"],
            "end_tc": scene["end_tc"],
            "speech_excerpt":  _trim_to_first_sentence(speech_excerpt),
            "scene_keywords": scene_keywords,
            "speech_segments_count": len(related),
        })

        last_scene_time = scene["start"]

    return merged_scenes