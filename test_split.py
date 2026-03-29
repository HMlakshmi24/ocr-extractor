"""
Fine-grained row analysis around key gutter zones.
Also tests mean180 B=246 D=210 to see what false split it creates in PDF1.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
from pdf2image import convert_from_path
from src.file_parser import POPPLER_PATH

PDF1 = r"c:\Users\hmlak\OneDrive\Desktop\office works\extraction\storage\uploads\business_cards_1.pdf"
PDF2 = r"c:\Users\hmlak\OneDrive\Desktop\office works\extraction\storage\uploads\business_cards_2.pdf"


def find_h_splits_verbose(proj, total, bright, dark, min_seg_pct=0.08, min_gutter=3, label=""):
    """Same as _find_h_splits but prints decisions."""
    MIN_SEG = int(total * min_seg_pct)
    smooth = np.convolve(proj, np.ones(3) / 3, mode='same')
    splits       = [0]
    in_bright    = float(smooth[0]) >= bright
    gutter_start = 0 if in_bright else -1
    recorded = []

    for i in range(1, total):
        v = float(smooth[i])
        if not in_bright and v >= bright:
            in_bright    = True; gutter_start = i
        elif in_bright and v < dark:
            in_bright = False
            if gutter_start >= 0:
                region = smooth[gutter_start:i]
                peak   = gutter_start + int(np.argmax(region))
                gw = i - gutter_start
                dist = peak - splits[-1]
                accept = gw >= min_gutter and dist >= MIN_SEG
                recorded.append({
                    'start': gutter_start, 'end': i, 'peak': peak,
                    'gw': gw, 'dist': dist, 'accept': accept,
                    'peak_smooth': float(smooth[peak])
                })
                if accept:
                    splits.append(peak)

    splits.append(total)
    if recorded:
        print(f"  [{label}]  Gutter candidates:")
        for r in recorded:
            tag = "ACCEPT" if r['accept'] else f"REJECT(gw={r['gw']}<{min_gutter} or dist={r['dist']}<{MIN_SEG})"
            print(f"    y={r['start']}-{r['end']}  peak={r['peak']}  smooth_peak={r['peak_smooth']:.1f}  {tag}")
    return splits


def load_page(pdf_path):
    poppler = POPPLER_PATH if os.path.exists(POPPLER_PATH) else None
    pages = convert_from_path(pdf_path, dpi=250, poppler_path=poppler)
    page = pages[0].convert('RGB')
    gray = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2GRAY)
    return page, gray


print("="*70)
print("PDF1: mean180 B=246 D=210 -- why does this give 5 rows?")
page1, gray1 = load_page(PDF1)
_, b180_1 = cv2.threshold(gray1, 180, 255, cv2.THRESH_BINARY)
mean180_1 = np.mean(b180_1.astype(float), axis=1)
splits1 = find_h_splits_verbose(mean180_1, page1.height, 246, 210, label="mean180 B246 D210 PDF1")
print(f"  Final splits: {splits1}")

print()
print("="*70)
print("PDF2: mean180 B=246 D=210 -- what gutters does it find?")
page2, gray2 = load_page(PDF2)
_, b180_2 = cv2.threshold(gray2, 180, 255, cv2.THRESH_BINARY)
mean180_2 = np.mean(b180_2.astype(float), axis=1)
splits2 = find_h_splits_verbose(mean180_2, page2.height, 246, 210, label="mean180 B246 D210 PDF2")
print(f"  Final splits: {splits2}")

print()
print("="*70)
print("PDF1: p5_gray FINE-GRAINED around y=250-400 (where false split occurs)")
p5_1 = np.percentile(gray1.astype(float), 5, axis=1)
print("  y   p5_gray   mean180")
for y in range(250, 420, 5):
    print(f"  {y:4d}  {p5_1[y]:7.1f}   {mean180_1[y]:7.1f}")

print()
print("="*70)
print("PDF2: p5_gray FINE-GRAINED around y=850-980 (first gutter zone)")
p5_2 = np.percentile(gray2.astype(float), 5, axis=1)
_, b180_2 = cv2.threshold(gray2, 180, 255, cv2.THRESH_BINARY)
mean180_2_arr = np.mean(b180_2.astype(float), axis=1)
print("  y   p5_gray   mean180")
for y in range(840, 970, 3):
    m = "GUTTER" if p5_2[y] > 200 else ""
    print(f"  {y:4d}  {p5_2[y]:7.1f}   {mean180_2_arr[y]:7.1f}  {m}")

print()
print("="*70)
print("PDF2: p5_gray around gutters 2 and 3 (y=1270-1320 and y=1680-1730)")
print("  y   p5_gray   mean180")
for y in list(range(1270,1320,3)) + list(range(1680,1730,3)):
    m = "GUTTER" if p5_2[y] > 200 else ""
    print(f"  {y:4d}  {p5_2[y]:7.1f}   {mean180_2_arr[y]:7.1f}  {m}")

print()
print("="*70)
print("PDF1: p5_gray around its gutters (y=790-870, y=1710-1740)")
print("  y   p5_gray   mean180")
for y in list(range(790,870,3)) + list(range(1710,1745,2)):
    m = "GUTTER" if p5_1[y] > 200 else ""
    print(f"  {y:4d}  {p5_1[y]:7.1f}   {mean180_1[y]:7.1f}  {m}")

print("\nDone.")
