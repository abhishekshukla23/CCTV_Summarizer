import os
import json
import cv2 as cv
from ultralytics import YOLO


video_path="cv_engine/videos/people.mp4"
keyframes_dir="cv_engine/keyframes"

os.makedirs(keyframes_dir,exist_ok=True)

TARGET_CLASSES=[0,2,3,5,7,24]

def format_timestamp(seconds):
    hrs=int(seconds//3600)
    mins=int((seconds%3600)//60)
    secs=int(seconds%60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"

model=YOLO("yolov8n.pt")


cap=cv.VideoCapture(video_path)

fps=cap.get(cv.CAP_PROP_FPS) or 30.0

active_tracks={}

completed_events=[]
frame_idx=0


while True:
    success,frame=cap.read()
    if not success:
        break
    
    current_time=frame_idx/fps
    frame_idx+=1
    
    
    results=model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=TARGET_CLASSES,
        conf=0.35,
        verbose=False
    )
    
    boxes=results[0].boxes
    
    if boxes is not None and boxes.id is not None:
        xyxy_list=boxes.xyxy.cpu().numpy().astype(int)
        ids=boxes.id.cpu().numpy().astype(int)
        classes=boxes.cls.cpu().numpy().astype(int)
        
        for box,track_id,cls_id in zip(xyxy_list,ids,classes):
            x1,y1,x2,y2=box
            area=(x2-x1)*(y2-y1)
            label=model.names[cls_id]
            
            
            if track_id not in active_tracks:
                
                active_tracks[track_id]={
                    "track_id": int(track_id),
                    "class_name": label,
                    "start_time": current_time,
                    "last_seen": current_time,
                    "max_area": area,
                    "best_frame": frame.copy()
                }
            else:
                active_tracks[track_id]["last_seen"] = current_time
                if area > active_tracks[track_id]["max_area"]:
                    active_tracks[track_id]["max_area"] = area
                    active_tracks[track_id]["best_frame"] = frame.copy()

            
            cv.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv.putText(frame, f"{label} #{track_id}", (x1, max(20, y1 - 8)),
                        cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
    finished_ids = []
    for tid, data in active_tracks.items():
        if current_time - data["last_seen"] > 2.0:
            duration = data["last_seen"] - data["start_time"]
            if duration >= 1.5:  # Ignore brief 1-second flicker detections
                img_path = os.path.join(keyframes_dir, f"event_{tid}.jpg")
                cv.imwrite(img_path, data["best_frame"])
                completed_events.append({
                    "track_id": int(tid),
                    "object": data["class_name"],
                    "start_time": format_timestamp(data["start_time"]),
                    "end_time": format_timestamp(data["last_seen"]),
                    "duration_sec": round(duration, 1),
                    "keyframe": img_path
                })
            finished_ids.append(tid)

    for tid in finished_ids:
        del active_tracks[tid]

    cv.imshow("CCTV Tracker Preview (Press Q to stop)", frame)
    if cv.waitKey(1) & 0xFF == ord("q"):
        break

# 5. Flush any objects still in frame when the video ends
for tid, data in active_tracks.items():
    duration = data["last_seen"] - data["start_time"]
    if duration >= 1.5:
        img_path = os.path.join(keyframes_dir, f"event_{tid}.jpg")
        cv.imwrite(img_path, data["best_frame"])
        completed_events.append({
            "track_id": int(tid),
            "object": data["class_name"],
            "start_time": format_timestamp(data["start_time"]),
            "end_time": format_timestamp(data["last_seen"]),
            "duration_sec": round(duration, 1),
            "keyframe": img_path
        })

cap.release()
cv.destroyAllWindows()

# Save raw CV events to JSON
with open("events_raw.json", "w") as f:
    json.dump(completed_events, f, indent=2)

print(f"\nDone! Extracted {len(completed_events)} candidate events:")
print(json.dumps(completed_events, indent=2))        