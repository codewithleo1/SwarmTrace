import { BrowserRouter, Routes, Route } from 'react-router-dom'
import TraceList from './pages/TraceList'
import TraceDetail from './pages/TraceDetail'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<TraceList />} />
        <Route path="/trace/:traceId" element={<TraceDetail />} />
      </Routes>
    </BrowserRouter>
  )
}
