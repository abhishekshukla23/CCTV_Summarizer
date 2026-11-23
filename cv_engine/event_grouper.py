import os
import json
from collections import Counter


base_dir=os.path.dirname(os.path.abspath(__file__))
raw_events_path=os.path.join(base_dir,"events_raw.json")
grouped_events_path=os.path.join(base_dir,"events_grouped.json")

window_size_sec=4.0


def timestamp_to_second(ts_str):
    h,m,s=map(int,ts_str.split(":"))
    return h*3600+m*60+s


def seconds_to_timestamp(seconds):
    hrs=int(seconds//3600)
    mins=int((seconds%3600)//60)
    secs=int(seconds%60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def group_events(raw_events,window_sec=4.0):
    if not raw_events:
        return []
    
    for ev in raw_events:
        ev["start_sec"]=timestamp_to_second(ev["start_time"])
        ev["end_sec"]=timestamp_to_second(ev["end_time"])
        
        
    sorted_events=sorted(raw_events,key=lambda x:x["start_sec"])
    
    
    grouped=[]
    current_group=[sorted_events[0]]
    group_start=sorted_events[0]["start_sec"]
    
    
    for ev in sorted_events[1:]:
        if ev["start_sec"]-group_start<=window_sec:
            current_group.append(ev)
        else:
            grouped.append(finalize_group(current_group,len(grouped)+1))
            current_group=[ev]
            group_start=ev["start_sec"]
            
    if current_group:
        grouped.append(finalize_group(current_group,len(grouped)+1))
        
    return grouped


def finalize_group(events_in_window,event_number):
    
    start_sec=min(e["start_sec"] for e in events_in_window)
    end_sec=max(e["end_sec"] for e in events_in_window)
    
    
    object_counts=dict(Counter(e["object"] for e in events_in_window))
    
    best_track=max(events_in_window,key=lambda e:e["duration_sec"])
    
    return {
        "event_id": event_number,
        "start_time": seconds_to_timestamp(start_sec),
        "end_time": seconds_to_timestamp(end_sec),
        "duration_sec": round(end_sec - start_sec, 1),
        "objects_detected": object_counts,
        "track_ids": [e["track_id"] for e in events_in_window],
        "keyframe": best_track["keyframe"]
    }
    
if __name__=="__main__":
    with open(raw_events_path, "r") as f:
        raw_data = json.load(f)

    merged_events = group_events(raw_data, window_sec=window_size_sec)

    with open(grouped_events_path, "w") as f:
        json.dump(merged_events, f, indent=2)

    print(f"Reduced {len(raw_data)} raw tracks -> {len(merged_events)} grouped scene events!")
    print(json.dumps(merged_events, indent=2))
    
