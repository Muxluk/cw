from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from app.services.utils import seconds_to_tc


def _group_boundaries(boundaries: list[float], duration: float, min_scene: float) -> list[dict[str, Any]]:
    points = [0.0] + sorted(set(max(0.0, min(duration, b)) for b in boundaries if b > 0.0))
    if not points or points[-1] < duration:
        points.append(duration)

    scenes: list[dict[str, Any]] = []
    start = points[0]
    index = 1
    for boundary in points[1:]:
        if boundary - start < min_scene:
            continue
        scenes.append({
            "scene_index": index,
            "start": round(start, 3),
            "end": round(boundary, 3),
            "start_tc": seconds_to_tc(start),
            "end_tc": seconds_to_tc(boundary),
        })
        start = boundary
        index += 1
    if not scenes and duration > 0:
        scenes.append({
            "scene_index": 1,
            "start": 0.0,
            "end": round(duration, 3),
            "start_tc": seconds_to_tc(0.0),
            "end_tc": seconds_to_tc(duration),
        })
    return scenes


def _detect_with_transnet(video_path: Path, duration: float, min_scene: float) -> list[dict[str, Any]] | None:
    try:
        import torch
        from transnetv2_pytorch import TransNetV2

        model = TransNetV2(device='cpu')
        model.eval()

        with torch.no_grad():
            predictions = model.predict_video(str(video_path))
            raw_probs = np.array(predictions).flatten()
            
        sigma = 1.5
        smoothed = gaussian_filter1d(raw_probs, sigma=sigma)
        signal_volatility = float(np.std(np.diff(raw_probs)))
        base_k = 3.0
        k = round(max(3.0, min(5.5, base_k + signal_volatility * 25.0)), 2)
        print(f"[TransNetV2] Аналіз динаміки відео. Волатильність: {signal_volatility:.4f} -> Адаптивний k = {k}")
        
        threshold = np.mean(smoothed) + (k * np.std(smoothed))
        peaks, _ = find_peaks(smoothed, height=threshold)
        fps = 25.0 
        boundaries = [float(p / fps) for p in peaks]

        return _group_boundaries(boundaries, duration, min_scene)

    except Exception as e:
        print(f"[TransNetV2] помилка: {type(e).__name__}: {e}")
        return None


def _detect_with_opencv(video_path: Path, duration: float, threshold: float, min_scene: float) -> list[dict[str, Any]]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_index = 0
    prev_hist = None
    boundaries: list[float] = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % max(1, int(fps // 2)) != 0:
            frame_index += 1
            continue
        small = cv2.resize(frame, (160, 90))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        if prev_hist is not None:
            diff = 1 - cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            if diff >= threshold:
                boundaries.append(frame_index / fps)
        prev_hist = hist
        frame_index += 1

    cap.release()
    return _group_boundaries(boundaries, duration, min_scene)


def detect_scenes(video_path: Path, duration: float, threshold: float, min_scene: float) -> dict[str, Any]:
    transnet_result = _detect_with_transnet(video_path, duration, min_scene)
    if transnet_result:
        return {"engine": "TransNetV2", "scenes": transnet_result}

    fallback_result = _detect_with_opencv(video_path, duration, threshold, min_scene)
    return {"engine": "OpenCV-fallback", "scenes": fallback_result}