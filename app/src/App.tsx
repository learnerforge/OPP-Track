import { useEffect, useState } from "react";
import { Routes, Route } from "./router";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Events from "./pages/Events";

/** Route table — index and login are public; events is gated behind login. */
export default function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return (
    <Routes path={path}>
      <Route path="/" element={<Index />} />
      <Route path="/login" element={<Login />} />
      <Route path="/events" element={<Events />} />
      <Route path="*" element={<Index />} />
    </Routes>
  );
}
