import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import "../css/Lab.css";

// Format seconds as mm:ss
const formatTime = (seconds: number) => {
    if (!isFinite(seconds)) return "--:--";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

export const Lab = () => {
    const [videoUrls, setVideoUrls] = useState<string[]>([]);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [videosReady, setVideosReady] = useState(false);
    const [startTime, setStartTime] = useState(0);
    const [endTime, setEndTime] = useState(0);

    const videoRef1 = useRef<HTMLVideoElement>(null);
    const videoRef2 = useRef<HTMLVideoElement>(null);

    // Fetch video URLs
    useEffect(() => {
        fetch("http://127.0.0.1:8000/videos/")
            .then(res => res.json())
            .then(data => {
                const urls = [];
                if (data.video1) urls.push(data.video1);
                if (data.video2) urls.push(data.video2);
                setVideoUrls(urls);
            });
    }, []);

    // Play/Pause videos in sync
    useEffect(() => {
        if (videosReady) {
            if (isPlaying) {
                videoRef1.current?.play();
                videoRef2.current?.play();
            } else {
                videoRef1.current?.pause();
                videoRef2.current?.pause();
            }
        }
    }, [isPlaying, videosReady]);

    // Sync currentTime on state update
    useEffect(() => {
        if (!videosReady) return;
        if (videoRef1.current && Math.abs(videoRef1.current.currentTime - currentTime) > 0.1) {
            videoRef1.current.currentTime = currentTime;
        }
        if (videoRef2.current && Math.abs(videoRef2.current.currentTime - currentTime) > 0.1) {
            videoRef2.current.currentTime = currentTime;
        }
    }, [currentTime, videosReady]);

    // Handle metadata loaded
    const handleLoadedMetadata = () => {
        if (videoRef1.current && videoRef2.current) {
            const minDuration = Math.min(
                videoRef1.current.duration || 0,
                videoRef2.current.duration || 0
            );
            setDuration(minDuration);
            setStartTime(0);
            setEndTime(minDuration);
            setVideosReady(true);
        }
    };

    // Update current time when videos play
    const handleTimeUpdate = () => {
        if (!videosReady) return;
        if (videoRef1.current && videoRef2.current) {
            const t1 = videoRef1.current.currentTime;
            const t2 = videoRef2.current.currentTime;
            setCurrentTime((t1 + t2) / 2);
        }
    };

    // Handle user seek
    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const time = Number(e.target.value);
        if (videoRef1.current) videoRef1.current.currentTime = time;
        if (videoRef2.current) videoRef2.current.currentTime = time;
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
            >
                {videoUrls.map((url, idx) => (
                    <motion.video
                        key={idx}
                        ref={idx === 0 ? videoRef1 : videoRef2}
                        src={url}
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        controls={false}
                        className="lab-video"
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 + idx * 0.1, duration: 0.5 }}
                        whileHover={{ scale: 1.03, boxShadow: "0 4px 32px #1976d2" }}
                    />
                ))}
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
                    max={endTime}
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
