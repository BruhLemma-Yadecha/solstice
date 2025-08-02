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
    const [normCsvUrl, setNormCsvUrl] = useState<string>("");
    const [videoId, setVideoId] = useState<string>("");
    const [frames, setFrames] = useState<FramePoints>({});
    const [normFrames, setNormFrames] = useState<FramePoints>({});
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [ex, setEx] = useState(0);
    const [videosReady, setVideosReady] = useState(false);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(0);
    const [status, setStatus] = useState(false);
    const [csvReloadKey, setCsvReloadKey] = useState(0);
    const [contentStartDetected, setContentStartDetected] = useState(false);

    const navigate = useNavigate();
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const canvasRef2 = useRef<HTMLCanvasElement>(null);

    // Use WebSocket for real-time updates instead of polling
    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout;
        let cancelled = false;

        const jobId = localStorage.getItem("video_job_id");

        const connectWebSocket = () => {
            try {
                ws = new WebSocket('ws://127.0.0.1:8001/ws/latest/');
                
                ws.onopen = () => {
                    console.log('WebSocket connected to latest data');
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        
                        // Check if this is for our specific job or general latest
                        if (!jobId || !data.job_id || data.job_id === jobId) {
                            if (data.video1 && data.csv_url && !cancelled) {
                                setVideoUrl(data.video1);
                                setCsvUrl(data.csv_url);
                                setNormCsvUrl(data.norm_csv_url);
                                if (data.video_id) setVideoId(data.video_id);
                            }
                        }
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                ws.onclose = () => {
                    console.log('WebSocket connection closed');
                    if (!cancelled) {
                        // Reconnect after 3 seconds
                        reconnectTimeout = setTimeout(connectWebSocket, 3000);
                    }
                };

                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            } catch (error) {
                console.error('Error creating WebSocket:', error);
                if (!cancelled) {
                    reconnectTimeout = setTimeout(connectWebSocket, 3000);
                }
            }
        };

        // Initial fallback fetch for immediate data
        const initialFetch = async () => {
            try {
                let url = "http://127.0.0.1:8008/video/latest/";
                if (jobId) {
                    url += `?job_id=${jobId}`;
                }
                const res = await fetch(url);
                const data = await res.json();
                if (data.video1 && data.csv_url && !cancelled) {
                    setVideoUrl(data.video1);
                    setCsvUrl(data.csv_url);
                    setNormCsvUrl(data.norm_csv_url);
                    if (data.video_id) setVideoId(data.video_id);
                }
            } catch (error) {
                console.error('Error fetching initial data:', error);
            }
        };

        // Start with initial fetch, then connect WebSocket
        initialFetch();
        connectWebSocket();

        return () => {
            cancelled = true;
            if (ws) {
                ws.close();
            }
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
            }
        };
    }, [csvReloadKey]);

    useEffect(() => {
        if (!normCsvUrl) return;
        fetch(normCsvUrl)
            .then(res => res.text())
            .then(csvText => {
                Papa.parse(csvText, {
                    header: true,
                    complete: (results: Papa.ParseResult<any>) => {
                        const grouped: FramePoints = {};
                        (results.data as any[]).forEach((row: any) => {
                            const frameIdx = parseInt(row.frame, 10);
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
                        setNormFrames(grouped);
                    }
                });
            })
            .catch(err => {
                console.error("Error fetching or parsing norm CSV:", err);
            });
    }, [normCsvUrl]);

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

    // Draw stick figure on canvas for the current video time
    useEffect(() => {
        if (!canvasRef.current || !videoRef.current) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const fps = 30;
        
        // Auto-detect content start: use the minimum frame number in CSV as reference
        const frameNumbers = Object.keys(frames).map(Number).filter(n => !isNaN(n));
        const minFrame = frameNumbers.length > 0 ? Math.min(...frameNumbers) : 0;
        const csvStartTime = minFrame / fps; // Time in video where CSV frame 0 corresponds
        
        // If we have CSV data, use it to calculate the offset
        let videoStartOffset = 0;
        if (frameNumbers.length > 0 && !contentStartDetected && videoRef.current.currentTime > 0) {
            // Auto-detect: assume current video time corresponds to the first available frame
            videoStartOffset = videoRef.current.currentTime - csvStartTime;
            setStartTime(videoStartOffset);
            setContentStartDetected(true);
        } else if (contentStartDetected) {
            videoStartOffset = startTime;
        }
        
        // Calculate relative time: how far into the CSV data are we?
        const relativeTime = Math.max(0, currentTime - videoStartOffset);
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
            [0, 1], [1, 2], [2, 3], [3, 7],
            [0, 4], [4, 5], [5, 6], [6, 8],
            [9, 10], [11, 12], [11, 13], [13, 15],
            [12, 14], [14, 16], [11, 23], [12, 24],
            [23, 25], [25, 27], [24, 26], [26, 28],
            [27, 29], [29, 31], [28, 30], [30, 32],
        ];

        ctx.strokeStyle = "#00bcd4";
        ctx.lineWidth = 2;

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

        ctx.fillStyle = "#00bcd4";
        interpolatedPoints.forEach((pt) => {
            if (pt) {
                ctx.beginPath();
                ctx.arc(pt.x * canvas.width, pt.y * canvas.height, 3, 0, 2 * Math.PI);
                ctx.fill();
            }
        });
    }, [currentTime, frames, ex]);

    // Draw normalized stick figure on second canvas
    useEffect(() => {
        if (!canvasRef2.current || !videoRef.current) return;
        if (!normCsvUrl) return;
        const canvas = canvasRef2.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const fps = 30;
        
        // Use the same synchronization logic as the first canvas
        const frameNumbers = Object.keys(normFrames).map(Number).filter(n => !isNaN(n));
        const minFrame = frameNumbers.length > 0 ? Math.min(...frameNumbers) : 0;
        const csvStartTime = minFrame / fps;
        
        let videoStartOffset = 0;
        if (frameNumbers.length > 0 && !contentStartDetected && videoRef.current.currentTime > 0) {
            videoStartOffset = videoRef.current.currentTime - csvStartTime;
        } else if (contentStartDetected) {
            videoStartOffset = startTime;
        }
        
        const relativeTime = Math.max(0, currentTime - videoStartOffset);
        const currentFrame = relativeTime * fps;
        const prevIdx = Math.floor(currentFrame);
        const nextIdx = Math.ceil(currentFrame);
        const alpha = currentFrame - prevIdx;

        // Use frames from normalized CSV
        const prevPoints = normFrames[prevIdx] || new Array(33).fill(null);
        const nextPoints = normFrames[nextIdx] || new Array(33).fill(null);

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

        // Same skeleton as above
        const skeleton: [number, number][] = [
            [0, 1], [1, 2], [2, 3], [3, 7],
            [0, 4], [4, 5], [5, 6], [6, 8],
            [9, 10], [11, 12], [11, 13], [13, 15],
            [12, 14], [14, 16], [11, 23], [12, 24],
            [23, 25], [25, 27], [24, 26], [26, 28],
            [27, 29], [29, 31], [28, 30], [30, 32],
        ];

        // Scale down the normalized pose to fit better in view
        const scale = 0.4; // Scale factor to make pose smaller
        const offsetX = canvas.width * (1 - scale) / 2; // Center horizontally
        const offsetY = canvas.height * (1 - scale) / 2; // Center vertically

        ctx.strokeStyle = "#ff9800";
        ctx.lineWidth = 2;

        skeleton.forEach(([a, b]) => {
            const ptA = interpolatedPoints[a];
            const ptB = interpolatedPoints[b];
            if (ptA && ptB) {
                ctx.beginPath();
                ctx.moveTo(ptA.x * canvas.width * scale + offsetX, ptA.y * canvas.height * scale + offsetY);
                ctx.lineTo(ptB.x * canvas.width * scale + offsetX, ptB.y * canvas.height * scale + offsetY);
                ctx.stroke();
            }
        });

        ctx.fillStyle = "#ff9800";
        interpolatedPoints.forEach((pt) => {
            if (pt) {
                ctx.beginPath();
                ctx.arc(pt.x * canvas.width * scale + offsetX, pt.y * canvas.height * scale + offsetY, 3, 0, 2 * Math.PI);
                ctx.fill();
            }
        });
    }, [currentTime, normFrames, ex, normCsvUrl]);

    // Play/Pause video when isPlaying or videosReady changes
    useEffect(() => {
        if (!videoRef.current) return;
        if (videosReady) {
            if (isPlaying) {
                videoRef.current.play();
            } else {
                videoRef.current.pause();
            }
        }
    }, [isPlaying, videosReady]);

    // Sync currentTime to video element (if out of sync)
    useEffect(() => {
        if (!videosReady || !videoRef.current) return;
        if (Math.abs(videoRef.current.currentTime - currentTime) > 0.1) {
            videoRef.current.currentTime = currentTime;
        }
    }, [currentTime, videosReady]);

    // Set ex offset on first play
    useEffect(() => {
        if (!videosReady || !videoRef.current) return;
        if (ex === 0 && videoRef.current.currentTime > 0) {
            setEx(videoRef.current.currentTime);
        }
    }, [videosReady, ex]);

    // Listen for user seeking via video controls (if enabled)
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;
        const onSeeked = () => setCurrentTime(video.currentTime);
        video.addEventListener("seeked", onSeeked);
        return () => video.removeEventListener("seeked", onSeeked);
    }, []);

    // When video metadata is loaded, set times and mark ready
    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            const dur = videoRef.current.duration || 0;
            setStartTime(0);
            setEndTime(dur);
            setVideosReady(true);
            setCurrentTime(0);
            setEx(0);
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

    // Delete video or job handler
    const handleDeleteVideo = () => {
        if (!videoId) {
            alert("No video ID found.");
            return;
        }
        const jobId = localStorage.getItem("video_job_id");
        let url = `http://127.0.0.1:8008/video/videos/${videoId}/delete/`;
        if (jobId) {
            url += `?job_id=${jobId}`;
        }
        fetch(url, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json",
            },
        })
            .then((response) => {
                if (response.ok) {
                    alert("Deleted successfully");
                    navigate("/");
                } else {
                    alert("Error deleting");
                }
            })
            .catch((error) => {
                alert("Error deleting: " + error);
            });
    };

    // Reload CSV handler
    const handleReloadCSV = () => {
        if (!videoId) {
            alert("No video ID found.");
            return;
        }
        const jobId = localStorage.getItem("video_job_id");
        let url = `http://127.0.0.1:8008/video/videos/${videoId}/regenerate-csv/`;
        if (jobId) {
            url += `?job_id=${jobId}`;
        }
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
        })
            .then((response) => {
                if (response.ok) {
                    alert("CSV regeneration started. It may take a few seconds.");
                    setCsvReloadKey(k => k + 1);
                } else {
                    alert("Error regenerating CSV");
                }
            })
            .catch((error) => {
                alert("Error regenerating CSV: " + error);
            });
    };

    // Manual content start time setter
    const setContentStartTime = () => {
        if (videoRef.current) {
            const currentVideoTime = videoRef.current.currentTime;
            setStartTime(currentVideoTime);
            setContentStartDetected(true);
            console.log(`Content start manually set to ${currentVideoTime.toFixed(2)}s`);
            alert(`Content start time set to ${Math.floor(currentVideoTime / 60)}:${(currentVideoTime % 60).toFixed(0).padStart(2, '0')}`);
        }
    };

    // Reset content start detection
    const resetContentStart = () => {
        setStartTime(0);
        setContentStartDetected(false);
        console.log('Content start reset');
        alert('Content start time reset - will auto-detect on next playback');
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
                style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.5rem", justifyContent: "center" }}
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
                    whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #00bcd4" }}
                    width={300}
                    height={225}
                />
                <div style={{ display: "flex", flexDirection: "row", gap: "2rem", justifyContent: "center" }}>
                    <motion.canvas
                        ref={canvasRef}
                        className="lab-video"
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4, duration: 0.5 }}
                        whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #00bcd4" }}
                        width={300}
                        height={225}
                        style={{ background: "#222", borderRadius: "1rem" }}
                    />
                    {/* Normalized CSV canvas */}
                    <motion.canvas
                        ref={canvasRef2}
                        className="lab-video"
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4, duration: 0.5 }}
                        whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #00bcd4" }}
                        width={300}
                        height={225}
                        style={{ background: "#222", borderRadius: "1rem" }}
                    />
                </div>
            </motion.div>
            <motion.div
                className="lab-controls"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.5 }}
            >
                <motion.button
                    onClick={() => setIsPlaying(!isPlaying)}
                    whileHover={{ cursor: videosReady ? "pointer" : "not-allowed", backgroundColor: "#00bcd400", outline: "none", border: "2px solid #00bcd4", color: "#00bcd4", boxShadow: "none" }}
                    whileFocus={{ cursor: videosReady ? "pointer" : "not-allowed", border: "2px solid #00bcd4", outline: "none" }}
                    whileTap={{ scale: 0.96 }}
                    disabled={!videosReady}
                >
                    {isPlaying ? "Pause" : "Play"}
                </motion.button>
                <motion.input
                    type="range"
                    min={startTime}
                    max={startTime+endTime}
                    value={currentTime}
                    onChange={handleSeek}
                    step={0.01}
                    disabled={!videosReady}
                    whileFocus={{ scale: 1.03 }}
                    style={{
                        width: "320px",
                        accentColor: "#00bcd4",
                        background: "linear-gradient(90deg, #00bcd4 0%, #2196f3 100%)",
                        borderRadius: "8px",
                        outline: "none",
                        margin: "0 1.5rem",
                        cursor: videosReady ? "pointer" : "not-allowed",
                        opacity: videosReady ? 1 : 0.5,
                        transition: "box-shadow 0.2s, background 0.2s"
                    }}
                />
                <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                >
                    {formatTime(currentTime)} / {formatTime(startTime+endTime)}
                </motion.span>
            </motion.div>
            {status && (
                <div style={{ position: "fixed", left: "10px", top: "10px", width: "calc(100% - 20px)", height: "100px", display: "flex", justifyContent: "center", alignItems: "center" }}>
                    <button onClick={() => setStatus(!status)} style={{ border: "none", background: "none", color: "#00bcd4", cursor: "pointer", right: "10px", boxShadow: "0 2px 26px rgba(0, 92, 212, 0.618)", backgroundColor: "transparent" }}>x</button>
                    <StatusPage />
                </div>
            )}
            <motion.div
                className="lab-button-controls"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6, duration: 0.5 }}
                style={{ 
                    display: "flex", 
                    flexDirection: "column", 
                    gap: "1.5rem", 
                    alignItems: "center", 
                    margin: "2rem 0",
                    maxWidth: "900px",
                    marginLeft: "auto",
                    marginRight: "auto"
                }}
            >
                {/* Synchronization Controls */}
                <div style={{ 
                    display: "flex", 
                    gap: "1rem", 
                    alignItems: "center",
                    padding: "1rem",
                    backgroundColor: "rgba(255, 152, 0, 0.1)",
                    borderRadius: "12px",
                    border: "1px solid rgba(255, 152, 0, 0.3)"
                }}>
                    <span style={{ color: "#ff9800", fontWeight: "600", fontSize: "0.9rem" }}>Timeline Sync:</span>
                    <motion.button
                        className="back-button"
                        onClick={setContentStartTime}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #ff9800", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #ff9800" }}
                        style={{ 
                            color: "#ff9800", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #ff9800",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                        title="Set current video time as CSV start time"
                    >
                        Sync Start
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={resetContentStart}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #f44336", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #f44336" }}
                        style={{ 
                            color: "#f44336", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #f44336",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                        title="Reset sync and auto-detect on next playback"
                    >
                        Reset Sync
                    </motion.button>
                </div>

                {/* Data Controls */}
                <div style={{ 
                    display: "flex", 
                    gap: "1rem", 
                    alignItems: "center",
                    padding: "1rem",
                    backgroundColor: "rgba(0, 188, 212, 0.1)",
                    borderRadius: "12px",
                    border: "1px solid rgba(0, 188, 212, 0.3)"
                }}>
                    <span style={{ color: "#00bcd4", fontWeight: "600", fontSize: "0.9rem" }}>Data Controls:</span>
                    <motion.button
                        className="back-button"
                        onClick={handleReloadCSV}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #00bcd4", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #00bcd4" }}
                        style={{ 
                            color: "#00bcd4", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #00bcd4",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Reload CSV
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={handleDeleteVideo}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #f44336", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #f44336" }}
                        style={{ 
                            color: "#f44336", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #f44336",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Delete Video
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={() => setStatus(!status)}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #00bcd4", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #00bcd4" }}
                        style={{ 
                            color: "#00bcd4", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #00bcd4",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Status
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={() => window.location.reload()}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #9e9e9e", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #9e9e9e" }}
                        style={{ 
                            color: "#9e9e9e", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #9e9e9e",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Reload Page
                    </motion.button>
                </div>

                {/* Navigation Controls */}
                <div style={{ 
                    display: "flex", 
                    gap: "1rem", 
                    alignItems: "center",
                    padding: "1rem",
                    backgroundColor: "rgba(0, 188, 212, 0.1)",
                    borderRadius: "12px",
                    border: "1px solid rgba(0, 188, 212, 0.3)"
                }}>
                    <span style={{ color: "#00bcd4", fontWeight: "600", fontSize: "0.9rem" }}>Navigation:</span>
                    <motion.button
                        className="back-button"
                        onClick={() => navigate("/")}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #00bcd4", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #00bcd4" }}
                        style={{ 
                            color: "#00bcd4", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #00bcd4",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Home
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={() => navigate("/videos")}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #00bcd4", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #00bcd4" }}
                        style={{ 
                            color: "#00bcd4", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #00bcd4",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Videos
                    </motion.button>
                    <motion.button
                        className="back-button"
                        onClick={() => navigate("/jobs")}
                        whileHover={{ scale: 1.05, boxShadow: "6px 6px #00bcd4", color: "#fff" }}
                        whileTap={{ scale: 0.95, boxShadow: "3px 3px #00bcd4" }}
                        style={{ 
                            color: "#00bcd4", 
                            backgroundColor: "transparent", 
                            border: "none", 
                            cursor: "pointer", 
                            boxShadow: "0 2px 0px #00bcd4",
                            padding: "0.5rem 1rem",
                            borderRadius: "8px"
                        }}
                    >
                        Jobs
                    </motion.button>
                </div>
            </motion.div>
        </motion.div>
    );
};
