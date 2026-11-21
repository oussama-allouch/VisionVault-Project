import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Search, Filter, Trash2, Download, Grid3x3, ChevronLeft, ChevronRight, Eye, Scan, Edit } from 'lucide-react'
import { imageService } from '../services/imageService'
import { categoryService } from '../services/categoryService'
import type { ImageData, Category } from '../types'
import { formatDate, formatFileSize } from '../utils/format'
import toast from 'react-hot-toast'

export default function GalleryPage() {
  const [images, setImages] = useState<ImageData[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [viewImage, setViewImage] = useState<ImageData | null>(null)
  const perPage = 24

  const fetchImages = useCallback(async () => {
    setLoading(true)
    try {
      const data = await imageService.list({ page, per_page: perPage, category_id: categoryId, search: search || undefined, sort_by: sortBy, sort_order: sortOrder })
      setImages(data.images); setTotal(data.total); setPages(data.pages)
    } catch { toast.error('Erreur de chargement des images.') }
    finally { setLoading(false) }
  }, [page, categoryId, search, sortBy, sortOrder])

  useEffect(() => { fetchImages() }, [fetchImages])
  useEffect(() => { categoryService.list().then(setCategories).catch(() => {}) }, [])

  // Flatten categories for dropdown
  const flatCats: Category[] = []
  const flatten = (cats: Category[], depth = 0) => {
    cats.forEach(c => { flatCats.push({ ...c, name: '  '.repeat(depth) + c.name }); if (c.children) flatten(c.children, depth + 1) })
  }
  flatten(categories)

  const toggleSelect = (id: number) => {
    const s = new Set(selected)
    s.has(id) ? s.delete(id) : s.add(id)
    setSelected(s)
  }
  const selectAll = () => { selected.size === images.length ? setSelected(new Set()) : setSelected(new Set(images.map(i => i.id))) }

  const handleDelete = async (ids: number[]) => {
    if (!confirm(`Supprimer ${ids.length} image(s) ?`)) return
    try {
      await imageService.bulkDelete(ids)
      toast.success(`${ids.length} image(s) supprimée(s).`)
      setSelected(new Set())
      setViewImage(null)
      fetchImages()
    } catch (e: any) {
      toast.error(e?.response?.data?.message || 'Erreur de suppression.')
    }
  }

  const handleDownload = async (ids: number[]) => {
    try {
      const blob = await imageService.bulkDownload(ids)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = 'images.zip'; a.click()
      URL.revokeObjectURL(url)
    } catch { toast.error('Erreur de téléchargement.') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Galerie d'images</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">{total.toLocaleString()} images au total</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} placeholder="Rechercher par nom..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none" />
        </div>
        <select value={categoryId ?? ''} onChange={e => { setCategoryId(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
          <option value="">Toutes les catégories</option>
          {flatCats.map(c => <option key={c.id} value={c.id}>{c.name} ({c.image_count ?? 0})</option>)}
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
          <option value="created_at">Date</option>
          <option value="filename">Nom</option>
          <option value="file_size">Taille</option>
        </select>
        <button onClick={() => setSortOrder(o => o === 'asc' ? 'desc' : 'asc')}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-700 dark:text-gray-300">
          <Filter className="w-4 h-4 inline mr-1" />{sortOrder === 'asc' ? '↑' : '↓'}
        </button>
      </div>

      {/* Bulk Actions */}
      {selected.size > 0 && (
        <div className="bg-indigo-50 dark:bg-indigo-950 rounded-xl p-3 flex items-center gap-3">
          <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">{selected.size} sélectionnée(s)</span>
          <button onClick={() => handleDelete([...selected])} className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"><Trash2 className="w-4 h-4" /> Supprimer</button>
          <button onClick={() => handleDownload([...selected])} className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1"><Download className="w-4 h-4" /> Télécharger ZIP</button>
          <button onClick={() => setSelected(new Set())} className="text-sm text-gray-500 ml-auto">Désélectionner</button>
        </div>
      )}

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <div key={i} className="aspect-square bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />)}
        </div>
      ) : images.length === 0 ? (
        <div className="text-center py-16">
          <Grid3x3 className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-500 dark:text-gray-400">Aucune image trouvée</h3>
          <p className="text-sm text-gray-400 mt-1">Importez le dataset ou téléversez des images.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {images.map(img => (
            <div key={img.id} className={`group relative bg-white dark:bg-gray-900 rounded-xl border overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer ${selected.has(img.id) ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-gray-200 dark:border-gray-800'}`}>
              <div className="aspect-square bg-gray-100 dark:bg-gray-800" onClick={() => setViewImage(img)}>
                {img.thumbnail_url ? (
                  <img src={img.thumbnail_url} alt={img.filename} className="w-full h-full object-cover" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400"><Grid3x3 className="w-8 h-8" /></div>
                )}
              </div>
              {/* Checkbox */}
              <input type="checkbox" checked={selected.has(img.id)} onChange={() => toggleSelect(img.id)}
                className="absolute top-2 left-2 w-4 h-4 rounded border-gray-300 text-indigo-600 opacity-0 group-hover:opacity-100 checked:opacity-100 transition-opacity" />
              {/* Overlay Actions */}
              <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Link to={`/features/${img.id}`} className="p-1.5 bg-white/90 dark:bg-gray-800/90 rounded-lg hover:bg-white shadow-sm"><Eye className="w-3.5 h-3.5 text-gray-600" /></Link>
                <Link to={`/editor/${img.id}`} className="p-1.5 bg-white/90 dark:bg-gray-800/90 rounded-lg hover:bg-white shadow-sm"><Edit className="w-3.5 h-3.5 text-gray-600" /></Link>
                <Link to={`/search?query=${img.id}`} className="p-1.5 bg-white/90 dark:bg-gray-800/90 rounded-lg hover:bg-white shadow-sm"><Scan className="w-3.5 h-3.5 text-gray-600" /></Link>
              </div>
              {/* Info */}
              <div className="p-2">
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{img.filename}</p>
                {img.category_name && <span className="text-[10px] text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950 px-1.5 py-0.5 rounded mt-1 inline-block">{img.category_name}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 text-gray-700 dark:text-gray-300"><ChevronLeft className="w-5 h-5" /></button>
          <span className="text-sm text-gray-600 dark:text-gray-400">Page {page} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 text-gray-700 dark:text-gray-300"><ChevronRight className="w-5 h-5" /></button>
          <button onClick={selectAll} className="text-xs text-indigo-600 ml-4 hover:underline">{selected.size === images.length ? 'Désélectionner tout' : 'Tout sélectionner'}</button>
        </div>
      )}

      {/* Image Detail Modal */}
      {viewImage && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setViewImage(null)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="grid md:grid-cols-2">
              <div className="bg-gray-100 dark:bg-gray-800 flex items-center justify-center min-h-64">
                {viewImage.image_url ? <img src={viewImage.image_url} alt={viewImage.filename} className="max-w-full max-h-[70vh] object-contain" /> : <Grid3x3 className="w-16 h-16 text-gray-400" />}
              </div>
              <div className="p-6 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{viewImage.filename}</h3>
                <div className="space-y-2 text-sm">
                  {[
                    ['Catégorie', viewImage.category_name || '—'],
                    ['Dimensions', viewImage.width && viewImage.height ? `${viewImage.width} × ${viewImage.height}` : '—'],
                    ['Taille', formatFileSize(viewImage.file_size)],
                    ['Type', viewImage.source_type],
                    ['Date', formatDate(viewImage.created_at)],
                    ['Indexée', viewImage.is_indexed ? 'Oui' : 'Non'],
                  ].map(([label, val]) => (
                    <div key={label} className="flex justify-between"><span className="text-gray-500">{label}</span><span className="text-gray-900 dark:text-white font-medium">{val}</span></div>
                  ))}
                </div>
                <div className="flex gap-2 pt-4">
                  <Link to={`/features/${viewImage.id}`} className="flex-1 py-2 text-center rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-sm font-medium hover:bg-indigo-100">Descripteurs</Link>
                  <Link to={`/search?query=${viewImage.id}`} className="flex-1 py-2 text-center rounded-lg bg-violet-50 dark:bg-violet-950 text-violet-700 dark:text-violet-300 text-sm font-medium hover:bg-violet-100">Recherche CBIR</Link>
                  <Link to={`/editor/${viewImage.id}`} className="flex-1 py-2 text-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-200">Éditer</Link>
                </div>
                <button onClick={() => handleDelete([viewImage.id])} className="w-full py-2 text-center rounded-lg border border-red-200 text-red-600 text-sm hover:bg-red-50 transition">Supprimer</button>
                <button onClick={() => setViewImage(null)} className="w-full py-2 text-center rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition">Fermer</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
