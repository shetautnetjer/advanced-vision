"""Vision adapter abstraction for screenshot interpretation.

The default adapter prefers a lightweight local YOLO detector when available and
falls back to a conservative no-op adapter when the computer-vision stack is
missing.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import get_settings
from .schemas import ActionProposal


class VisionAdapter:
    """Simple interface for screenshot analysis."""

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        raise NotImplementedError


class StubVisionAdapter(VisionAdapter):
    """Safe fallback when the local detector stack is unavailable."""

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        return ActionProposal(
            action_type="noop",
            confidence=0.1,
            rationale=(
                "Computer-vision adapter unavailable, using safe fallback. "
                f"Received task='{task}' for image_path='{image_path}'."
            ),
        )


STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "bar",
    "box",
    "button",
    "click",
    "find",
    "focus",
    "for",
    "go",
    "icon",
    "in",
    "is",
    "my",
    "of",
    "on",
    "open",
    "press",
    "screen",
    "select",
    "show",
    "tab",
    "the",
    "this",
    "to",
    "url",
    "website",
    "window",
}


def _normalize_text(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(normalized.split())


def _task_keywords(task: str) -> set[str]:
    return {
        token
        for token in _normalize_text(task).split()
        if token and token not in STOPWORDS and len(token) >= 2
    }


def _task_phrases(task: str) -> list[str]:
    phrases = []
    for quoted in re.findall(r"['\"]([^'\"]{2,})['\"]", task):
        normalized = _normalize_text(quoted)
        if normalized:
            phrases.append(normalized)

    keywords = sorted(_task_keywords(task))
    if keywords:
        phrases.append(" ".join(keywords))
    normalized_task = _normalize_text(task)
    if normalized_task:
        phrases.append(normalized_task)
    return list(dict.fromkeys(phrases))


def _center_from_box(box: list[list[float]]) -> tuple[int, int]:
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return (int(sum(xs) / len(xs)), int(sum(ys) / len(ys)))


class RapidOcrAdapter(VisionAdapter):
    """OCR-backed adapter for finding visible UI text."""

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_engine() -> Any:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore

        return RapidOCR()

    def _extract_text_regions(self, image_path: str) -> list[dict[str, Any]]:
        engine = self._load_engine()
        results, _ = engine(image_path)
        detections: list[dict[str, Any]] = []
        for item in results or []:
            if len(item) < 3:
                continue
            box, text, confidence = item
            normalized_text = _normalize_text(str(text))
            if not normalized_text or len(normalized_text) < 2:
                continue
            center_x, center_y = _center_from_box(box)
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            detections.append(
                {
                    "text": str(text),
                    "normalized_text": normalized_text,
                    "confidence": float(confidence),
                    "center_x": center_x,
                    "center_y": center_y,
                    "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                }
            )
        return detections

    def _score_detection(self, detection: dict[str, Any], task: str) -> float:
        detection_text = detection["normalized_text"]
        task_keywords = _task_keywords(task)
        if not task_keywords:
            return 0.0

        detection_tokens = set(detection_text.split())
        overlap = len(task_keywords & detection_tokens)
        if overlap == 0:
            for phrase in _task_phrases(task):
                if phrase and (phrase in detection_text or detection_text in phrase):
                    overlap = max(overlap, 1)
                    break

        if overlap == 0:
            return 0.0

        token_score = overlap / max(len(task_keywords), 1)
        confidence_score = min(max(detection["confidence"], 0.0), 1.0)
        length_bonus = min(len(detection_text.split()) / 4.0, 1.0) * 0.1
        return token_score * 0.7 + confidence_score * 0.2 + length_bonus

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        detections = self._extract_text_regions(image_path)
        if not detections:
            return ActionProposal(
                action_type="noop",
                confidence=0.2,
                rationale="OCR ran successfully but found no readable text in the screenshot.",
                source="ocr",
            )

        scored: list[tuple[float, dict[str, Any]]] = []
        for detection in detections:
            score = self._score_detection(detection, task)
            if score > 0:
                scored.append((score, detection))

        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            best_score, best = scored[0]
            confidence = round(min(max(best_score, best["confidence"]), 0.99), 3)
            return ActionProposal(
                action_type="click",
                x=best["center_x"],
                y=best["center_y"],
                bbox=best["bbox"],
                confidence=confidence,
                matched_text=best["text"],
                rationale=(
                    "OCR matched visible UI text from the screenshot to the task. "
                    f"Matched '{best['text']}'."
                ),
                source="ocr",
            )

        preview = ", ".join(f"{item['text']}@{item['confidence']:.2f}" for item in detections[:8])
        return ActionProposal(
            action_type="noop",
            confidence=round(detections[0]["confidence"], 3),
            rationale=(
                "OCR is working, but none of the detected text regions matched the task closely enough. "
                f"Visible text preview: {preview}"
            ),
            source="ocr",
        )


class YoloVisionAdapter(VisionAdapter):
    """Best-effort local detector that only clicks on explicit label matches."""

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_model(model_path: str) -> Any:
        from ultralytics import YOLO  # type: ignore

        return YOLO(model_path)

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        model = self._load_model(str(self.model_path))
        results = model.predict(source=image_path, verbose=False, conf=0.25, max_det=10)
        if not results:
            return ActionProposal(
                action_type="noop",
                confidence=0.2,
                rationale="YOLO ran but returned no prediction results.",
            )

        result = results[0]
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        detections: list[dict[str, Any]] = []
        if boxes is not None:
            for box in boxes:
                cls_index = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
                label = str(names.get(cls_index, cls_index))
                detections.append(
                    {
                        "label": label,
                        "confidence": confidence,
                        "center_x": int((x1 + x2) / 2),
                        "center_y": int((y1 + y2) / 2),
                    }
                )

        if not detections:
            return ActionProposal(
                action_type="noop",
                confidence=0.2,
                rationale="YOLO ran successfully but found no objects in the screenshot.",
            )

        detections.sort(key=lambda item: item["confidence"], reverse=True)
        task_text = task.lower()
        for detection in detections:
            if detection["label"].lower() in task_text:
                return ActionProposal(
                    action_type="click",
                    x=detection["center_x"],
                    y=detection["center_y"],
                    matched_text=detection["label"],
                    confidence=round(detection["confidence"], 3),
                    rationale=(
                        "Local YOLO detector matched the requested label "
                        f"'{detection['label']}' in the screenshot."
                    ),
                    source="yolo",
                )

        top_detections = ", ".join(
            f"{item['label']}@{item['confidence']:.2f}" for item in detections[:5]
        )
        return ActionProposal(
            action_type="noop",
            confidence=round(detections[0]["confidence"], 3),
            rationale=(
                "Local YOLO detector is working, but no detected label matched the task text. "
                f"Top detections: {top_detections}"
            ),
            source="yolo",
        )


class BrowserHeuristicAdapter(VisionAdapter):
    """Small deterministic fallback for browser chrome regions."""

    def analyze_screenshot(self, image_path: str, task: str) -> ActionProposal:
        from PIL import Image

        width, height = Image.open(image_path).size
        task_text = _normalize_text(task)
        if any(phrase in task_text for phrase in ("address bar", "url bar", "search bar", "omnibox")):
            x = int(width * 0.33)
            y = max(90, int(height * 0.08))
            return ActionProposal(
                action_type="click",
                x=x,
                y=y,
                confidence=0.55,
                rationale="Used browser heuristic for the address/search bar region.",
                source="browser_heuristic",
            )
        return ActionProposal(
            action_type="noop",
            confidence=0.15,
            rationale="Browser heuristics found no safe deterministic match for the task.",
            source="browser_heuristic",
        )


def _default_model_path() -> Path:
    settings = get_settings()
    return settings.repo_root / "yolov8n.pt"


def _build_default_adapter() -> VisionAdapter:
    model_path = _default_model_path()
    if not model_path.exists():
        return StubVisionAdapter()

    try:
        return YoloVisionAdapter(model_path=model_path)
    except Exception:
        return StubVisionAdapter()


def analyze_screenshot(image_path: str, task: str) -> ActionProposal:
    """Analyze a screenshot with the best local adapter available."""
    adapters: list[VisionAdapter] = []
    try:
        adapters.append(RapidOcrAdapter())
    except Exception:
        pass
    adapters.append(_build_default_adapter())
    adapters.append(BrowserHeuristicAdapter())
    adapters.append(StubVisionAdapter())

    reasons: list[str] = []
    best_noop: ActionProposal | None = None
    for adapter in adapters:
        try:
            proposal = adapter.analyze_screenshot(image_path=image_path, task=task)
        except Exception as exc:
            reasons.append(f"{adapter.__class__.__name__} failed: {exc}")
            continue

        if proposal.action_type != "noop":
            if reasons:
                joined = " | ".join(reasons)
                proposal.rationale = f"{proposal.rationale} Fallback chain: {joined}"
            return proposal

        if best_noop is None or (proposal.confidence or 0.0) > (best_noop.confidence or 0.0):
            best_noop = proposal

    if best_noop is not None and reasons:
        best_noop.rationale = f"{best_noop.rationale} Fallback chain: {' | '.join(reasons)}"
        return best_noop
    return best_noop or StubVisionAdapter().analyze_screenshot(image_path=image_path, task=task)
