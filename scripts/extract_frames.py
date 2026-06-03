import cv2
import os
import sys
import shutil

TARGET_FRAMES = int(sys.argv[1])
VIDEO_PATH = sys.argv[2]
OUTPUT_DIR = sys.argv[3]

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

os.makedirs(OUTPUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(VIDEO_PATH)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

step = max(1, total_frames // TARGET_FRAMES)

frame_id = 0
saved_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_id % step == 0:
        filename = os.path.join(OUTPUT_DIR, f"frame_{saved_id:04d}.jpg")
        cv2.imwrite(filename, frame)
        saved_id += 1

    frame_id += 1

cap.release()
print(f"Saved {saved_id} frames.")