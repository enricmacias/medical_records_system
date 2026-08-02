import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import LanguageToggle from './components/LanguageToggle'
import { LanguageProvider, useLanguage } from './i18n/LanguageContext'
import HomePage from './pages/HomePage'
import RecordPage from './pages/RecordPage'
import './App.css'

function AppHeader() {
  const { t } = useLanguage()

  return (
    <header className="app-header">
      <div className="app-header-main">
        <Link to="/" className="brand">VetRecords</Link>
        <p className="tagline">{t('app.tagline')}</p>
      </div>
      <LanguageToggle />
    </header>
  )
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <AppHeader />
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

export default function App() {
  return (
    <LanguageProvider>
      <AppRoutes />
    </LanguageProvider>
  )
}
