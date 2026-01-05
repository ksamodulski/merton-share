import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import BondEntryPage from './pages/BondEntryPage'
import PortfolioEntryPage from './pages/PortfolioEntryPage'
import CRRAPage from './pages/CRRAPage'
import MarketDataPage from './pages/MarketDataPage'
import ResultsPage from './pages/ResultsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/bonds" replace />} />
        <Route path="bonds" element={<BondEntryPage />} />
        <Route path="portfolio" element={<PortfolioEntryPage />} />
        <Route path="risk-profile" element={<CRRAPage />} />
        <Route path="market-data" element={<MarketDataPage />} />
        <Route path="results" element={<ResultsPage />} />
      </Route>
    </Routes>
  )
}

export default App
