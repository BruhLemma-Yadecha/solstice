import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const StatusPage = () => {
  const [status, setStatus] = useState<string>("Loading...");
  const [jobId, setJobId] = useState<string | null>(null);

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
    <div style={{ color: "#00bcd4", marginTop: "30vh", textAlign: "center" }}>
      <h2>Processing Status</h2>
      <p>Job ID: {jobId || "N/A"}</p>
      <p>Status: {status}</p>
        <p>
            {status === "COMPLETED" ? (
            <Link to="/lab" style={{ color: "#00bcd4", textDecoration: "underline" }}>
                Go to Lab
            </Link>
        ) : null}
        </p>
    </div>
  );
};

export default StatusPage;