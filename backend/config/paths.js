import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const BACKEND_ROOT = path.resolve(__dirname, "..");
export const PROJECT_ROOT = path.resolve(BACKEND_ROOT, "..");

export const UPLOADS_DIR = path.join(BACKEND_ROOT, "uploads");
export const OUTPUTS_DIR = path.join(BACKEND_ROOT, "outputs");

fs.mkdirSync(UPLOADS_DIR, { recursive: true });
fs.mkdirSync(OUTPUTS_DIR, { recursive: true });

export const PYTHON_BIN = path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe");
export const PIPELINE_SCRIPT = path.join(PROJECT_ROOT, "cv_engine", "pipeline.py");
export const QA_SCRIPT = path.join(PROJECT_ROOT, "cv_engine", "qa_engine.py");