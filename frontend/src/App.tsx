import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import GalleryPage from './pages/GalleryPage'
import CategoriesPage from './pages/CategoriesPage'
import UploadPage from './pages/UploadPage'
import EditorPage from './pages/EditorPage'
import FeaturesPage from './pages/FeaturesPage'
import SearchPage from './pages/SearchPage'
import AnalyticsPage from './pages/AnalyticsPage'
import NotFoundPage from './pages/NotFoundPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes inside MainLayout */}
        <Route path="/" element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="gallery" element={<GalleryPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="editor/:id" element={<EditorPage />} />
          <Route path="features/:id" element={<FeaturesPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
