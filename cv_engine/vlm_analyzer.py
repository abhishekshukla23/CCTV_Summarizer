import os
import json
import ollama


base_dir=os.path.dirname(os.path.abspath(__file__))

project_root=os.path.dirname(base_dir)
grouped_events_path=os.path.join(base_dir,"events_grouped.json")
final_output_path=os.path.join(base_dir,"final_summary.json")

vlm_model="qwen3-vl:4b"

def resolve_image_path(keyframe_path):
    
    normalized=keyframe_path.replace("\\","/")
    if os.path.exists(normalized):
        return normalized
    
    root_joined=os.path.join(project_root,normalized)
    if os.path.exists(root_joined):
        return root_joined
    
    return os.path.join(base_dir,normalized)


def analyze_single_event(event):
    img_path=resolve_image_path(event["keyframe"])
    
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"keyframe not found at:{img_path}")
    
    prompt = f"""
You are an AI CCTV surveillance analyst.
Analyze this CCTV keyframe captured between {event['start_time']} and {event['end_time']} (duration: {event['duration_sec']}s).
Computer Vision object counts in this window: {json.dumps(event['objects_detected'])}.

Return a JSON object with exactly these 3 keys:
- "activity_type": short 2-4 word label (e.g., "Pedestrian Foot Traffic", "Crowd Gathering", "Loitering Near Entrance")
- "scene_description": 1-2 factual sentences describing what people/vehicles are doing, the setting, and notable visual details.
- "alert_level": "normal", "attention", or "critical"
"""
    response = ollama.chat(
        model=vlm_model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [img_path]
            }
        ],
        format="json"  
    )

    return json.loads(response["message"]["content"])


def generate_overall_summary(enriched_events):
    timeline_text="\n".join(
        f"- [{ev['start_time']} - {ev['end_time']}] ({ev['activity_type']}): {ev['scene_description']}"
        for ev in enriched_events
    )
    prompt = f"""
Based ONLY on these timestamped CCTV event logs, write a concise 3-4 sentence executive summary of everything that occurred in the footage. Do not invent details not present in the logs.

Event Logs:
{timeline_text}
"""
    response=ollama.chat(
        model=vlm_model,
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ]
    )
    return response["message"]["content"].strip()

if __name__ == "__main__":
    with open(grouped_events_path, "r") as f:
        grouped_events = json.load(f)

    enriched_events = []
    print(f"Analyzing {len(grouped_events)} scene events using {vlm_model}...\n")

    for ev in grouped_events:
        print(f"Processing Event #{ev['event_id']} ({ev['start_time']} - {ev['end_time']})...")
        vlm_result = analyze_single_event(ev)

        enriched_event = {
            **ev,
            "activity_type": vlm_result.get("activity_type", "Unclassified Activity"),
            "scene_description": vlm_result.get("scene_description", ""),
            "alert_level": vlm_result.get("alert_level", "normal")
        }
        enriched_events.append(enriched_event)
        print(f"  -> {enriched_event['activity_type']}: {enriched_event['scene_description']}\n")

    print("Generating overall executive summary...")
    executive_summary = generate_overall_summary(enriched_events)

    final_report = {
        "total_raw_tracks_filtered": 52,
        "total_events_analyzed": len(enriched_events),
        "executive_summary": executive_summary,
        "events": enriched_events
    }

    with open(final_output_path, "w") as f:
        json.dump(final_report, f, indent=2)

    print("\n=== FINAL CCTV SUMMARY ===")
    print(executive_summary)
    print(f"\nSaved complete report to {final_output_path}")