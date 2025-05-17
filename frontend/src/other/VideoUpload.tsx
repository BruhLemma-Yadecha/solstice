// VideoUpload.tsx
import React, { useState } from "react";
import { motion } from "framer-motion";
import "./VideoUpload.css"; // Import the CSS file

type VideoUploadProps = {
  onUploadComplete: () => void;
};

const VideoUpload = ({ onUploadComplete }: VideoUploadProps) => {
  const [video, setVideo] = useState<File | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setVideo(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!video) return;
    const formData = new FormData();
    formData.append("video", video);

    const response = await fetch("http://127.0.0.1:8000/upload/", {
      method: "POST",
      body: formData,
    });

    console.log(response);
    onUploadComplete();
  };

  return (
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
        <input
          type="file"
          accept="video/*"
          onChange={handleChange}
          className="video-upload-input"
        />
        {video ? video.name : "Choose a video"}
      </motion.label>
      <motion.button
        className="video-upload-btn"
        onClick={handleUpload}
        disabled={!video}
        whileHover={{
          scale: video ? 1.08 : 1,
          backgroundColor: video ? "#00bcd4" : "#ccc",
          color: "#fff",
          boxShadow: video ? "0 4px 24px #00bcd4" : "none",
        }}
        whileTap={{ scale: 0.96 }}
      >
        Upload Video
      </motion.button>
    </motion.div>
  );
};

export default VideoUpload;