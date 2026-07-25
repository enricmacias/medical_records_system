import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RecordPage from './pages/RecordPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="app-header">
          <Link to="/" className="brand">
            VetRecords
          </Link>
          <p className="tagline">PDF medical records, structured for review</p>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/records/:id" element={<RecordPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
