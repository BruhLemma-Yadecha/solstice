// VideoUpload.tsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import "../css/VideoUpload.css";

const VideoUpload = () => {
  const [video, setVideo] = useState<File | null>(null);
  const [option, setOption] = useState<string>("option1");
  const [upload, setUpload] = useState("Upload Video");
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setVideo(e.target.files[0]);
    }
  };

  const handleOptionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setOption(e.target.value);
  };

  const handleUpload = async () => {
    if (!video) return;
    setUpload("Uploading...");
    const formData = new FormData();
    formData.append("video", video);
    formData.append("option", option);

    const response = await fetch("http://127.0.0.1:8000/upload/", {
      method: "POST",
      body: formData,
    });

    console.log(response);
    setUpload("Uploaded");
    navigate("/lab");
  };

  return (
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
            whileFocus={{ scale: 1.03, borderColor: "#1976d2" }}
          />
          {video ? video.name : "Choose a video"}
        </motion.label>
        <motion.select
          className="video-upload-select"
          value={option}
          onChange={handleOptionChange}
          whileFocus={{ scale: 1.03, borderColor: "#1976d2" }}
          whileHover={{ scale: 1.04, borderColor: "#42a5f5" }}
        >
          <option value="alg1">Algorithm 1</option>
          <option value="alg2">Algorithm 2</option>
          <option value="alg3">Algorithm 3</option>
        </motion.select>
        <motion.button
          className="video-upload-btn"
          onClick={handleUpload}
          disabled={!video || upload==="Uploading..."}
          whileHover={{
            scale: video ? 1.08 : 1,
            backgroundColor: video ? "#00bcd4" : "#ccc",
            color: "#fff",
            boxShadow: (video || !(upload==="Uploading...")) ? "0 4px 24px #00bcd4" : "none",
          }}
          whileTap={{ scale: 0.96 }}
        >
          {upload}
        </motion.button>
      </motion.div>
    </div>
  );
};

export default VideoUpload;