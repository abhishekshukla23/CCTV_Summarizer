import fs from "fs";
import path from "path";
import VideoJob from "../models/VideoJob.model.js";
import { OUTPUTS_DIR } from "../config/paths.js";
import {
  runPipelineInBackground,
  askVideoQuestionService,
} from "../services/python.service.js";

export async function uploadVideoHandler(req, res) {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No video file uploaded." });
    }

    const job = await VideoJob.create({
      originalFilename: req.file.originalname,
      videoUrl: `/uploads/${req.file.filename}`,
      status: "processing",
    });

    const jobId = job._id.toString();

    res.status(202).json({
      message: "Video uploaded. AI processing started.",
      jobId,
      status: job.status,
    });

    runPipelineInBackground(jobId, req.file.path);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

export async function getAllVideos(_, res) {
  try {
    const jobs = await VideoJob.find().sort({ createdAt: -1 });
    res.json(jobs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

export async function getVideoById(req, res) {
  try {
    const job = await VideoJob.findById(req.params.id);
    if (!job) return res.status(404).json({ error: "Video job not found." });
    res.json(job);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

export async function askVideoQuestion(req, res) {
  try {
    const { question } = req.body;
    if (!question || !question.trim()) {
      return res.status(400).json({ error: "Question is required." });
    }

    const summaryPath = path.join(OUTPUTS_DIR, req.params.id, "summary.json");
    if (!fs.existsSync(summaryPath)) {
      return res.status(404).json({ error: "Summary not ready for this video." });
    }

    const answerData = await askVideoQuestionService(summaryPath, question.trim());
    res.json(answerData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}