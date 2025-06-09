import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

type VideoFile = {
  name: string;
  url: string;
  id?: string;
};

const ListVideo = () => {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [selected, setSelected] = useState<VideoFile | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch the list of videos from your Django API endpoint
    fetch("http://127.0.0.1:8000/video/videos/")
      .then(res => res.json())
      .then(data => {
        // data should be an array of video objects with .file and .id
        const files = (data || []).map((video: any) => ({
          name: video.file.split("/").pop(),
          url: video.file,
          id: video.id,
        }));
        setVideos(files);
      });
  }, []);

  const handleSelect = (video: VideoFile) => {
    setSelected(video);
  };

  const handleSendToUpload = async () => {
    if (!selected) return;
    // Fetch the video file as a Blob
    const response = await fetch(selected.url);
    const blob = await response.blob();
    // Create a File object (optional, for name)
    const file = new File([blob], selected.name, { type: blob.type });

    // Prepare FormData
    const formData = new FormData();
    formData.append("video_file", file);
    formData.append("pose_algorithm_id", "1"); // or let user choose

    // Upload to backend
    const uploadRes = await fetch("http://127.0.0.1:8000/video/upload/", {
      method: "POST",
      body: formData,
    });
    const uploadData = await uploadRes.json();
    localStorage.setItem("video_job_id", uploadData.id);

    // Navigate to /lab
    navigate("/lab");
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1 style={{ color: "#00bcd4", textAlign:"center" }}>Select a Video from Server</h1>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "2rem", justifyContent: "center" }}>
        {videos.map(video => (
          <motion.div
            key={video.name}
            style={{
              border:"2px solid #00bcd4",
              borderRadius: "1rem",
              padding: "1rem",
              width: "400px",
              background: selected?.name === video.name ? "#00bcd4" : "#002f3b", // highlight selected
              cursor: "pointer",
              color: selected?.name === video.name ? "#002f3b" : "#00bcd4",      // invert text color if selected
              transition: "background 0.2s, color 0.2s, border 0.2s",
            }}
            whileHover={{ scale: 1.05, boxShadow: "0 4px 24px #00bcd4" }}
            onClick={() => handleSelect(video)}
          >
            <video
              src={video.url}
              width={400}
              height={220}
              style={{ borderRadius: "0.5rem", background: "#111", margin:"auto" }}
              controls={false}
              muted
            />
            <div style={{ marginTop: "0.5rem", fontSize: "0.9rem" }}>
              <strong>{video.name}</strong>
            </div>
          </motion.div>
        ))}
      </div>
      <div style={{ marginTop: "3rem", alignContent: "center", display: "flex", justifyContent: "center", flexDirection: "column", gap: "1rem", margin:"auto", alignItems: "center" }}>
        <div>
            <motion.button
                className="back-button"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", boxShadow: "0 2px 0px #00bcd4" }}
            >
                Back
          </motion.button>
        </div>
        <motion.button
          className="video-upload-btn"
          onClick={handleSendToUpload}
          disabled={!selected}
          whileHover={{
            scale: selected ? 1.08 : 1,
            backgroundColor: selected ? "#00bcd4" : "#ccc",
            color: "#fff",
            boxShadow: selected ? "0 4px 24px #00bcd4" : "none",
          }}
          whileTap={{ scale: 0.96 }}
            style={{
                color: "#fff",
                backgroundColor: selected ? "#00bcd4" : "#ccc",
                border: "none",
                padding: "0.5rem 1rem",
                borderRadius: "0.5rem",
                cursor: selected ? "pointer" : "not-allowed",
                boxShadow: selected ? "0 2px 0px #00bcd4" : "none",
                width: "200px",
            }}
        >
            {selected ? "Send to Lab" : "Select a video first"}
        </motion.button>
      </div>
    </div>
  );
};

export default ListVideo;