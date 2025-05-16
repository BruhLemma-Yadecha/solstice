import { useNavigate, Link } from "react-router-dom";
import React, { useState, useEffect } from "react";
import CameraPose from "../other/CameraPose";

const Home = () => {

  const [isUFile, setisUFile] = useState(true);

  return (
    <>
        <div>
            <p>Home</p>
        </div>
        { isUFile ? (<div>UFile is true</div>) : (<div>UFile is false</div>) }
    </>
  )
};

export default Home;