import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import React from "react";

import { Lab } from "./pages/Lab";
import VideoUpload from "./pages/VideoUpload";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<VideoUpload />} />
        <Route path="/lab" element={<Lab />} />
      </Routes>
    </Router>
  );
}

export default App;
