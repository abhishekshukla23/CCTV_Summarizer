import os
import json
import ollama



base_dir=os.path.dirname(os.path.abspath(__file__))

final_output_path=os.path.join(base_dir,"final_summary.json")

qa_model="qwen3:4b"

def load_video_context(summary_path):
    with open(summary_path,"r") as f:
        data=json.load(f)
        
    events_text=[]
    for ev in data.get("events",[]):
        events_text.append(
            f"Event #{ev['event_id']} | Time: {ev['start_time']} to {ev['end_time']} "
            f"| Objects: {json.dumps(ev['objects_detected'])} "
            f"| Activity: {ev['activity_type']} "
            f"| Details: {ev['scene_description']}"
        )
    
    context_block=(
        f"Overall Summary: {data.get('executive_summary', '')}\n\n"
        f"Timestamped Event Logs:\n" + "\n".join(events_text)
    )
    
    return context_block


import re

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "relevant_timestamps": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["answer", "relevant_timestamps"]
}

TS_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")

def ask_video_question(question, context_block):
    system_prompt = (
        "You are a CCTV Video Investigation Assistant. "
        "Answer in 1-3 sentences using ONLY the event logs provided. "
        "If something is not in the logs, say it was not observed. "
        "Do not explain your reasoning. "
        "Note: the 'person' count in an event is the number of people detected "
        "during that event window, NOT the number present at the same instant, "
        "and events overlap in time, so do not add counts across events. "
        "relevant_timestamps must be HH:MM:SS values from the logs, or an empty list."
    )
    user_prompt = f"CCTV Event Logs:\n{context_block}\n\nQuestion: {question}"

    response = ollama.chat(
        model=qa_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        format=ANSWER_SCHEMA,
        think=False,
        options={"temperature": 0.1, "num_predict": 300, "num_ctx": 4096},
        keep_alive="30m",
    )

    try:
        data = json.loads(response["message"]["content"])
    except json.JSONDecodeError:
        return {"answer": "Could not parse model output.", "relevant_timestamps": []}

    timestamps = [t for t in data.get("relevant_timestamps", []) if TS_RE.match(t)]
    return {"answer": data.get("answer", "").strip(), "relevant_timestamps": timestamps}


if __name__ == "__main__":
    if not os.path.exists(final_output_path):
        raise FileNotFoundError(f"Run vlm_analyzer.py first to generate {final_output_path}")
    
    context=load_video_context(final_output_path)
    
    print("=== CCTV Video Q&A Ready (type 'exit' to quit) ===\n")
    
    while True:
        user_q=input("Ask about the video:").strip()
        if user_q.lower() in ["exit","quit"]:
            break
        
        if not user_q:
            continue
        
        result=ask_video_question(user_q,context)
        print(f"\nAnswer: {result.get('answer')}")
        print(f"Timestamps: {result.get('relevant_timestamps')}\n")