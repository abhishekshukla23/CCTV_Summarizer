import {Router} from "express"

import {uploadVideo} from "../middlewares/upload.middleware.js"

import{
    uploadVideoHandler,
    getAllVideos,
    getVideoById,
    askVideoQuestion
} from "../controllers/video.controller.js"


const router=Router()

router.post("/upload",uploadVideo.single("video"),uploadVideoHandler)
router.get("/",getAllVideos)
router.get("/:id",getAllVideos)
router.post("/:id/ask",askVideoQuestion)

export default router;