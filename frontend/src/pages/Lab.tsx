import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Papa from "papaparse";
import "../css/Lab.css";

const formatTime = (seconds: number) => {
    if (!isFinite(seconds)) return "--:--";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

type FramePoints = { [frame: string]: { x: number; y: number }[] };

export const Lab = () => {
    const [videoUrl, setVideoUrl] = useState<string>("");
    const [csvUrl, setCsvUrl] = useState<string>("");
    const [frames, setFrames] = useState<FramePoints>({});
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [videosReady, setVideosReady] = useState(false);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(0);
    const navigate = useNavigate();

    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // Fetch video and CSV URLs
    useEffect(() => {
        fetch("http://127.0.0.1:8000/video/latest/")
            .then(res => res.json())
            .then(data => {
                if (data.video1) setVideoUrl(data.video1);
                if (data.csv_url) setCsvUrl(data.csv_url); // Adjust this key to match your backend response
            });
    }, []);

    // Fetch and parse CSV
    useEffect(() => {
        if (!csvUrl) return;
        fetch(csvUrl)
            .then(res => res.text())
            .then(csvText => {
                Papa.parse(csvText, {
                    header: true,
                    complete: (results: Papa.ParseResult<any>) => {
                        const grouped: FramePoints = {};
                        (results.data as any[]).forEach((row: any) => {
                            const frame = row.frame;
                            const points: { x: number; y: number }[] = [];
                            Object.keys(row).forEach((key) => {
                                if (key.endsWith("_x")) {
                                    const idx = key.replace("landmark_", "").replace("_x", "");
                                    const yKey = `landmark_${idx}_y`;
                                    if (row[key] && row[yKey]) {
                                        points.push({ x: parseFloat(row[key]), y: parseFloat(row[yKey]) });
                                    }
                                }
                            });
                            if (points.length) grouped[frame] = points;
                        });
                        setFrames(grouped);
                    }
                });
            });
    }, [csvUrl]);

    // Draw points for the current frame
    useEffect(() => {
        if (!canvasRef.current || !videoRef.current) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Find the closest frame to the current video time
        const fps = 30; // or get from video metadata
        const frameIdx = Math.round(currentTime * fps);
        const points = frames[frameIdx] || [];

        ctx.fillStyle = "#00bcd4";
        points.forEach(pt => {
            ctx.beginPath();
            ctx.arc(pt.x * canvas.width, pt.y * canvas.height, 5, 0, 2 * Math.PI);
            ctx.fill();
        });
    }, [currentTime, frames]);

    // Play/Pause video
    useEffect(() => {
        if (videosReady) {
            if (isPlaying) {
                videoRef.current?.play();
            } else {
                videoRef.current?.pause();
            }
        }
    }, [isPlaying, videosReady]);

    // Sync currentTime on state update
    useEffect(() => {
        if (!videosReady) return;
        if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.1) {
            videoRef.current.currentTime = currentTime;
        }
    }, [currentTime, videosReady]);

    // Handle metadata loaded
    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            const dur = videoRef.current.duration || 0;
            setStartTime(0);
            setEndTime(dur);
            setVideosReady(true);
        }
    };

    // Update current time when video plays
    const handleTimeUpdate = () => {
        if (!videosReady) return;
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    // Handle user seek
    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const time = Number(e.target.value);
        setCurrentTime(time);
    };

    return (
        <motion.div
            className="lab-container"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, type: "spring" }}
        >
            <motion.button
                className="back-button"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05, boxShadow: "0 4px 24px #00bcd4" }}
                whileTap={{ scale: 0.95 }}
                style={{color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer"}}
            >
                Back
            </motion.button>
            
            <motion.h2
                className="lab-title"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.6 }}
            >
                Lab Solstice
            </motion.h2>

            <motion.div
                className="lab-videos-row"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3, duration: 0.6 }}
                style={{ display: "flex", gap: "2rem", justifyContent: "center" }}
            >
                <motion.video
                    ref={videoRef}
                    src={videoUrl}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    controls={false}
                    loop={false} // <-- changed
                    onEnded={() => setIsPlaying(false)} // <-- add this
                    className="lab-video"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.5 }}
                    whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #1976d2" }}
                    width={400}
                    height={300}
                />
                <canvas
                    ref={canvasRef}
                    width={400}
                    height={300}
                    style={{ background: "#222", borderRadius: "1rem" }}
                />
            </motion.div>

            <motion.div
                className="lab-controls"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
            >
                <motion.button
                    onClick={() => setIsPlaying(!isPlaying)}
                    whileHover={{ scale: 1.08, backgroundColor: "#1565c0" }}
                    whileTap={{ scale: 0.96 }}
                >
                    {isPlaying ? "Pause" : "Play"}
                </motion.button>

                <motion.input
                    type="range"
                    min={startTime}
                    max={endTime - 0.05} // avoid seeking to very end
                    value={currentTime}
                    onChange={handleSeek}
                    step={0.01}
                    disabled={!videosReady}
                    whileFocus={{ scale: 1.03 }}
                />

                <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                >
                    {formatTime(currentTime)} / {formatTime(endTime)}
                </motion.span>
            </motion.div>
        </motion.div>
    );
};