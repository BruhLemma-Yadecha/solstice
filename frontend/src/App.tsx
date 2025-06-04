import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import React from "react";

import { Lab } from "./pages/Lab";
import VideoUpload from "./pages/VideoUpload";
import StatusPage from "./pages/status";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<VideoUpload />} />
        <Route path="/lab" element={<Lab />} />
        <Route path="/status" element={<StatusPage />} />
      </Routes>
    </Router>
  );
}

export default App;
