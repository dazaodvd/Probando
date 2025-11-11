import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ChatAssistant from "@/components/ChatAssistant";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatAssistant />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
