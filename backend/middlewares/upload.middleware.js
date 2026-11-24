import multer from "multer"

import {UPLOADS_DIR} from "../config/paths.js"


const storage=multer.diskStorage({
    destination: (_, __, cb) => cb(null, UPLOADS_DIR),
  filename: (_, file, cb) => {
    const safeName = `${Date.now()}_${file.originalname.replace(/\s+/g, "_")}`;
    cb(null, safeName);
  },
})


const fileFilter=(_,file,cb)=>{
    if(file.mimetype.startsWith("video/")){
        cb(null,true)
    }
    else{
        cb(new Error("only video files are allowed"),false)
    }
}


export const uploadVideo=multer({
    storage,
    fileFilter,
    limits:{fileSize:500*1024*1024}
})