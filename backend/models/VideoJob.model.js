import mongoose, { mongo } from "mongoose"

const eventSchema=new mongoose.Schema({
   event_id: Number,
  start_time: String,
  end_time: String,
  duration_sec: Number,
  objects_detected: { type: Map, of: Number },
  track_ids: [Number],
  keyframe: String,
  keyframeUrl: String,
  activity_type: String,
  scene_description: String,
  alert_level: { type: String, default: "normal" }
},{_id:false})

const videoJobSchema=new mongoose.Schema({
originalFilename: { type: String, required: true },
  videoUrl: { type: String, required: true },
  status: {
    type: String,
    enum: ["processing", "completed", "failed"],
    default: "processing"
  },
  errorMessage: { type: String, default: "" },
  video_duration_sec: Number,
  total_raw_tracks_filtered: Number,
  total_events_analyzed: Number,
  executive_summary: String,
  events: [eventSchema]
}, { timestamps: true });

export default mongoose.model("VideoJob",videoJobSchema)