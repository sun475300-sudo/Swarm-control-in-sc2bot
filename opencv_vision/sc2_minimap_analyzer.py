# Phase 589: OpenCV
"""
sc2_minimap_analyzer.py — StarCraft II Minimap Analysis with OpenCV
Performs colour-based segmentation, contour detection, heatmap generation,
template matching, morphological cleanup, edge detection, histogram comparison,
drawing overlays, and a video-frame processing pipeline on SC2 minimap imagery.

Graceful fallback to a pure-NumPy stub when OpenCV is absent.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_minimap_analyzer")

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------
try:
    import cv2

    CV2_AVAILABLE = True
    log.info("OpenCV %s available.", cv2.__version__)
except ImportError:
    CV2_AVAILABLE = False
    log.warning("OpenCV not installed — using NumPy stub operations.")

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Colour range presets (HSV) for SC2 minimap regions
# ---------------------------------------------------------------------------
@dataclass
class ColourRange:
    """HSV lower / upper bounds for a minimap colour region."""

    name: str
    lower: np.ndarray
    upper: np.ndarray
    bgr_display: Tuple[int, int, int] = (255, 255, 255)


# Typical SC2 minimap colours (HSV).  Exact values depend on tileset.
COLOUR_PRESETS: Dict[str, ColourRange] = {
    "creep": ColourRange(
        name="creep",
        lower=np.array([120, 30, 40]),
        upper=np.array([160, 255, 200]),
        bgr_display=(180, 50, 180),  # purple
    ),
    "minerals": ColourRange(
        name="minerals",
        lower=np.array([90, 100, 100]),
        upper=np.array([130, 255, 255]),
        bgr_display=(255, 180, 0),  # blue
    ),
    "enemy": ColourRange(
        name="enemy",
        lower=np.array([0, 120, 120]),
        upper=np.array([10, 255, 255]),
        bgr_display=(0, 0, 255),  # red
    ),
    "friendly": ColourRange(
        name="friendly",
        lower=np.array([35, 80, 80]),
        upper=np.array([85, 255, 255]),
        bgr_display=(0, 255, 0),  # green
    ),
    "terrain": ColourRange(
        name="terrain",
        lower=np.array([15, 20, 30]),
        upper=np.array([35, 120, 140]),
        bgr_display=(80, 120, 80),  # brownish-green
    ),
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class DetectedRegion:
    """A contiguous region found on the minimap."""

    label: str
    contour: np.ndarray
    area: float
    centroid: Tuple[int, int]
    bounding_rect: Tuple[int, int, int, int]  # x, y, w, h


@dataclass
class BaseLocation:
    """A detected base location on the minimap."""

    position: Tuple[int, int]
    area: float
    is_main: bool = False
    is_natural: bool = False


@dataclass
class FrameAnalysis:
    """Full analysis result for a single minimap frame."""

    frame_index: int
    timestamp_s: float
    regions: Dict[str, List[DetectedRegion]]
    base_locations: List[BaseLocation]
    unit_positions: List[Tuple[int, int]]
    edges: Optional[np.ndarray] = None
    histogram: Optional[np.ndarray] = None


# ---------------------------------------------------------------------------
# MinimapAnalyzer
# ---------------------------------------------------------------------------
class MinimapAnalyzer:
    """OpenCV-based analyser for SC2 minimap frames.

    Parameters
    ----------
    minimap_size : tuple
        Expected (width, height) of minimap images.
    colour_presets : dict or None
        Override default HSV colour ranges.
    morph_kernel_size : int
        Kernel size for morphological noise removal.
    """

    def __init__(
        self,
        minimap_size: Tuple[int, int] = (256, 256),
        colour_presets: Optional[Dict[str, ColourRange]] = None,
        morph_kernel_size: int = 5,
    ) -> None:
        self.minimap_size = minimap_size
        self.colour_presets = colour_presets or dict(COLOUR_PRESETS)
        self.morph_kernel_size = morph_kernel_size

        # Accumulated heatmap (float32, same spatial dims as minimap).
        self.heatmap: np.ndarray = np.zeros(
            (minimap_size[1], minimap_size[0]), dtype=np.float32
        )
        self._frame_count: int = 0
        self._history: List[FrameAnalysis] = []

        # Template cache: name -> grey-scale template image
        self._templates: Dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Colour-based segmentation
    # ------------------------------------------------------------------
    def segment_by_colour(self, frame_bgr: np.ndarray) -> Dict[str, np.ndarray]:
        """Segment the minimap into binary masks for each colour preset.

        Returns dict mapping preset name -> binary mask (uint8, 0/255).
        """
        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        else:
            hsv = self._bgr_to_hsv_stub(frame_bgr)

        masks: Dict[str, np.ndarray] = {}
        for name, preset in self.colour_presets.items():
            if CV2_AVAILABLE:
                mask = cv2.inRange(hsv, preset.lower, preset.upper)
            else:
                mask = self._inrange_stub(hsv, preset.lower, preset.upper)
            mask = self._morphological_clean(mask)
            masks[name] = mask
        return masks

    # ------------------------------------------------------------------
    # Morphological operations (noise removal)
    # ------------------------------------------------------------------
    def _morphological_clean(self, mask: np.ndarray) -> np.ndarray:
        """Apply open-then-close to remove small noise."""
        if not CV2_AVAILABLE:
            return mask

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (self.morph_kernel_size, self.morph_kernel_size)
        )
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
        return cleaned

    # ------------------------------------------------------------------
    # Contour detection
    # ------------------------------------------------------------------
    def detect_contours(
        self, mask: np.ndarray, label: str, min_area: float = 30.0
    ) -> List[DetectedRegion]:
        """Find contours in a binary mask and return DetectedRegion list."""
        if not CV2_AVAILABLE:
            return self._detect_contours_stub(mask, label, min_area)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: List[DetectedRegion] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            x, y, w, h = cv2.boundingRect(cnt)
            regions.append(
                DetectedRegion(
                    label=label,
                    contour=cnt,
                    area=area,
                    centroid=(cx, cy),
                    bounding_rect=(x, y, w, h),
                )
            )
        return regions

    def _detect_contours_stub(
        self, mask: np.ndarray, label: str, min_area: float
    ) -> List[DetectedRegion]:
        """Very rough stub: find connected non-zero blobs via flood."""
        regions: List[DetectedRegion] = []
        binary = (mask > 127).astype(np.uint8)
        ys, xs = np.nonzero(binary)
        if len(xs) > 0:
            cx, cy = int(xs.mean()), int(ys.mean())
            area = float(len(xs))
            if area >= min_area:
                regions.append(
                    DetectedRegion(
                        label=label,
                        contour=np.array([[cx, cy]]),
                        area=area,
                        centroid=(cx, cy),
                        bounding_rect=(
                            int(xs.min()),
                            int(ys.min()),
                            int(xs.ptp()),
                            int(ys.ptp()),
                        ),
                    )
                )
        return regions

    # ------------------------------------------------------------------
    # Base location detection
    # ------------------------------------------------------------------
    def detect_base_locations(
        self,
        frame_bgr: np.ndarray,
        min_mineral_area: float = 80.0,
    ) -> List[BaseLocation]:
        """Identify base locations by finding mineral clusters."""
        masks = self.segment_by_colour(frame_bgr)
        mineral_mask = masks.get(
            "minerals", np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        )
        regions = self.detect_contours(
            mineral_mask, "minerals", min_area=min_mineral_area
        )

        # Sort by area descending — largest cluster is likely main base minerals.
        regions.sort(key=lambda r: r.area, reverse=True)
        bases: List[BaseLocation] = []
        for idx, region in enumerate(regions):
            bases.append(
                BaseLocation(
                    position=region.centroid,
                    area=region.area,
                    is_main=(idx == 0),
                    is_natural=(idx == 1),
                )
            )
        return bases

    # ------------------------------------------------------------------
    # Unit position heatmap
    # ------------------------------------------------------------------
    def update_heatmap(
        self, unit_positions: List[Tuple[int, int]], decay: float = 0.98
    ) -> np.ndarray:
        """Accumulate unit positions into a temporal heatmap.

        Parameters
        ----------
        unit_positions : list of (x, y)
        decay : float
            Multiplicative decay applied to existing heatmap each frame.
        """
        self.heatmap *= decay
        for x, y in unit_positions:
            if 0 <= x < self.minimap_size[0] and 0 <= y < self.minimap_size[1]:
                # Gaussian-ish splat (3x3)
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if (
                            0 <= nx < self.minimap_size[0]
                            and 0 <= ny < self.minimap_size[1]
                        ):
                            weight = 1.0 if (dx == 0 and dy == 0) else 0.5
                            self.heatmap[ny, nx] += weight
        return self.heatmap

    def render_heatmap(self, save_path: Optional[str] = None) -> np.ndarray:
        """Normalise heatmap to 0-255 and apply a colour map."""
        norm = self.heatmap.copy()
        max_val = norm.max()
        if max_val > 0:
            norm = (norm / max_val * 255).astype(np.uint8)
        else:
            norm = norm.astype(np.uint8)

        if CV2_AVAILABLE:
            coloured = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        else:
            # Simple fallback: greyscale -> pseudo-colour via stacking
            coloured = np.stack([norm, norm // 2, 255 - norm], axis=-1)

        if save_path:
            if CV2_AVAILABLE:
                cv2.imwrite(save_path, coloured)
            log.info("Heatmap saved to %s", save_path)
        return coloured

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------
    def register_template(self, name: str, template_bgr: np.ndarray) -> None:
        """Register a building template image (BGR) for later matching."""
        if CV2_AVAILABLE:
            grey = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
        else:
            grey = np.mean(template_bgr, axis=2).astype(np.uint8)
        self._templates[name] = grey

    def match_templates(
        self,
        frame_bgr: np.ndarray,
        threshold: float = 0.75,
    ) -> List[Tuple[str, Tuple[int, int], float]]:
        """Run template matching for all registered templates.

        Returns list of (template_name, (x, y), confidence).
        """
        if not CV2_AVAILABLE:
            log.warning("OpenCV not available — skipping template matching.")
            return []

        grey_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        matches: List[Tuple[str, Tuple[int, int], float]] = []

        for name, tmpl in self._templates.items():
            th, tw = tmpl.shape[:2]
            if th > grey_frame.shape[0] or tw > grey_frame.shape[1]:
                continue
            result = cv2.matchTemplate(grey_frame, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            for pt in zip(*locations[::-1]):  # (x, y)
                score = float(result[pt[1], pt[0]])
                matches.append((name, (int(pt[0]), int(pt[1])), score))

        # Non-maximum suppression: keep best per 20-px neighbourhood
        if matches:
            matches.sort(key=lambda m: m[2], reverse=True)
            kept: List[Tuple[str, Tuple[int, int], float]] = []
            for m in matches:
                too_close = False
                for k in kept:
                    if abs(m[1][0] - k[1][0]) < 20 and abs(m[1][1] - k[1][1]) < 20:
                        too_close = True
                        break
                if not too_close:
                    kept.append(m)
            matches = kept

        return matches

    # ------------------------------------------------------------------
    # Edge detection (Canny) for terrain analysis
    # ------------------------------------------------------------------
    def detect_edges(
        self,
        frame_bgr: np.ndarray,
        low_threshold: int = 50,
        high_threshold: int = 150,
    ) -> np.ndarray:
        """Apply Canny edge detection for terrain boundary analysis."""
        if CV2_AVAILABLE:
            grey = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(grey, (5, 5), 1.4)
            edges = cv2.Canny(blurred, low_threshold, high_threshold)
        else:
            # Stub: simple gradient magnitude
            grey = np.mean(frame_bgr, axis=2).astype(np.float32)
            gx = np.diff(grey, axis=1, prepend=0)
            gy = np.diff(grey, axis=0, prepend=0)
            mag = np.sqrt(gx**2 + gy**2)
            edges = ((mag > low_threshold) * 255).astype(np.uint8)
        return edges

    # ------------------------------------------------------------------
    # Image histogram comparison
    # ------------------------------------------------------------------
    def compute_histogram(self, frame_bgr: np.ndarray, bins: int = 64) -> np.ndarray:
        """Compute a normalised HSV histogram for the frame."""
        if CV2_AVAILABLE:
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [bins, bins], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        else:
            # Stub: flatten and bin
            flat = frame_bgr.ravel().astype(np.float32)
            hist, _ = np.histogram(flat, bins=bins, range=(0, 256))
            hist = hist.astype(np.float32)
            s = hist.sum()
            if s > 0:
                hist /= s
        return hist

    def compare_histograms(
        self,
        hist_a: np.ndarray,
        hist_b: np.ndarray,
    ) -> Dict[str, float]:
        """Compare two histograms using multiple metrics.

        Returns dict with correlation, chi-square, intersection, and
        Bhattacharyya distance.
        """
        if CV2_AVAILABLE:
            methods = {
                "correlation": cv2.HISTCMP_CORREL,
                "chi_square": cv2.HISTCMP_CHISQR,
                "intersection": cv2.HISTCMP_INTERSECT,
                "bhattacharyya": cv2.HISTCMP_BHATTACHARYYA,
            }
            return {
                name: float(cv2.compareHist(hist_a, hist_b, method))
                for name, method in methods.items()
            }

        # Stub: correlation only
        a = hist_a.ravel().astype(np.float64)
        b = hist_b.ravel().astype(np.float64)
        a -= a.mean()
        b -= b.mean()
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        corr = float(np.dot(a, b) / denom) if denom > 0 else 0.0
        return {"correlation": corr}

    # ------------------------------------------------------------------
    # Drawing overlay functions
    # ------------------------------------------------------------------
    def draw_regions(
        self,
        frame_bgr: np.ndarray,
        regions: List[DetectedRegion],
        thickness: int = 2,
    ) -> np.ndarray:
        """Draw contours and labels for detected regions."""
        canvas = frame_bgr.copy()
        if not CV2_AVAILABLE:
            return canvas

        for region in regions:
            preset = self.colour_presets.get(region.label)
            colour = preset.bgr_display if preset else (255, 255, 255)
            cv2.drawContours(canvas, [region.contour], -1, colour, thickness)
            cx, cy = region.centroid
            cv2.circle(canvas, (cx, cy), 3, colour, -1)
            cv2.putText(
                canvas,
                f"{region.label} ({region.area:.0f})",
                (cx + 5, cy - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                colour,
                1,
                cv2.LINE_AA,
            )
        return canvas

    def draw_base_locations(
        self,
        frame_bgr: np.ndarray,
        bases: List[BaseLocation],
    ) -> np.ndarray:
        """Draw circles and labels for base locations."""
        canvas = frame_bgr.copy()
        if not CV2_AVAILABLE:
            return canvas

        for base in bases:
            colour = (0, 255, 255) if base.is_main else (0, 200, 200)
            radius = max(int(math.sqrt(base.area / math.pi)), 5)
            cv2.circle(canvas, base.position, radius, colour, 2)
            label = "MAIN" if base.is_main else ("NAT" if base.is_natural else "EXP")
            cv2.putText(
                canvas,
                label,
                (base.position[0] + radius + 2, base.position[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                colour,
                1,
                cv2.LINE_AA,
            )
        return canvas

    def draw_heatmap_overlay(
        self,
        frame_bgr: np.ndarray,
        alpha: float = 0.5,
    ) -> np.ndarray:
        """Blend the accumulated heatmap onto the minimap frame."""
        heatmap_colour = self.render_heatmap()
        # Resize heatmap if needed
        h, w = frame_bgr.shape[:2]
        if CV2_AVAILABLE and (
            heatmap_colour.shape[0] != h or heatmap_colour.shape[1] != w
        ):
            heatmap_colour = cv2.resize(heatmap_colour, (w, h))

        if CV2_AVAILABLE:
            blended = cv2.addWeighted(frame_bgr, 1.0 - alpha, heatmap_colour, alpha, 0)
        else:
            blended = (
                frame_bgr.astype(np.float32) * (1.0 - alpha)
                + heatmap_colour.astype(np.float32) * alpha
            ).astype(np.uint8)
        return blended

    def draw_rectangles(
        self,
        frame_bgr: np.ndarray,
        rects: List[Tuple[int, int, int, int]],
        colour: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 1,
    ) -> np.ndarray:
        """Draw rectangles (x, y, w, h) on the frame."""
        canvas = frame_bgr.copy()
        if not CV2_AVAILABLE:
            return canvas
        for x, y, w, h in rects:
            cv2.rectangle(canvas, (x, y), (x + w, y + h), colour, thickness)
        return canvas

    def draw_text(
        self,
        frame_bgr: np.ndarray,
        text: str,
        position: Tuple[int, int] = (10, 20),
        colour: Tuple[int, int, int] = (255, 255, 255),
        scale: float = 0.5,
    ) -> np.ndarray:
        """Put text on the frame."""
        canvas = frame_bgr.copy()
        if not CV2_AVAILABLE:
            return canvas
        cv2.putText(
            canvas,
            text,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            colour,
            1,
            cv2.LINE_AA,
        )
        return canvas

    # ------------------------------------------------------------------
    # Full frame analysis
    # ------------------------------------------------------------------
    def analyse_frame(
        self,
        frame_bgr: np.ndarray,
        frame_index: int = 0,
        timestamp_s: float = 0.0,
    ) -> FrameAnalysis:
        """Run the complete analysis pipeline on a single minimap frame."""

        # 1. Colour segmentation + contour detection
        masks = self.segment_by_colour(frame_bgr)
        all_regions: Dict[str, List[DetectedRegion]] = {}
        for name, mask in masks.items():
            regions = self.detect_contours(mask, name)
            if regions:
                all_regions[name] = regions

        # 2. Base locations
        bases = self.detect_base_locations(frame_bgr)

        # 3. Unit positions (from friendly + enemy masks)
        unit_positions: List[Tuple[int, int]] = []
        for key in ("friendly", "enemy"):
            for region in all_regions.get(key, []):
                unit_positions.append(region.centroid)

        # 4. Update heatmap
        self.update_heatmap(unit_positions)

        # 5. Edge detection
        edges = self.detect_edges(frame_bgr)

        # 6. Histogram
        hist = self.compute_histogram(frame_bgr)

        analysis = FrameAnalysis(
            frame_index=frame_index,
            timestamp_s=timestamp_s,
            regions=all_regions,
            base_locations=bases,
            unit_positions=unit_positions,
            edges=edges,
            histogram=hist,
        )
        self._history.append(analysis)
        self._frame_count += 1
        return analysis

    # ------------------------------------------------------------------
    # Video frame processing pipeline (simulated)
    # ------------------------------------------------------------------
    def process_video(
        self,
        frames: List[np.ndarray],
        fps: float = 10.0,
        save_annotated: bool = False,
        output_dir: str = "minimap_output",
    ) -> List[FrameAnalysis]:
        """Process a sequence of minimap frames (simulated video).

        Parameters
        ----------
        frames : list of BGR ndarray
        fps : float
        save_annotated : bool
            If True, save annotated frames to *output_dir*.
        """
        results: List[FrameAnalysis] = []

        if save_annotated:
            os.makedirs(output_dir, exist_ok=True)

        prev_hist: Optional[np.ndarray] = None

        for idx, frame in enumerate(frames):
            ts = idx / fps
            analysis = self.analyse_frame(frame, frame_index=idx, timestamp_s=ts)
            results.append(analysis)

            # Histogram-based game state change detection
            if prev_hist is not None and analysis.histogram is not None:
                cmp = self.compare_histograms(prev_hist, analysis.histogram)
                corr = cmp.get("correlation", 1.0)
                if corr < 0.85:
                    log.info(
                        "Frame %d (%.1fs): significant minimap change detected (corr=%.3f)",
                        idx,
                        ts,
                        corr,
                    )
            prev_hist = analysis.histogram

            # Save annotated frame
            if save_annotated and CV2_AVAILABLE:
                canvas = frame.copy()
                for region_list in analysis.regions.values():
                    canvas = self.draw_regions(canvas, region_list)
                canvas = self.draw_base_locations(canvas, analysis.base_locations)
                canvas = self.draw_text(canvas, f"F{idx} t={ts:.1f}s", (5, 15))
                path = os.path.join(output_dir, f"frame_{idx:05d}.png")
                cv2.imwrite(path, canvas)

            if (idx + 1) % 50 == 0:
                log.info("Processed %d / %d frames.", idx + 1, len(frames))

        log.info(
            "Video pipeline complete — %d frames, %d base locations in last frame.",
            len(frames),
            len(results[-1].base_locations) if results else 0,
        )
        return results

    # ------------------------------------------------------------------
    # Simulated minimap frame generator (for testing)
    # ------------------------------------------------------------------
    @staticmethod
    def generate_simulated_frames(
        n_frames: int = 100,
        size: Tuple[int, int] = (256, 256),
        seed: int = 42,
    ) -> List[np.ndarray]:
        """Generate synthetic minimap frames for pipeline testing.

        Produces BGR images with random coloured blobs simulating creep
        spread, mineral patches, and moving units.
        """
        rng = np.random.RandomState(seed)
        frames: List[np.ndarray] = []
        w, h = size

        # Static elements: terrain background, mineral patches
        base_terrain = np.full(
            (h, w, 3), (60, 90, 50), dtype=np.uint8
        )  # brownish green

        # Mineral patch positions (fixed)
        mineral_positions = [(50, 50), (200, 50), (50, 200), (200, 200), (128, 128)]

        for f_idx in range(n_frames):
            frame = base_terrain.copy()

            # Draw mineral patches (blue-ish blobs)
            for mx, my in mineral_positions:
                jx = mx + rng.randint(-2, 3)
                jy = my + rng.randint(-2, 3)
                if CV2_AVAILABLE:
                    cv2.circle(frame, (jx, jy), 12, (255, 180, 0), -1)
                else:
                    yy, xx = np.ogrid[-12:13, -12:13]
                    mask = xx**2 + yy**2 <= 144
                    for dy in range(-12, 13):
                        for dx in range(-12, 13):
                            py, px = jy + dy, jx + dx
                            if 0 <= py < h and 0 <= px < w and mask[dy + 12, dx + 12]:
                                frame[py, px] = [255, 180, 0]

            # Creep spread (purple, grows over time)
            creep_radius = min(15 + f_idx // 3, 80)
            creep_cx, creep_cy = 180, 180
            if CV2_AVAILABLE:
                cv2.circle(
                    frame, (creep_cx, creep_cy), creep_radius, (180, 50, 180), -1
                )
            else:
                for dy in range(-creep_radius, creep_radius + 1):
                    for dx in range(-creep_radius, creep_radius + 1):
                        if dx * dx + dy * dy <= creep_radius * creep_radius:
                            py, px = creep_cy + dy, creep_cx + dx
                            if 0 <= py < h and 0 <= px < w:
                                frame[py, px] = [180, 50, 180]

            # Friendly units (green dots, moving)
            n_friendly = 3 + f_idx // 20
            for _ in range(n_friendly):
                ux = int(np.clip(128 + rng.randn() * 30 + f_idx * 0.2, 0, w - 1))
                uy = int(np.clip(128 + rng.randn() * 30, 0, h - 1))
                if CV2_AVAILABLE:
                    cv2.circle(frame, (ux, uy), 3, (0, 255, 0), -1)
                else:
                    for ddy in range(-3, 4):
                        for ddx in range(-3, 4):
                            py, px = uy + ddy, ux + ddx
                            if (
                                0 <= py < h
                                and 0 <= px < w
                                and ddx * ddx + ddy * ddy <= 9
                            ):
                                frame[py, px] = [0, 255, 0]

            # Enemy units (red dots)
            n_enemy = rng.randint(0, 4)
            for _ in range(n_enemy):
                ex = rng.randint(10, w - 10)
                ey = rng.randint(10, h - 10)
                if CV2_AVAILABLE:
                    cv2.circle(frame, (ex, ey), 3, (0, 0, 255), -1)
                else:
                    for ddy in range(-3, 4):
                        for ddx in range(-3, 4):
                            py, px = ey + ddy, ex + ddx
                            if (
                                0 <= py < h
                                and 0 <= px < w
                                and ddx * ddx + ddy * ddy <= 9
                            ):
                                frame[py, px] = [0, 0, 255]

            # Add slight noise
            noise = rng.randint(-5, 6, size=frame.shape, dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            frames.append(frame)

        return frames

    # ------------------------------------------------------------------
    # Stub helpers (when OpenCV is absent)
    # ------------------------------------------------------------------
    @staticmethod
    def _bgr_to_hsv_stub(bgr: np.ndarray) -> np.ndarray:
        """Minimal BGR -> HSV conversion (NumPy only)."""
        img = bgr.astype(np.float32) / 255.0
        b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        v = np.max(img, axis=2)
        diff = v - np.min(img, axis=2)
        s = np.where(v == 0, 0, diff / v)

        h = np.zeros_like(v)
        mask_r = (v == r) & (diff > 0)
        mask_g = (v == g) & (diff > 0)
        mask_b = (v == b) & (diff > 0)
        h[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / diff[mask_r]) % 6)
        h[mask_g] = 60 * (((b[mask_g] - r[mask_g]) / diff[mask_g]) + 2)
        h[mask_b] = 60 * (((r[mask_b] - g[mask_b]) / diff[mask_b]) + 4)

        hsv = np.stack([h / 2, s * 255, v * 255], axis=-1).astype(np.uint8)
        return hsv

    @staticmethod
    def _inrange_stub(
        hsv: np.ndarray, lower: np.ndarray, upper: np.ndarray
    ) -> np.ndarray:
        """Stub for cv2.inRange using NumPy."""
        mask = np.ones(hsv.shape[:2], dtype=np.uint8) * 255
        for c in range(3):
            mask[(hsv[:, :, c] < lower[c]) | (hsv[:, :, c] > upper[c])] = 0
        return mask

    # ------------------------------------------------------------------
    # Summary / stats
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Return a summary of all processed frames."""
        if not self._history:
            return {"frames_processed": 0}

        all_bases = [len(a.base_locations) for a in self._history]
        all_units = [len(a.unit_positions) for a in self._history]

        return {
            "frames_processed": self._frame_count,
            "avg_bases_detected": float(np.mean(all_bases)),
            "max_bases_detected": int(np.max(all_bases)),
            "avg_unit_blobs": float(np.mean(all_units)),
            "heatmap_max_intensity": float(self.heatmap.max()),
            "total_regions_detected": sum(
                sum(len(rl) for rl in a.regions.values()) for a in self._history
            ),
        }


