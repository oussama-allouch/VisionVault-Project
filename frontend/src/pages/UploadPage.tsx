import { useState, useEffect, useCallback } from 'react'
import { Upload, X, Image, CheckCircle, AlertCircle } from 'lucide-react'
import { imageService } from '../services/imageService'
import { categoryService } from '../services/categoryService'
import type { Category } from '../types'
import toast from 'react-hot-toast'

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([])
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [categories, setCategories] = useState<Category[]>([])
  const [uploading, setUploading] = useState(false)
  const [results, setResults] = useState<{ name: string; ok: boolean; msg?: string }[]>([])
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => { categoryService.list().then(setCategories).catch(() => {}) }, [])

  const flatCats: Category[] = []
  const flatten = (cats: Category[], depth = 0) => { cats.forEach(c => { flatCats.push({ ...c, name: '  '.repeat(depth) + c.name }); if (c.children) flatten(c.children, depth + 1) }) }
  flatten(categories)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const dropped = Array.from(e.dataTransfer.files).filter(f => /\.(jpe?g|png|webp|bmp|gif|tiff)$/i.test(f.name))
    setFiles(prev => [...prev, ...dropped])
  }, [])

  const handleSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFiles(prev => [...prev, ...Array.from(e.target.files!)])
  }

  const removeFile = (i: number) => setFiles(f => f.filter((_, idx) => idx !== i))

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true); setResults([])
    let res: typeof results
    try {
      if (files.length === 1) {
        await imageService.upload(files[0], categoryId)
        res = [{ name: files[0].name, ok: true }]
      } else {
        const data = await imageService.bulkUpload(files, categoryId)
        res = data.uploads.map(item => ({
          name: item.filename, ok: item.status === 201, msg: item.result.message,
        }))
      }
    } catch {
      res = files.map(file => ({ name: file.name, ok: false, msg: 'Échec de l’envoi. Vérifiez le format et la limite de 16 Mio.' }))
    }
    setResults(res); setUploading(false)
    const ok = res.filter(r => r.ok).length
    if (ok > 0) toast.success(`${ok} image(s) téléversée(s) avec succès.`)
    setFiles(files.filter((_, i) => !res[i]?.ok))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Téléverser des images</h1>

      {/* Drag & Drop */}
      <div onDragOver={e => { e.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-12 text-center transition-colors ${dragOver ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950' : 'border-gray-300 dark:border-gray-700 hover:border-indigo-400'}`}>
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-700 dark:text-gray-300">Glissez-déposez vos images ici</p>
        <p className="text-sm text-gray-400 mt-1">ou</p>
        <label className="inline-block mt-4 px-6 py-2.5 bg-indigo-600 text-white rounded-lg cursor-pointer hover:bg-indigo-700 transition text-sm font-medium">
          Parcourir les fichiers
          <input type="file" multiple accept="image/*" onChange={handleSelect} className="hidden" />
        </label>
        <p className="text-xs text-gray-400 mt-3">Formats acceptés : JPEG, PNG, WebP, BMP, GIF, TIFF</p>
      </div>

      {/* Category + Upload */}
      {files.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 space-y-4">
          <div className="flex items-center gap-3">
            <select aria-label="Catégorie de destination" value={categoryId ?? ''} onChange={e => setCategoryId(e.target.value ? Number(e.target.value) : undefined)}
              className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
              <option value="">Pas de catégorie</option>
              {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button onClick={handleUpload} disabled={uploading}
              className="px-6 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2">
              {uploading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Upload className="w-4 h-4" />}
              {uploading ? 'Envoi en cours...' : `Téléverser ${files.length} fichier(s)`}
            </button>
          </div>

          {/* File List */}
          <div className="space-y-2 max-h-64 overflow-auto">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-800">
                <Image className="w-5 h-5 text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{f.name}</span>
                <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(0)} Ko</span>
                <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500"><X className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 space-y-2">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Résultats</h3>
          {results.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              {r.ok ? <CheckCircle className="w-4 h-4 text-green-500" /> : <AlertCircle className="w-4 h-4 text-red-500" />}
              <span className={r.ok ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}>{r.name}</span>
              {r.msg && <span className="text-gray-400">— {r.msg}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
