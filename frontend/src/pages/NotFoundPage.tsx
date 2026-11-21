import { Link } from 'react-router-dom'
import { ArrowLeft, Eye } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <div className="mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 mb-6">
          <Eye className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-8xl font-black bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent mb-4">
          404
        </h1>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Page non trouvée
        </h2>
        <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
          La page que vous recherchez n'existe pas ou a été déplacée.
        </p>
      </div>
      <Link to="/dashboard"
        className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-medium hover:from-indigo-700 hover:to-violet-700 flex items-center gap-2 transition shadow-sm">
        <ArrowLeft className="w-4 h-4" /> Retour au tableau de bord
      </Link>
    </div>
  )
}