# ---------------------------------------------------------------------------
# Main — demonstrate full pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=== SC2 Minimap Analyzer (OpenCV) ===")

    analyzer = MinimapAnalyzer(minimap_size=(256, 256))

    # 1. Generate simulated frames
    frames = MinimapAnalyzer.generate_simulated_frames(n_frames=60, size=(256, 256))
    log.info("Generated %d simulated minimap frames.", len(frames))

    # 2. Register a dummy building template (16x16 block)
    template = np.full((16, 16, 3), (180, 50, 180), dtype=np.uint8)
    analyzer.register_template("hatchery", template)

    # 3. Single-frame analysis demo
    single = analyzer.analyse_frame(frames[30], frame_index=30, timestamp_s=3.0)
    log.info(
        "Frame 30: %d region types, %d bases, %d unit blobs",
        len(single.regions),
        len(single.base_locations),
        len(single.unit_positions),
    )

    # 4. Edge detection demo
    edges = analyzer.detect_edges(frames[30])
    edge_pixels = int(np.count_nonzero(edges))
    log.info(
        "Edge pixels in frame 30: %d (%.1f%%)",
        edge_pixels,
        edge_pixels / edges.size * 100,
    )

    # 5. Histogram comparison (frame 0 vs frame 50)
    hist_a = analyzer.compute_histogram(frames[0])
    hist_b = analyzer.compute_histogram(frames[50])
    cmp = analyzer.compare_histograms(hist_a, hist_b)
    log.info("Histogram comparison (frame 0 vs 50): %s", cmp)

    # 6. Template matching
    matches = analyzer.match_templates(frames[30], threshold=0.6)
    log.info("Template matches in frame 30: %d", len(matches))

    # 7. Process full video sequence
    # Reset analyser to get clean heatmap
    analyzer_fresh = MinimapAnalyzer(minimap_size=(256, 256))
    results = analyzer_fresh.process_video(frames, fps=10.0, save_annotated=False)
    log.info("Pipeline returned %d frame analyses.", len(results))

    # 8. Render final heatmap
    analyzer_fresh.render_heatmap(save_path="sc2_minimap_heatmap.png")

    # 9. Drawing overlay demo
    canvas = frames[30].copy()
    for region_list in single.regions.values():
        canvas = analyzer.draw_regions(canvas, region_list)
    canvas = analyzer.draw_base_locations(canvas, single.base_locations)
    canvas = analyzer.draw_text(canvas, "SC2 Minimap Analysis", (10, 15))
    canvas = analyzer.draw_rectangles(
        canvas, [(100, 100, 50, 50)], colour=(0, 255, 255)
    )
    canvas = analyzer.draw_heatmap_overlay(canvas, alpha=0.3)
    if CV2_AVAILABLE:
        cv2.imwrite("sc2_minimap_annotated.png", canvas)
        log.info("Annotated frame saved.")

    # 10. Summary
    stats = analyzer_fresh.summary()
    for k, v in stats.items():
        log.info("  %-30s %s", k, v)

    log.info("=== Phase 589 complete ===")


if __name__ == "__main__":
    main()
