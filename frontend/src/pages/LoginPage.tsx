import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) { toast.error('Veuillez remplir tous les champs.'); return }
    setLoading(true)
    try {
      await login(email, password)
      toast.success('Connexion réussie !')
      navigate('/dashboard')
    } catch {
      toast.error('Email ou mot de passe invalide.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-950 via-purple-950 to-slate-950 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 mb-4">
            <Eye className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">VisionVault</h1>
          <p className="text-gray-400 mt-2">Galerie intelligente & recherche CBIR</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl p-8 space-y-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Connexion</h2>
            <p className="text-sm text-gray-500 mt-1">Accédez à votre galerie d'images</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
                placeholder="demo@visionvault.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mot de passe</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
                placeholder="••••••••" />
            </div>
          </div>

          <button type="submit" disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-medium hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 transition flex items-center justify-center gap-2">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>

          <div className="text-center">
            <p className="text-xs text-gray-400">Compte démo : demo@visionvault.com / demo2024</p>
          </div>
        </form>

        <p className="text-center text-xs text-gray-500 mt-6">Mini-projet 1 — Groupe G11 — AISD Master S3</p>
      </div>
    </div>
  )
}
