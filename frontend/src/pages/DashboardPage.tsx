import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Image, FolderOpen, Upload, Search, Database, ArrowRight } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { analyticsService } from '../services/analyticsService'
import type { AnalyticsOverview } from '../types'

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#818cf8', '#6d28d9', '#7c3aed', '#4f46e5', '#4338ca', '#3730a3',
  '#a855f7', '#9333ea', '#7e22ce', '#6b21a8', '#581c87', '#312e81', '#5b21b6', '#4c1d95', '#e879f9', '#d946ef']

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsService.overview().then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>

  const stats = [
    { label: 'Images indexées', value: data?.total_images || 0, icon: Image, color: 'from-indigo-500 to-indigo-600' },
    { label: 'Catégories', value: data?.categories || 0, icon: FolderOpen, color: 'from-violet-500 to-violet-600' },
    { label: 'Uploads utilisateur', value: data?.user_uploads || 0, icon: Upload, color: 'from-purple-500 to-purple-600' },
    { label: 'Recherches effectuées', value: data?.searches || 0, icon: Search, color: 'from-fuchsia-500 to-fuchsia-600' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Tableau de bord</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Vue d'ensemble de votre galerie VisionVault</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{value.toLocaleString()}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Index Status + Category Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Index Status */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-500" /> État de l'index CBIR
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Images indexées</span>
              <span className="font-medium text-gray-900 dark:text-white">{data?.index_status.indexed} / {data?.index_status.total}</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
              <div className="bg-indigo-600 h-2.5 rounded-full transition-all" style={{ width: `${data?.index_status.total ? (data.index_status.indexed / data.index_status.total * 100) : 0}%` }} />
            </div>
          </div>
        </div>

        {/* Category Distribution */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Répartition par catégorie</h2>
          {data?.category_distribution && data.category_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={data.category_distribution} dataKey="image_count" nameKey="category_name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false} fontSize={10}>
                  {data.category_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-sm">Aucune donnée. Importez le dataset GHIM-10K.</p>}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { to: '/gallery', label: 'Galerie d\'images', desc: 'Parcourir et gérer vos images', icon: Image },
          { to: '/upload', label: 'Téléverser des images', desc: 'Ajouter de nouvelles images', icon: Upload },
          { to: '/search', label: 'Recherche CBIR', desc: 'Recherche par similarité visuelle', icon: Search },
        ].map(({ to, label, desc, icon: Icon }) => (
          <Link key={to} to={to} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition-all group">
            <Icon className="w-8 h-8 text-indigo-500 mb-3" />
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              {label} <ArrowRight className="w-4 h-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
