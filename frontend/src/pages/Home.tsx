import { useNavigate, Link } from "react-router-dom";
import React, { useState, useEffect } from "react";
import VideoUpload from "../other/VideoUpload";
import { Lab } from "./Lab";

const Home = () => {
  const [isUFile, setisUFile] = useState(true);

  return (
    <>
        <div>
            <p>Home</p>
        </div>
        { isUFile ? (<VideoUpload onUploadComplete={() => setisUFile(false)} />) : (<Lab />) }
    </>
  )
};

export default Home;