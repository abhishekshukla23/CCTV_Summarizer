import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { connectDB } from "./config/db.js";
import { UPLOADS_DIR, OUTPUTS_DIR } from "./config/paths.js";
import videoRoutes from "./routes/video.routes.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// Static media serving
app.use("/uploads", express.static(UPLOADS_DIR));
app.use("/outputs", express.static(OUTPUTS_DIR));

// API routes
app.use("/api/videos", videoRoutes);

const port = process.env.PORT || 5000;

connectDB().then(() => {
  app.listen(port, () => {
    console.log(`Backend running at http://localhost:${port}`);
  });
});