import io
import math
import os
import uuid
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance

from backend.app.config import settings
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


class ImageTamperDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "ImageTamperDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document

        rendered_pages = context.get_rendered_pages(max_pages=2)
        if not rendered_pages:
            return flags

        all_regions: List[Dict[str, Any]] = []
        target_page_no = 1
        target_img: Image.Image = rendered_pages[0][1]

        for page_no, pil_img in rendered_pages:
            page_regions = self._analyze_page(pil_img, page_no, context)
            if page_regions:
                all_regions.extend(page_regions)
                if page_no == 1 or not target_img:
                    target_page_no = page_no
                    target_img = pil_img

        if not all_regions:
            return flags

        # Generate Heatmap / Bounding-box Overlay PNG
        overlay_path = self._create_overlay(target_img, target_page_no, all_regions, doc.id)

        # Build structured evidence list
        evidence_list = []
        for r in all_regions[:15]:
            evidence_list.append({
                "document_id": doc.id,
                "page": r.get("page", 1),
                "type": r.get("type", "tamper_region"),
                "bbox": r.get("bbox", [0, 0, 0, 0]),
                "score": round(float(r.get("score", 0.0)), 2),
            })

        flags.append(
            AnomalyFlagDTO(
                detector=self.name,
                code="IMAGE_TAMPER_SUSPECTED",
                severity="HIGH",
                reason="Visual compression, repetition, or baseline irregularities detected in document layout; preliminary indicator requiring human verification.",
                evidence=evidence_list,
                confidence=0.88,
                recommended_action="Perform visual verification of highlighted regions against authorized primary copy.",
                overlay_image_path=overlay_path,
            )
        )

        return flags

    def _analyze_page(
        self, img: Image.Image, page_no: int, context: DetectionContext
    ) -> List[Dict[str, Any]]:
        """
        Runs ELA, copy-move detection, and baseline regularity check on a single page.
        """
        regions: List[Dict[str, Any]] = []

        # 1. Error Level Analysis (ELA)
        ela_regions = self._run_ela(img, page_no)
        regions.extend(ela_regions)

        # 2. Copy-Move Detection (OpenCV ORB features)
        copy_move_regions = self._run_copy_move(img, page_no)
        regions.extend(copy_move_regions)

        # 3. Text Baseline Regularity Check
        baseline_regions = self._run_baseline_check(context, page_no, img.size)
        regions.extend(baseline_regions)

        return regions

    def _run_ela(self, img: Image.Image, page_no: int) -> List[Dict[str, Any]]:
        """
        Calculates localized compression differences via Error Level Analysis (ELA).
        """
        regions: List[Dict[str, Any]] = []
        try:
            # Resave to JPEG buffer at target quality
            buf = io.BytesIO()
            img_rgb = img.convert("RGB")
            img_rgb.save(buf, format="JPEG", quality=settings.ANOMALY_ELA_QUALITY)
            buf.seek(0)
            resaved = Image.open(buf)

            # Compute difference and scale
            diff = ImageChops.difference(img_rgb, resaved)
            diff_np = np.array(diff.convert("L"), dtype=np.float32) * (settings.ANOMALY_ELA_SCALE / 10.0)

            # Analyze 32x32 blocks
            h, w = diff_np.shape
            block_size = 32
            mean_overall = np.mean(diff_np)
            std_overall = np.std(diff_np)

            # Only flag localized blocks if they significantly exceed global mean + 3*std
            threshold = max(settings.ANOMALY_ELA_DIFF_THRESHOLD, mean_overall + 3.0 * std_overall)

            high_blocks = []
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = diff_np[y : y + block_size, x : x + block_size]
                    b_mean = np.mean(block)
                    if b_mean > threshold:
                        high_blocks.append((x, y, block_size, block_size, b_mean))

            # If an isolated cluster of blocks shows high compression disparity (not whole noisy page)
            if 1 <= len(high_blocks) <= 25:
                for bx, by, bw, bh, bscore in high_blocks[:5]:
                    regions.append({
                        "page": page_no,
                        "type": "ela_inconsistency",
                        "bbox": [bx, by, bw, bh],
                        "score": float(bscore),
                    })
        except Exception:
            pass
        return regions

    def _run_copy_move(self, img: Image.Image, page_no: int) -> List[Dict[str, Any]]:
        """
        Detects copy-move tampering using OpenCV ORB feature descriptor matching
        and 2D shift-vector spatial clustering.
        """
        regions: List[Dict[str, Any]] = []
        try:
            from collections import defaultdict
            gray = np.array(img.convert("L"))
            orb = cv2.ORB_create(nfeatures=1500)
            kp, des = orb.detectAndCompute(gray, None)

            if des is None or len(kp) < 30:
                return regions

            # Self-matching with k=3 (0=self, 1=closest other, 2=second closest)
            bf = cv2.BFMatcher(cv2.NORM_HAMMING)
            matches = bf.knnMatch(des, des, k=3)

            clusters = defaultdict(list)
            bin_size = 25

            for match in matches:
                if len(match) >= 3:
                    m, n = match[1], match[2]
                    if m.distance < 0.78 * n.distance:
                        pt1 = kp[m.queryIdx].pt
                        pt2 = kp[m.trainIdx].pt
                        dx = int(round((pt2[0] - pt1[0]) / bin_size))
                        dy = int(round((pt2[1] - pt1[1]) / bin_size))
                        dist = math.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1])
                        # Filter out identical text line repetition (dy == 0) and small displacements
                        if dist >= settings.ANOMALY_COPY_MOVE_MIN_DISTANCE and abs(dy) >= 2:
                            clusters[(dx, dy)].append((pt1, pt2))

            for (dx, dy), pairs in clusters.items():
                if len(pairs) >= settings.ANOMALY_COPY_MOVE_MIN_MATCHES:
                    pts1 = [p[0] for p in pairs]
                    pts2 = [p[1] for p in pairs]
                    x_min = min(min(p[0] for p in pts1), min(p[0] for p in pts2))
                    y_min = min(min(p[1] for p in pts1), min(p[1] for p in pts2))
                    x_max = max(max(p[0] for p in pts1), max(p[0] for p in pts2))
                    y_max = max(max(p[1] for p in pts1), max(p[1] for p in pts2))

                    regions.append({
                        "page": page_no,
                        "type": "copy_move_cluster",
                        "bbox": [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)],
                        "score": float(len(pairs)),
                    })
                    break
        except Exception:
            pass
        return regions

    def _run_baseline_check(
        self, context: DetectionContext, page_no: int, img_size: Tuple[int, int]
    ) -> List[Dict[str, Any]]:
        """
        Checks OCR word boxes for irregular baseline alignment.
        """
        regions: List[Dict[str, Any]] = []
        try:
            doc = context.document
            target_page = None
            for p in doc.pages:
                if p.page_no == page_no:
                    target_page = p
                    break

            if not target_page or not target_page.words_json:
                return regions

            words = target_page.words_json
            if len(words) < 10:
                return regions

            # Group words by similar y0 baseline (within 6px)
            lines: Dict[int, List[Dict[str, Any]]] = {}
            for w in words:
                bbox = w.get("bbox", [0, 0, 0, 0])
                if len(bbox) == 4:
                    y_center = int(bbox[1] // 10) * 10
                    lines.setdefault(y_center, []).append(w)

            for y_line, line_words in lines.items():
                if len(line_words) >= 4:
                    baselines = [w["bbox"][3] for w in line_words if len(w.get("bbox", [])) == 4]
                    if len(baselines) >= 4:
                        var = np.var(baselines)
                        if var > settings.ANOMALY_TEXT_BASELINE_VAR_THRESHOLD:
                            x0 = min(w["bbox"][0] for w in line_words)
                            y0 = min(w["bbox"][1] for w in line_words)
                            x1 = max(w["bbox"][2] for w in line_words)
                            y1 = max(w["bbox"][3] for w in line_words)
                            regions.append({
                                "page": page_no,
                                "type": "baseline_irregularity",
                                "bbox": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                                "score": float(var),
                            })
                            break
        except Exception:
            pass
        return regions

    def _create_overlay(
        self,
        base_img: Image.Image,
        page_no: int,
        regions: List[Dict[str, Any]],
        doc_id: int,
    ) -> str:
        """
        Generates and saves a translucent bounding-box overlay PNG.
        """
        os.makedirs(settings.ANOMALY_STORAGE_DIR, exist_ok=True)
        filename = f"overlay_doc_{doc_id}_p{page_no}_{uuid.uuid4().hex[:8]}.png"
        out_path = os.path.join(settings.ANOMALY_STORAGE_DIR, filename)

        # Create overlay layer
        overlay = base_img.convert("RGBA")
        draw_layer = Image.new("RGBA", overlay.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(draw_layer)

        for r in regions:
            bbox = r.get("bbox", [0, 0, 50, 50])
            x, y, w, h = bbox[0], bbox[1], max(bbox[2], 20), max(bbox[3], 20)
            # Red-orange highlight box with alpha fill
            draw.rectangle(
                [x, y, x + w, y + h],
                fill=(239, 68, 68, 50),
                outline=(239, 68, 68, 220),
                width=3,
            )

        composite = Image.alpha_composite(overlay, draw_layer)
        composite.save(out_path, format="PNG")
        return out_path
