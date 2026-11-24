import fs from "fs";
import path from "path";
import { spawn } from "child_process";
import VideoJob from "../models/VideoJob.model.js";
import {
  PYTHON_BIN,
  PIPELINE_SCRIPT,
  QA_SCRIPT,
  OUTPUTS_DIR,
} from "../config/paths.js";

export function runPipelineInBackground(jobId, inputVideoPath) {
  const jobOutputDir = path.join(OUTPUTS_DIR, jobId);

  const pyProcess = spawn(PYTHON_BIN, [
    PIPELINE_SCRIPT,
    "--video",
    inputVideoPath,
    "--output",
    jobOutputDir,
  ]);

  let stderrLog = "";

  pyProcess.stdout.on("data", (data) => {
    console.log(`[Pipeline ${jobId}]: ${data.toString().trim()}`);
  });

  pyProcess.stderr.on("data", (data) => {
    stderrLog += data.toString();
    console.error(`[Pipeline Err ${jobId}]: ${data.toString().trim()}`);
  });

  pyProcess.on("close", async (code) => {
    if (code !== 0) {
      await VideoJob.findByIdAndUpdate(jobId, {
        status: "failed",
        errorMessage: stderrLog || `Pipeline exited with code ${code}`,
      });
      return;
    }

    try {
      const summaryPath = path.join(jobOutputDir, "summary.json");
      const report = JSON.parse(fs.readFileSync(summaryPath, "utf-8"));

      const formattedEvents = (report.events || []).map((ev) => ({
        ...ev,
        keyframeUrl: `/outputs/${jobId}/keyframes/${ev.keyframe}`,
      }));

      await VideoJob.findByIdAndUpdate(jobId, {
        status: "completed",
        video_duration_sec: report.video_duration_sec,
        total_raw_tracks_filtered: report.total_raw_tracks_filtered,
        total_events_analyzed: report.total_events_analyzed,
        executive_summary: report.executive_summary,
        events: formattedEvents,
      });
      console.log(`Job ${jobId} completed and saved to MongoDB.`);
    } catch (err) {
      await VideoJob.findByIdAndUpdate(jobId, {
        status: "failed",
        errorMessage: err.message,
      });
    }
  });
}

export function askVideoQuestionService(summaryPath, question) {
  return new Promise((resolve, reject) => {
    const pyQa = spawn(PYTHON_BIN, [
      QA_SCRIPT,
      "--summary",
      summaryPath,
      "--question",
      question,
    ]);

    let stdoutData = "";
    let stderrData = "";

    pyQa.stdout.on("data", (d) => (stdoutData += d.toString()));
    pyQa.stderr.on("data", (d) => (stderrData += d.toString()));

    pyQa.on("close", (code) => {
      if (code !== 0) {
        return reject(new Error(stderrData || "Q&A execution failed."));
      }
      try {
        resolve(JSON.parse(stdoutData.trim()));
      } catch {
        reject(new Error("Invalid JSON from Q&A engine."));
      }
    });
  });
}