import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Papa from "papaparse";
import "../css/Lab.css";
import StatusPage from "./status";

const formatTime = (seconds: number) => {
    if (!isFinite(seconds)) return "--:--";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

type FramePoints = { [frame: number]: ({ x: number; y: number } | null)[] };

export const Lab = () => {
    const [videoUrl, setVideoUrl] = useState<string>("");
    const [csvUrl, setCsvUrl] = useState<string>("");
    const [frames, setFrames] = useState<FramePoints>({});
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [ex, setEx] = useState(0);
    const [videosReady, setVideosReady] = useState(false);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(0);
    const [status, setStatus] = useState(false);
    const navigate = useNavigate();

    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // Fetch video and CSV URLs
    useEffect(() => {
        fetch("http://127.0.0.1:8000/video/latest/")
            .then(res => res.json())
            .then(data => {
                if (data.video1) setVideoUrl(data.video1);
                if (data.csv_url) setCsvUrl(data.csv_url);
            });
    }, []);

    // Fetch and parse CSV into a mapping from frame number → 33-length array of {x,y} or null
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
                            const frameIdx = parseInt(row.frame, 10);
                            // Build an array of length 33; if a landmark is missing, put null
                            const points: ({ x: number; y: number } | null)[] = new Array(33).fill(null);

                            for (let i = 0; i < 33; i++) {
                                const xKey = `landmark_${i}_x`;
                                const yKey = `landmark_${i}_y`;
                                const xVal = parseFloat(row[xKey]);
                                const yVal = parseFloat(row[yKey]);
                                if (!isNaN(xVal) && !isNaN(yVal)) {
                                    points[i] = { x: xVal, y: yVal };
                                }
                            }

                            grouped[frameIdx] = points;
                        });
                        setFrames(grouped);
                    }
                });
            });
    }, [csvUrl]);

    // Draw a stick figure (with interpolation) onto the canvas on each time update
    useEffect(() => {
        if (!canvasRef.current || !videoRef.current) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const fps = 30;
        // Compute fractional frame index relative to ex
        const relativeTime = currentTime - ex;
        if (relativeTime < 0) return;
        const currentFrame = relativeTime * fps;
        const prevIdx = Math.floor(currentFrame);
        const nextIdx = Math.ceil(currentFrame);
        const alpha = currentFrame - prevIdx;

        const prevPoints = frames[prevIdx] || new Array(33).fill(null);
        const nextPoints = frames[nextIdx] || new Array(33).fill(null);

        // Interpolate between prev and next points
        const interpolatedPoints: ({ x: number; y: number } | null)[] = prevPoints.map((pt, i) => {
            const ptNext = nextPoints[i];
            if (pt && ptNext) {
                return {
                    x: pt.x * (1 - alpha) + ptNext.x * alpha,
                    y: pt.y * (1 - alpha) + ptNext.y * alpha,
                };
            } else if (pt) {
                return pt;
            } else if (ptNext) {
                return ptNext;
            }
            return null;
        });

        // Define MediaPipe 33-keypoint skeleton connections
        const skeleton: [number, number][] = [
            [0, 1], [1, 2], [2, 3], [3, 7],       // Right arm
            [0, 4], [4, 5], [5, 6], [6, 8],       // Left arm
            [9, 10],                              // Shoulders
            [11, 12],                             // Hips
            [11, 13], [13, 15],                   // Left leg
            [12, 14], [14, 16],                   // Right leg
            [11, 23], [12, 24],                   // Lower body
            [23, 25], [25, 27],                   // Left lower leg
            [24, 26], [26, 28],                   // Right lower leg
            [27, 29], [29, 31],                   // Left foot
            [28, 30], [30, 32],                   // Right foot
        ];

        ctx.strokeStyle = "#00bcd4";
        ctx.lineWidth = 2;

        // Draw each stick segment if both endpoints exist
        skeleton.forEach(([a, b]) => {
            const ptA = interpolatedPoints[a];
            const ptB = interpolatedPoints[b];
            if (ptA && ptB) {
                ctx.beginPath();
                ctx.moveTo(ptA.x * canvas.width, ptA.y * canvas.height);
                ctx.lineTo(ptB.x * canvas.width, ptB.y * canvas.height);
                ctx.stroke();
            }
        });

        // Draw each joint as a small circle
        ctx.fillStyle = "#00bcd4";
        interpolatedPoints.forEach((pt) => {
            if (pt) {
                ctx.beginPath();
                ctx.arc(pt.x * canvas.width, pt.y * canvas.height, 3, 0, 2 * Math.PI);
                ctx.fill();
            }
        });
    }, [currentTime, frames, ex]);

    // Play/Pause video whenever isPlaying or videosReady changes
    useEffect(() => {
        if (videosReady) {
            if (isPlaying) {
                videoRef.current?.play();
            } else {
                videoRef.current?.pause();
            }
        }
    }, [isPlaying, videosReady]);

    // Sync React state currentTime → video.currentTime, but only if out of tolerance
    useEffect(() => {
        if (!videosReady) return;
        const video = videoRef.current;
        if (!video) return;

        if (Math.abs(video.currentTime - currentTime) > 0.1) {
            video.currentTime = currentTime;
        }

        // On first sync, capture offset "ex"
        if (ex === 0 && video.currentTime > 0) {
            setEx(video.currentTime);
        }
    }, [currentTime, videosReady, ex]);

    // Update currentTime when the user seeks via the video element (if controls are enabled)
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;
        const onSeeked = () => {
            setCurrentTime(video.currentTime);
        };
        video.addEventListener("seeked", onSeeked);
        return () => {
            video.removeEventListener("seeked", onSeeked);
        };
    }, [videoRef]);

    // When video metadata is loaded, set times and mark ready
    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            const dur = videoRef.current.duration || 0;
            setStartTime(0);
            setEndTime(dur);
            setVideosReady(true);
        }
    };

    // Update currentTime on timeupdate events
    const handleTimeUpdate = () => {
        if (!videosReady) return;
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
        }
    };

    // Handle manual seeking via slider
    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const time = Number(e.target.value);
        if (videoRef.current) {
            videoRef.current.currentTime = time;
        }
        setCurrentTime(time);
    };

    return (
        <motion.div
            className="lab-container"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, type: "spring" }}
        >

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
                    loop={false}
                    onEnded={() => setIsPlaying(false)}
                    className="lab-video"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.5 }}
                    whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #1976d2" }}
                    width={400}
                    height={300}
                />
                <motion.canvas
                    ref={canvasRef}
                    className="lab-video"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.5 }}
                    whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #1976d2" }}
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
                    min={startTime + ex}
                    max={endTime + ex}
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
                    {formatTime(currentTime)} / {formatTime(endTime + ex)}
                </motion.span>
            </motion.div>
            {status && (
            <div style={{position: "fixed", left: "10px", top: "10px", width: "calc(100% - 20px)", height: "100px", display: "flex", justifyContent: "center", alignItems: "center"}}>
                <button onClick={() => setStatus(!status)} style={{border: "none", background: "none", color: "#00bcd4", cursor: "pointer", right: "10px", boxShadow: "0 2px 26px rgba(0, 92, 212, 0.618)", backgroundColor: "transparent"}}>x</button>
                <StatusPage/>
            </div>)}
            <div>
                <motion.button
                    className="back-button"
                    onClick={() => navigate("/")}
                    whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                    whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                    style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "5rem", boxShadow: "0 2px 0px #00bcd4" }}
                >
                    Back
                </motion.button>
                <motion.button
                    className="back-button"
                    onClick={() => window.location.reload()}
                    whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                    whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                    style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "5rem", boxShadow: "0 2px 0px #00bcd4" }}
                >
                    Reload
                </motion.button>
                <motion.button
                    className="back-button"
                    onClick={() => setStatus(!status)}
                    whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                    whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                    style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "5rem", boxShadow: "0 2px 0px #00bcd4" }}
                >
                    Status
                </motion.button>
            </div>
        </motion.div>
    );
};
