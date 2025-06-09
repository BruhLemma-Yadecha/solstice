import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../css/status.css"

const StatusPage = () => {
  const [status, setStatus] = useState<string>("Loading...");
  const [jobId, setJobId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const storedJobId = localStorage.getItem("video_job_id");
    setJobId(storedJobId);

    if (!storedJobId) {
      setStatus("No job ID found.");
      return;
    }

    const fetchStatus = () => {
      fetch(`http://127.0.0.1:8000/video/jobs/${storedJobId}/status/`)
        .then(res => res.json())
        .then(data => {
          setStatus(data.status || JSON.stringify(data));
        })
        .catch(() => setStatus("Error fetching status"));
    };

    fetchStatus(); // initial fetch
    const interval = setInterval(fetchStatus, 3000); // poll every 3 seconds

    return () => clearInterval(interval); // cleanup on unmount
  }, []);

  return (
    <>
        <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="status-container"
            style={{ color: "#00bcd4", marginTop: "30vh", textAlign: "center", padding: "20px", borderRadius: "8px", }}
        >
            <motion.h2
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            style={{ marginBottom: 16 }}
            >
            Processing Status
            </motion.h2>
            <motion.p
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            >
            Job ID: {jobId || "N/A"}
            </motion.p>
            <motion.p
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            >
            Status: {status}
            </motion.p>
            <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: status === "COMPLETED" ? 1 : 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            >
            <motion.div
            whileHover={{ scale: 1.08, boxShadow: "0 4px 24px #00bcd4" }}
            whileTap={{ scale: 0.96 }}
            style={{ display: "inline-block" }}
            >
            <Link to="/lab" style={{ color: "#00bcd4", textDecoration: "underline", fontWeight: 600 }}>
                Go to Lab
            </Link>
            </motion.div>
            </motion.p>
        </motion.div>
        {/* <div className="status-footer">
            <motion.button
                className="back-button"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05, boxShadow: "0 4px 24px #00bcd4", backgroundColor: "#00bcd4", color: "#fff" }}
                whileTap={{ scale: 0.95 }}
                style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "auto" }}
            >
                Back
            </motion.button>
            <motion.button
                className="back-button"
                onClick={() => navigate("/status")}
                whileHover={{ scale: 1.05, boxShadow: "0 4px 24px #00bcd4", backgroundColor: "#00bcd4", color: "#fff" }}
                whileTap={{ scale: 0.95 }}
                style={{ color: "#00bcd4", backgroundColor: "transparent", border: "none", cursor: "pointer", margin: "auto" }}
            >
                Status
            </motion.button>
        </div> */}
    </>
  );
};

export default StatusPage;