// VideoUpload.tsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import StatusPage from "./status";
import "../css/VideoUpload.css";

const VideoUpload = () => {
  const [video, setVideo] = useState<File | null>(null);
  const [option, setOption] = useState<number>(1);
  const [upload, setUpload] = useState("Upload Video");
  const [status, setStatus] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setVideo(e.target.files[0]);
    }
  };

  const handleOptionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setOption(Number(e.target.value));
  };

  const handleUpload = async () => {
    if (!video) return;
    setUpload("Uploading...");
    const formData = new FormData();
    formData.append("video_file", video);
    formData.append("pose_algorithm_id", "1");

    const response = await fetch("http://127.0.0.1:8000/video/upload/", {
      method: "POST",
      body: formData,
    });

    const responseData = await response.json();
    console.log(responseData);
    localStorage.setItem("video_job_id", responseData.id);

    setUpload("Uploaded");
    navigate("/lab");
  };

  return (
    <>
      <div style={{marginTop:"30vh", height:"100%"}}>
        <motion.div
          className="video-upload-container"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, type: "spring" }}
        >
          <motion.label
            className="video-upload-label"
            whileHover={{ scale: 1.05, boxShadow: "0 4px 24px #00bcd4" }}
            whileTap={{ scale: 0.98 }}
          >
            <motion.input
              type="file"
              accept="video/*"
              onChange={handleChange}
              className="video-upload-input"
              style={{ display: "none" }}
              whileFocus={{ scale: 1.03, borderColor: "#00bcd4" }}
            />
            {video ? video.name : "Choose a video"}
          </motion.label>
          <motion.select
            className="video-upload-select"
            value={option}
            onChange={handleOptionChange}
            whileFocus={{ scale: 1.03, borderColor: " #00bcd4" }}
            whileHover={{ scale: 1.04, borderColor: " #00bcd4" }}
          >
            <option value="1">Algorithm 1</option>
            <option value="2">Algorithm 2</option>
            <option value="3">Algorithm 3</option>
          </motion.select>
          <motion.button
            className="video-upload-btn"
            onClick={handleUpload}
            disabled={!video || upload==="Uploading..."}
            whileHover={{
              scale: video ? 1.08 : 1,
              backgroundColor: video ? " #00bcd4" : " #ccc",
              color: "#fff",
              boxShadow: (video || !(upload==="Uploading...")) ? "0 4px 24px #00bcd4" : "none",
            }}
            whileTap={{ scale: 0.96 }}
          >
            {upload}
          </motion.button>
        </motion.div>
      </div>
      {status && (
      <div style={{position: "fixed", bottom: "300px", width: "100%", height: "200px", display: "flex", justifyContent: "center", alignItems: "center"}}>
          <StatusPage/>
      </div>)}
      <div className="video-upload-footer">
        <motion.button
            className="back-button"
            onClick={() => setStatus(!status)}
            whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
            whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
            style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "auto", boxShadow: "0 2px 0px #00bcd4" }}
        >
            Status
        </motion.button>
      </div>
    </>
  );
};

export default VideoUpload;