import os
import sys
import json
import argparse
import cv2 as cv
from ultralytics import YOLO

base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.append(base_dir)
    
from event_grouper import group_events
from vlm_analyzer import analyze_single_event, generate_overall_summary


target_classes=[0, 2, 3, 5, 7, 24]


def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def extract_raw_tracks(video_path, keyframes_dir, show_preview=False):
    """Runs YOLO + ByteTrack headlessly (or with preview) and saves clean keyframes."""
    os.makedirs(keyframes_dir, exist_ok=True)
    model = YOLO("yolov8n.pt")

    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    fps = cap.get(cv.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    video_duration = round(total_frames / fps, 1) if total_frames > 0 else 0.0

    active_tracks = {}
    completed_events = []
    frame_idx = 0

    while True:
        success, frame = cap.read()
        if not success:
            break

        clean_frame = frame.copy()  # Untouched frame for VLM analysis
        current_time = frame_idx / fps
        frame_idx += 1

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=target_classes,
            conf=0.35,
            verbose=False
        )

        boxes = results[0].boxes
        if boxes is not None and boxes.id is not None:
            xyxy_list = boxes.xyxy.cpu().numpy().astype(int)
            ids = boxes.id.cpu().numpy().astype(int).tolist()
            classes = boxes.cls.cpu().numpy().astype(int)

            for box, track_id, cls_id in zip(xyxy_list, ids, classes):
                x1, y1, x2, y2 = box
                area = (x2 - x1) * (y2 - y1)
                label = model.names[cls_id]

                if track_id not in active_tracks:
                    active_tracks[track_id] = {
                        "track_id": track_id,
                        "class_name": label,
                        "start_time": current_time,
                        "last_seen": current_time,
                        "max_area": area,
                        "best_frame": clean_frame
                    }
                else:
                    active_tracks[track_id]["last_seen"] = current_time
                    if area > active_tracks[track_id]["max_area"]:
                        active_tracks[track_id]["max_area"] = area
                        active_tracks[track_id]["best_frame"] = clean_frame

                if show_preview:
                    cv.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        finished_ids = []
        for tid, data in active_tracks.items():
            if current_time - data["last_seen"] > 2.0:
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
                finished_ids.append(tid)

        for tid in finished_ids:
            del active_tracks[tid]

        if show_preview:
            cv.imshow("CCTV Tracker", frame)
            if cv.waitKey(1) & 0xFF == ord("q"):
                break

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
    if show_preview:
        cv.destroyAllWindows()

    return completed_events, video_duration


def run_full_pipeline(video_path, output_dir, window_sec=4.0):
    os.makedirs(output_dir, exist_ok=True)
    keyframes_dir = os.path.join(output_dir, "keyframes")

    print(f"[1/3] Tracking objects in: {video_path}")
    raw_tracks, video_duration = extract_raw_tracks(video_path, keyframes_dir, show_preview=False)

    print(f"[2/3] Grouping {len(raw_tracks)} raw tracks into time windows...")
    grouped_events = group_events(raw_tracks, window_sec=window_sec)

    print(f"[3/3] Analyzing {len(grouped_events)} scene events with local VLM...")
    enriched_events = []
    for ev in grouped_events:
        vlm_result = analyze_single_event(ev)
        # Store relative keyframe filename so frontend/backend can serve it easily
        ev_clean = {
            **ev,
            "keyframe": os.path.basename(ev["keyframe"]),
            "activity_type": vlm_result.get("activity_type", "Unclassified Activity"),
            "scene_description": vlm_result.get("scene_description", ""),
            "alert_level": vlm_result.get("alert_level", "normal")
        }
        enriched_events.append(ev_clean)

    executive_summary = generate_overall_summary(enriched_events) if enriched_events else "No significant object activity detected."

    final_report = {
        "video_duration_sec": video_duration,
        "total_raw_tracks_filtered": len(raw_tracks),
        "total_events_analyzed": len(enriched_events),
        "executive_summary": executive_summary,
        "events": enriched_events
    }

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"Pipeline complete! Summary saved to: {summary_path}")
    return final_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run end-to-end CCTV summarization pipeline")
    parser.add_argument("--video", required=True, help="Path to input CCTV video file")
    parser.add_argument("--output", required=True, help="Directory to save keyframes and summary.json")
    parser.add_argument("--window", type=float, default=4.0, help="Event grouping window in seconds")
    args = parser.parse_args()

    run_full_pipeline(args.video, args.output, window_sec=args.window)