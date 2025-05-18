import { useNavigate, Link } from "react-router-dom";
import React, { useState } from "react";
import { motion } from "framer-motion";
import VideoUpload from "./VideoUpload";
import { Lab } from "./Lab";
import "./Home.css";

const Home = () => {
  const [isUFile, setisUFile] = useState(true);

  return (
    <motion.div
      className="home-container"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, type: "spring" }}
    >
      <motion.div
        className="home-header"
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5, type: "spring" }}
        whileHover={{ scale: 1.03, boxShadow: "0 4px 24px #00bcd4" }}
      >
        <p>Home</p>
      </motion.div>
      <motion.div
        className="home-content"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        {isUFile ? (
          <VideoUpload/>
        ) : (
          <Lab />
        )}
      </motion.div>
    </motion.div>
  );
};

export default Home;