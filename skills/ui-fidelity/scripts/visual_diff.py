#!/usr/bin/env python3
"""
visual_diff.py — CV 对齐后做分区 diff，供 ui-fidelity 闭环的「视觉保真线」调用。

定位：这是**量化预筛**，不是语义裁判。
  - 它先用 ORB 特征把「实现截图」对齐到「设计参考图」的坐标系，消除 1-2px 平移/亚像素
    错位造成的 pixel-diff 假阳性（裸 pixelmatch 的主要噪声来源）。
  - 再分区找出真正不同的块，输出每块的 bbox + 面积占比 + 平均色差，写成 JSON + 标注 PNG。
  - 它**只回答「哪里不同、多大、偏色还是结构」**；差异属于 content/style/layout/size 哪一类
    这种**语义判断交给 ui-fidelity-reviewer（VLM 子代理）**——研究证实纯像素相似 ≠ 还原正确，
    语义分类得靠 VLM。本脚本给 reviewer 喂「该看哪几个坐标」，二者配合而非替代。

用法:
  python3 visual_diff.py --design 设计参考.png --impl dev-browser截图.png --out outdir/ \\
      [--threshold 40] [--min-area-ratio 0.0002]

  --threshold       灰度差阈值(0-255)，超过才算「这个像素变了」，默认 40
  --min-area-ratio  差异块面积下限(占整图比例)，滤掉零碎噪点，默认 0.0002

输出 outdir/:
  diff.json            结构化差异（aligned / diff_ratio / regions[bbox,area,mean_delta,hint]）
  diff_annotated.png   设计图上用红框标出每个差异块（人/agent 直接看坐标）
  diff_heatmap.png     差异热力图

依赖（一次性本地装，与项目 python-docx 同列）:
  pip install opencv-python numpy

退出码: 0=完成(无论是否有差异)  2=依赖缺失  3=入参/读图错误
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    sys.stderr.write(
        "[visual_diff] 缺依赖。请先：pip install opencv-python numpy\n"
    )
    sys.exit(2)


def load_gray_bgr(path: str):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        sys.stderr.write(f"[visual_diff] 读不到图（路径或格式不对）：{path}\n")
        sys.exit(3)
    return img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def align_impl_to_design(design_bgr, impl_bgr, design_gray, impl_gray):
    """把 impl 对齐到 design 坐标系。返回 (warped_impl_bgr, method, inliers)。

    优先 ORB+单应矩阵(RANSAC)；特征不足时退化为「等比缩放到 design 尺寸」。
    """
    dh, dw = design_gray.shape[:2]
    orb = cv2.ORB_create(nfeatures=3000)
    k1, d1 = orb.detectAndCompute(impl_gray, None)
    k2, d2 = orb.detectAndCompute(design_gray, None)

    if d1 is not None and d2 is not None and len(k1) >= 12 and len(k2) >= 12:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        raw = matcher.knnMatch(d1, d2, k=2)
        good = [m for m, n in (p for p in raw if len(p) == 2) if m.distance < 0.75 * n.distance]
        if len(good) >= 12:
            src = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
            if H is not None:
                inliers = int(mask.sum()) if mask is not None else 0
                if inliers >= 10:
                    warped = cv2.warpPerspective(impl_bgr, H, (dw, dh))
                    return warped, "ORB+homography", inliers

    # 退化：等比缩放（仅当两图基本同构、只是分辨率不同时可用）
    resized = cv2.resize(impl_bgr, (dw, dh), interpolation=cv2.INTER_AREA)
    return resized, "resize-fallback", 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True, help="设计参考 PNG（基准坐标系）")
    ap.add_argument("--impl", required=True, help="dev-browser 实现截图 PNG")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--threshold", type=int, default=40)
    ap.add_argument("--min-area-ratio", type=float, default=0.0002)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    design_bgr, design_gray = load_gray_bgr(args.design)
    impl_bgr, impl_gray = load_gray_bgr(args.impl)

    warped_bgr, method, inliers = align_impl_to_design(
        design_bgr, impl_bgr, design_gray, impl_gray
    )
    warped_gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    dh, dw = design_gray.shape[:2]
    # warp 引入的黑边会被误判为差异 → 用 mask 排除 impl 实际未覆盖的区域
    valid = (warped_gray > 0).astype(np.uint8)

    delta = cv2.absdiff(design_gray, warped_gray)
    _, mask = cv2.threshold(delta, args.threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.bitwise_and(mask, mask, mask=valid)
    # 形态学闭运算把零碎差异连成块
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    total_px = dw * dh
    diff_px = int((mask > 0).sum())
    diff_ratio = diff_px / total_px if total_px else 0.0

    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = max(16, int(args.min_area_ratio * total_px))
    annotated = design_bgr.copy()
    regions = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        roi_design = design_bgr[y : y + h, x : x + w].astype(np.int16)
        roi_impl = warped_bgr[y : y + h, x : x + w].astype(np.int16)
        mean_delta = float(np.abs(roi_design - roi_impl).mean())
        # 粗启发：宽高比极端/面积大 → 偏「布局/结构」；小而色差大 → 偏「样式/配色」
        aspect = w / h if h else 0
        hint = "layout/structural" if (area > 0.01 * total_px or aspect > 6 or aspect < 1 / 6) else "style/color"
        regions.append(
            {
                "bbox": [int(x), int(y), int(w), int(h)],
                "area_px": int(area),
                "area_ratio": round(area / total_px, 5),
                "mean_delta": round(mean_delta, 1),
                "hint": hint,
            }
        )
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)

    regions.sort(key=lambda r: r["area_px"], reverse=True)

    heat = cv2.applyColorMap(delta, cv2.COLORMAP_JET)
    cv2.imwrite(str(out / "diff_annotated.png"), annotated)
    cv2.imwrite(str(out / "diff_heatmap.png"), heat)

    report = {
        "design": args.design,
        "impl": args.impl,
        "canvas": [dw, dh],
        "aligned": method != "resize-fallback",
        "alignment_method": method,
        "inliers": inliers,
        "threshold": args.threshold,
        "diff_ratio": round(diff_ratio, 4),
        "region_count": len(regions),
        "regions": regions,
        "annotated_png": str(out / "diff_annotated.png"),
        "heatmap_png": str(out / "diff_heatmap.png"),
        "note": "regions[].hint 仅是几何粗启发；content/style/layout/size 的语义分类交给 ui-fidelity-reviewer (VLM)。像素对齐 ≠ 还原正确，须叠加 reviewer 语义判断 + 交互行为验证。",
    }
    (out / "diff.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # stdout 给 agent 一行摘要 + 完整 JSON 路径
    if method == "resize-fallback":
        sys.stderr.write(
            "[visual_diff] ⚠ ORB 对齐失败，退化为等比缩放——diff_ratio 可能含错位假阳性，"
            "结果仅供参考，以 reviewer 语义判断为准。\n"
        )
    print(
        f"diff_ratio={diff_ratio:.4f} regions={len(regions)} "
        f"align={method}(inliers={inliers}) → {out / 'diff.json'}"
    )


if __name__ == "__main__":
    main()
