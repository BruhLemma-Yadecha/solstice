// VideoUpload.tsx
import React, { useState } from "react";

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
    
    console.log(response)
    onUploadComplete();
  };

  return (
    <div>
      <input type="file" accept="video/*" onChange={handleChange} />
      <button onClick={handleUpload} disabled={!video}>
        Upload Video
      </button>
    </div>
  );
};

export default VideoUpload;