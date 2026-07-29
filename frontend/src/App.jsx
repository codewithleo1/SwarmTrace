import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TraceList from './pages/TraceList'
import TraceDetail from './pages/TraceDetail'
import TraceDiff from './pages/TraceDiff'
import Login from './pages/Login'
import Settings from './pages/Settings'

function PrivateRoute({ children }) {
  const token = localStorage.getItem('swt_token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<PrivateRoute><TraceList /></PrivateRoute>} />
        <Route path="/trace/:traceId" element={<PrivateRoute><TraceDetail /></PrivateRoute>} />
        <Route path="/diff/:originalId/:forkedId" element={<PrivateRoute><TraceDiff /></PrivateRoute>} />
        <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
      </Routes>
    </BrowserRouter>
  )
}