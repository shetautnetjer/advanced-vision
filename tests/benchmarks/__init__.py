"""Eagle2-2B Classification Benchmark Tests.

This module contains comprehensive benchmarks for Eagle2-2B vision model
testing classification capabilities across UI elements, screen changes,
and trading chart elements.
"""

from .test_eagle2_classification import (
    Eagle2Classifier,
    SyntheticImageGenerator,
    BenchmarkResults,
    ClassificationResult,
    PerformanceMetrics,
    ThresholdMetrics,
)

__all__ = [
    "Eagle2Classifier",
    "SyntheticImageGenerator", 
    "BenchmarkResults",
    "ClassificationResult",
    "PerformanceMetrics",
    "ThresholdMetrics",
]
