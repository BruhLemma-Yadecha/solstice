import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

type Job = {
    id: string;
    status: string;
    created_at: string;
    pose_data_file?: string | null;
    input_video: {
        id: string;
        file: string;
    };
};

const statusColors: Record<string, string> = {
    UPLOADED: "#bdbdbd",
    PROCESSING: "#ff9800",
    COMPLETED: "#4caf50",
    FAILED: "#f44336",
};

const JobList: React.FC = () => {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/video/jobs/")
            .then(res => res.json())
            .then(data => {
                setJobs(data);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    return (
        <motion.div
            className="joblist-container"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, type: "spring" }}
            style={{ maxWidth: 1200, margin: "2rem auto", background: "#181c24", borderRadius: 16, padding: 32 }}
        >
            <div style={{ display: "flex", gap: "2rem", justifyContent: "space-between", alignItems: "center", margin: "1.5rem 0" }}>
                <h2 style={{ color: "#00bcd4", margin: 0 }}>Job List</h2>
                <div style={{ display: "flex", gap: "1rem" }}>
                    <LabNavButtons />
                </div>
            </div>
            {loading ? (
                <div>Loading...</div>
            ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", color: "#fff" }}>
                    <thead>
                        <tr>
                            <th style={{ textAlign: "left", padding: 8 }}>Job ID</th>
                            <th style={{ textAlign: "left", padding: 8 }}>Video</th>
                            <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                            <th style={{ textAlign: "left", padding: 8 }}>Created</th>
                            <th style={{ textAlign: "left", padding: 8 }}>CSV</th>
                        </tr>
                    </thead>
                    <tbody>
                        {jobs.map(job => (
                            <tr key={job.id} style={{ borderBottom: "1px solid #222" }}>
                                <td style={{ padding: 8, fontSize: 13 }}>{job.id}</td>
                                <td style={{ padding: 8, fontSize: 13 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                        <video
                                            src={job.input_video.file}
                                            width={120}
                                            height={72}
                                            muted
                                            controls={false}
                                            playsInline
                                            style={{ borderRadius: 8, background: "#111", objectFit: "cover", border: "1px solid #222" }}
                                            preload="metadata"
                                            ref={el => {
                                                if (el) {
                                                    el.currentTime = 0.5;
                                                    el.pause();
                                                    // Play a short preview (0.5s to 2.5s), then pause
                                                    el.onmouseenter = () => {
                                                        el.currentTime = 0.5;
                                                        el.play();
                                                        const stop = () => {
                                                            if (el.currentTime >= 7.5) {
                                                                el.pause();
                                                                el.currentTime = 0.5;
                                                                el.removeEventListener("timeupdate", stop);
                                                            }
                                                        };
                                                        el.addEventListener("timeupdate", stop);
                                                        el.onmouseleave = () => {
                                                            el.pause();
                                                            el.currentTime = 0.5;
                                                            el.removeEventListener("timeupdate", stop);
                                                        };
                                                    };
                                                }
                                            }}
                                        />
                                        <a href={job.input_video.file} target="_blank" rel="noopener noreferrer" style={{ color: "#00bcd4" }}>
                                            Video {job.input_video.id}
                                        </a>
                                    </div>
                                </td>
                                <td style={{ padding: 8 }}>
                                    <span style={{
                                        color: statusColors[job.status] || "#fff",
                                        fontWeight: 600,
                                        letterSpacing: 1,
                                    }}>
                                        {job.status}
                                    </span>
                                </td>
                                <td style={{ padding: 8, fontSize: 13 }}>{new Date(job.created_at).toLocaleString()}</td>
                                <td style={{ padding: 8, display: "flex", alignItems: "center", gap: 8 }}>
                                    {job.pose_data_file ? (
                                        <a href={job.pose_data_file} target="_blank" rel="noopener noreferrer" style={{ color: "#4caf50" }}>
                                            Download CSV
                                        </a>
                                    ) : (
                                        <span style={{ color: "#bdbdbd" }}>Not ready</span>
                                    )}
                                    <OpenInLabButton job={job} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </motion.div>
    );
};

const OpenInLabButton: React.FC<{ job: Job }> = ({ job }) => {
    const navigate = useNavigate();
    const handleOpen = () => {
        localStorage.setItem("video_job_id", job.id);
        localStorage.setItem("video_id", job.input_video.id);
        localStorage.setItem("video_url", job.input_video.file);
        if (job.pose_data_file) {
            localStorage.setItem("csv_url", job.pose_data_file);
        } else {
            localStorage.removeItem("csv_url");
        }
        navigate("/lab");
    };
    return (
        <button
            onClick={handleOpen}
            style={{
                background: "#00bcd4",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                padding: "4px 10px",
                cursor: "pointer",
                fontSize: 12,
                marginLeft: 4,
                opacity: job.pose_data_file ? 1 : 0.6,
                width: 150,
                textAlign: "center",
            }}
            disabled={!job.pose_data_file}
            title={job.pose_data_file ? "Open in Lab" : "CSV not ready"}
        >
            <h3>{job.pose_data_file ? "Open in Lab" : "CSV not ready"}</h3>
        </button>
    );
};

const LabNavButtons: React.FC = () => {
    const navigate = useNavigate();
    return (
        <>
           <motion.button
                className="back-button"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", boxShadow: "0 2px 0px #00bcd4", padding:"none" }}
            >
                Back
            </motion.button>
            <motion.button
                className="back-button"
                onClick={() => navigate("/lab")}
                whileHover={{ scale: 1.05, boxShadow: "8px 8px #00bcd4", color: "#fff" }}
                whileTap={{ scale: 0.95, boxShadow: "4px 3px #00bcd4" }}
                style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", boxShadow: "0 2px 0px #00bcd4" }}
            >
                Lab
            </motion.button>
        </>
    );
};

export default JobList;
