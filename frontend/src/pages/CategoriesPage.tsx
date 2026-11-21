import { useState, useEffect } from 'react'
import { FolderOpen, Plus, Edit2, Trash2, ChevronRight, ChevronDown, Image } from 'lucide-react'
import { categoryService } from '../services/categoryService'
import type { Category } from '../types'
import toast from 'react-hot-toast'

function CategoryNode({ cat, onRefresh }: { cat: Category; onRefresh: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(cat.name)

  const handleSave = async () => {
    if (!name.trim()) return
    try { await categoryService.update(cat.id, name.trim()); toast.success('Catégorie renommée.'); setEditing(false); onRefresh() }
    catch { toast.error('Erreur.') }
  }

  const handleDelete = async () => {
    if (!confirm(`Supprimer "${cat.name}" ? Les images seront dissociées.`)) return
    try { await categoryService.remove(cat.id); toast.success('Catégorie supprimée.'); onRefresh() }
    catch { toast.error('Erreur.') }
  }

  return (
    <div>
      <div className="flex items-center gap-2 group py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800">
        {cat.children && cat.children.length > 0 ? (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400">
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        ) : <span className="w-4" />}
        <FolderOpen className="w-4 h-4 text-indigo-500" />
        {editing ? (
          <input value={name} onChange={e => setName(e.target.value)} onBlur={handleSave} onKeyDown={e => e.key === 'Enter' && handleSave()}
            className="flex-1 px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white" autoFocus />
        ) : (
          <span className="flex-1 text-sm text-gray-700 dark:text-gray-300">{cat.name}</span>
        )}
        <span className="text-xs text-gray-400 flex items-center gap-1"><Image className="w-3 h-3" />{cat.image_count ?? 0}</span>
        <div className="opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
          <button onClick={() => { setEditing(true); setName(cat.name) }} className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"><Edit2 className="w-3.5 h-3.5 text-gray-500" /></button>
          <button onClick={handleDelete} className="p-1 hover:bg-red-50 dark:hover:bg-red-950 rounded"><Trash2 className="w-3.5 h-3.5 text-red-500" /></button>
        </div>
      </div>
      {expanded && cat.children && cat.children.length > 0 && (
        <div className="ml-6 border-l border-gray-200 dark:border-gray-800 pl-2">
          {cat.children.map(child => <CategoryNode key={child.id} cat={child} onRefresh={onRefresh} />)}
        </div>
      )}
    </div>
  )
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [parentId, setParentId] = useState<number | undefined>()

  const fetch = () => { setLoading(true); categoryService.list().then(setCategories).catch(() => {}).finally(() => setLoading(false)) }
  useEffect(fetch, [])

  const flatCats: Category[] = []
  const flatten = (cats: Category[], depth = 0) => {
    cats.forEach(c => { flatCats.push({ ...c, name: '  '.repeat(depth) + c.name }); if (c.children) flatten(c.children, depth + 1) })
  }
  flatten(categories)

  const handleCreate = async () => {
    if (!newName.trim()) return
    try { await categoryService.create(newName.trim(), parentId); toast.success('Catégorie créée.'); setNewName(''); fetch() }
    catch { toast.error('Erreur.') }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gestion des catégories</h1>

      {/* Create */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 flex gap-3">
        <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nouvelle catégorie..." onKeyDown={e => e.key === 'Enter' && handleCreate()}
          className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white" />
        <select value={parentId ?? ''} onChange={e => setParentId(e.target.value ? Number(e.target.value) : undefined)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
          <option value="">Racine</option>
          {flatCats.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 flex items-center gap-1"><Plus className="w-4 h-4" /> Créer</button>
      </div>

      {/* Tree */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
        {loading ? <div className="flex justify-center py-8"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
        : categories.length === 0 ? <p className="text-center text-gray-400 py-8">Aucune catégorie. Importez le dataset pour créer automatiquement les catégories.</p>
        : categories.map(cat => <CategoryNode key={cat.id} cat={cat} onRefresh={fetch} />)}
      </div>
    </div>
  )
}
