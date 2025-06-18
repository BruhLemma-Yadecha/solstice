import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

import { Lab } from "./pages/Lab";
import VideoUpload from "./pages/VideoUpload";
import StatusPage from "./pages/status";
import ListVideo from "./pages/videos"
import JobList from "./pages/JobList";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<VideoUpload />} />
        <Route path="/lab" element={<Lab />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/videos" element={<ListVideo />} />
        <Route path="/jobs" element={<JobList />} />
      </Routes>
    </Router>
  );
}

export default App;
