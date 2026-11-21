import ProtectedImage from '../components/ProtectedImage'
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Image, ChevronLeft, ChevronRight, Check, X, RotateCcw, Zap, BarChart3, Info, Target, Loader2, Scan } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend } from 'recharts'
import { cbirService } from '../services/cbirService'
import { imageService } from '../services/imageService'
import type { ImageData, SearchResult } from '../types'
import { formatDuration } from '../utils/format'
import toast from 'react-hot-toast'

// Feature group definitions for weight visualization
const FEATURE_GROUPS = [
  { name: 'Histogramme couleur', start: 0, end: 47, color: '#6366f1' },
  { name: 'Moments de couleur', start: 48, end: 56, color: '#8b5cf6' },
  { name: 'Couleurs dominantes', start: 57, end: 76, color: '#a78bfa' },
  { name: 'GLCM', start: 77, end: 82, color: '#c084fc' },
  { name: 'LBP', start: 83, end: 92, color: '#e879f9' },
] as const

interface IterationRecord {
  iteration: number
  precisionAtK: number | null
  recallAtK: number | null
  relevantCount: number
  nonRelevantCount: number
  weights: number[] | null
  duration: number
}

export default function SearchPage() {
  const [searchParams] = useSearchParams()

  // Query state
  const [queryImage, setQueryImage] = useState<ImageData | null>(null)
  const [numResults, setNumResults] = useState(25)
  const [searching, setSearching] = useState(false)

  // Results state
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [results, setResults] = useState<SearchResult[]>([])
  const [duration, setDuration] = useState(0)
  const [iteration, setIteration] = useState(0)

  // Feedback state
  const [judgments, setJudgments] = useState<Record<number, 'relevant' | 'non_relevant' | 'neutral'>>({})
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [weights, setWeights] = useState<number[] | null>(null)
  const [history, setHistory] = useState<IterationRecord[]>([])

  // Gallery picker modal
  const [showPicker, setShowPicker] = useState(false)
  const [pickerImages, setPickerImages] = useState<ImageData[]>([])
  const [pickerPage, setPickerPage] = useState(1)
  const [pickerPages, setPickerPages] = useState(1)
  const [pickerSearch, setPickerSearch] = useState('')
  const [pickerLoading, setPickerLoading] = useState(false)

  // Load query image from URL param
  useEffect(() => {
    const qid = searchParams.get('query')
    if (qid) {
      imageService.get(Number(qid)).then(setQueryImage).catch(() => toast.error('Image requête introuvable.'))
    }
  }, [searchParams])

  // Gallery picker fetch
  const fetchPickerImages = useCallback(async () => {
    setPickerLoading(true)
    try {
      const data = await imageService.list({ page: pickerPage, per_page: 20, search: pickerSearch || undefined })
      setPickerImages(data.images)
      setPickerPages(data.pages)
    } catch { /* ignore */ }
    finally { setPickerLoading(false) }
  }, [pickerPage, pickerSearch])

  useEffect(() => { if (showPicker) fetchPickerImages() }, [showPicker, fetchPickerImages])

  // Perform CBIR search
  const handleSearch = async () => {
    if (!queryImage) { toast.error('Veuillez sélectionner une image requête.'); return }
    setSearching(true)
    setResults([]); setWeights(null); setHistory([]); setIteration(0); setJudgments({})
    try {
      const data = await cbirService.search(queryImage.id, numResults)
      setSessionId(data.session_id)
      setResults(data.results)
      setDuration(data.duration_ms)
      setIteration(0)
      setHistory([{
        iteration: 0, precisionAtK: data.precision_at_k, recallAtK: data.recall_at_k,
        relevantCount: 0, nonRelevantCount: 0, weights: null, duration: data.duration_ms,
      }])
      // Initialize all judgments as neutral
      const j: Record<number, 'relevant' | 'non_relevant' | 'neutral'> = {}
      data.results.forEach((r: SearchResult) => { j[r.image_id] = 'neutral' })
      setJudgments(j)
      toast.success(`Recherche terminée — ${data.total_results} résultats en ${formatDuration(data.duration_ms)}`)
    } catch (e: any) {
      toast.error(e?.response?.data?.message || 'Erreur de recherche CBIR.')
    } finally { setSearching(false) }
  }

  // Apply Re-weighting Type-1 feedback
  const handleFeedback = async () => {
    if (!sessionId) return
    const relevantIds = Object.entries(judgments).filter(([, v]) => v === 'relevant').map(([k]) => Number(k))
    const nonRelevantIds = Object.entries(judgments).filter(([, v]) => v === 'non_relevant').map(([k]) => Number(k))

    if (relevantIds.length === 0) {
      toast.error('Veuillez marquer au moins une image comme pertinente.')
      return
    }

    setFeedbackLoading(true)
    const nextIteration = iteration + 1
    try {
      const data = await cbirService.feedback(sessionId, nextIteration, relevantIds, nonRelevantIds, numResults)
      setResults(data.results)
      setWeights(data.weights)
      setDuration(data.duration_ms)
      setIteration(nextIteration)

      // Record history
      setHistory(prev => [...prev, {
        iteration: nextIteration,
        precisionAtK: data.precision_at_k,
        recallAtK: data.recall_at_k,
        relevantCount: relevantIds.length,
        nonRelevantCount: nonRelevantIds.length,
        weights: data.weights,
        duration: data.duration_ms,
      }])

      // Reset judgments for new results
      const j: Record<number, 'relevant' | 'non_relevant' | 'neutral'> = {}
      data.results.forEach((r: SearchResult) => { j[r.image_id] = 'neutral' })
      setJudgments(j)

      toast.success(`Re-weighting itération ${nextIteration} — P@K: ${data.precision_at_k != null ? (data.precision_at_k * 100).toFixed(1) + '%' : 'N/A'}`)
    } catch (e: any) {
      toast.error(e?.response?.data?.message || 'Erreur de feedback.')
    } finally { setFeedbackLoading(false) }
  }

  // Reset all
  const handleReset = () => {
    setQueryImage(null); setResults([]); setSessionId(null); setWeights(null)
    setHistory([]); setIteration(0); setJudgments({}); setDuration(0)
  }

  // Toggle judgment
  const toggleJudgment = (imageId: number) => {
    setJudgments(prev => {
      const current = prev[imageId] || 'neutral'
      const next = current === 'neutral' ? 'relevant' : current === 'relevant' ? 'non_relevant' : 'neutral'
      return { ...prev, [imageId]: next }
    })
  }

  // Bulk set
  const setAllJudgments = (value: 'relevant' | 'non_relevant' | 'neutral') => {
    const j: Record<number, 'relevant' | 'non_relevant' | 'neutral'> = {}
    results.forEach(r => { j[r.image_id] = value })
    setJudgments(j)
  }

  // Compute weight chart data
  const weightChartData = weights ? FEATURE_GROUPS.map(g => {
    const groupWeights = weights.slice(g.start, g.end + 1)
    const mean = groupWeights.reduce((a, b) => a + b, 0) / groupWeights.length
    return { name: g.name, poids: parseFloat(mean.toFixed(4)), fill: g.color }
  }) : []

  // History chart data for precision/recall evolution
  const historyChartData = history.map(h => ({
    iteration: `It. ${h.iteration}`,
    'Précision@K': h.precisionAtK != null ? parseFloat((h.precisionAtK * 100).toFixed(1)) : 0,
    'Rappel@K': h.recallAtK != null ? parseFloat((h.recallAtK * 100).toFixed(1)) : 0,
  }))

  const relevantCount = Object.values(judgments).filter(v => v === 'relevant').length
  const nonRelevantCount = Object.values(judgments).filter(v => v === 'non_relevant').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Scan className="w-7 h-7 text-indigo-500" /> Recherche CBIR
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Recherche d'images par similarité visuelle — Re-weighting Type-1
          </p>
        </div>
        {results.length > 0 && (
          <button onClick={handleReset} className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-2 transition">
            <RotateCcw className="w-4 h-4" /> Nouvelle recherche
          </button>
        )}
      </div>

      {/* Query Selection */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-indigo-500" /> Image requête
        </h2>
        <div className="flex flex-col sm:flex-row gap-4 items-start">
          {/* Query image preview */}
          <div className="w-40 h-40 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700 flex items-center justify-center overflow-hidden bg-gray-50 dark:bg-gray-800 shrink-0">
            {queryImage?.thumbnail_url ? (
              <ProtectedImage src={queryImage.thumbnail_url} alt={queryImage.filename} className="w-full h-full object-cover" />
            ) : (
              <div className="text-center p-4">
                <Image className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-xs text-gray-400">Aucune image</p>
              </div>
            )}
          </div>

          <div className="flex-1 space-y-3">
            {queryImage && (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <p className="font-medium text-gray-900 dark:text-white">{queryImage.filename}</p>
                {queryImage.category_name && <p>Catégorie : <span className="text-indigo-600 dark:text-indigo-400">{queryImage.category_name}</span></p>}
                {queryImage.width && queryImage.height && <p>{queryImage.width} × {queryImage.height} px</p>}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button onClick={() => { setShowPicker(true); setPickerPage(1); setPickerSearch('') }}
                className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-2 transition">
                <Search className="w-4 h-4" /> Choisir une image
              </button>
              <select value={numResults} onChange={e => setNumResults(Number(e.target.value))}
                className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
                <option value={5}>5 résultats</option>
                <option value={10}>10 résultats</option>
                <option value={20}>20 résultats</option>
                <option value={25}>25 résultats</option>
                <option value={50}>50 résultats</option>
              </select>
              <button onClick={handleSearch} disabled={!queryImage || searching}
                className="px-6 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-medium hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 flex items-center gap-2 transition shadow-sm">
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Lancer la recherche
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <>
          {/* Results header */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {results.length} résultats — Itération {iteration}
                </span>
                <span className="text-xs text-gray-400">{formatDuration(duration)}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => setAllJudgments('relevant')}
                  className="px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-400 text-xs font-medium hover:bg-green-100 dark:hover:bg-green-900 transition">
                  <Check className="w-3 h-3 inline mr-1" /> Tous pertinents
                </button>
                <button onClick={() => setAllJudgments('non_relevant')}
                  className="px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-400 text-xs font-medium hover:bg-red-100 dark:hover:bg-red-900 transition">
                  <X className="w-3 h-3 inline mr-1" /> Tous non pertinents
                </button>
                <button onClick={() => setAllJudgments('neutral')}
                  className="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition">
                  Réinitialiser
                </button>
                <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2 ml-2">
                  <span className="text-green-600">{relevantCount} ✓</span>
                  <span className="text-red-600">{nonRelevantCount} ✗</span>
                </span>
              </div>
            </div>
          </div>

          {/* Results grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {results.map(r => {
              const judgment = judgments[r.image_id] || 'neutral'
              const borderColor = judgment === 'relevant' ? 'border-green-500 ring-2 ring-green-200 dark:ring-green-900'
                : judgment === 'non_relevant' ? 'border-red-500 ring-2 ring-red-200 dark:ring-red-900'
                : 'border-gray-200 dark:border-gray-800'
              return (
                <div key={r.image_id} data-result-id={r.image_id} className={`relative bg-white dark:bg-gray-900 rounded-xl border overflow-hidden shadow-sm hover:shadow-md transition-all ${borderColor}`}>
                  {/* Rank badge */}
                  <div className="absolute top-2 left-2 z-10 w-7 h-7 rounded-full bg-black/60 text-white text-xs font-bold flex items-center justify-center">
                    {r.rank}
                  </div>
                  {/* Same category indicator */}
                  {r.same_category != null && (
                    <div className={`absolute top-2 right-2 z-10 w-5 h-5 rounded-full flex items-center justify-center ${r.same_category ? 'bg-green-500' : 'bg-red-500'}`}>
                      {r.same_category ? <Check className="w-3 h-3 text-white" /> : <X className="w-3 h-3 text-white" />}
                    </div>
                  )}
                  {/* Image */}
                  <div className="aspect-square bg-gray-100 dark:bg-gray-800 cursor-pointer" onClick={() => toggleJudgment(r.image_id)}>
                    {r.image.thumbnail_url ? (
                      <ProtectedImage src={r.image.thumbnail_url} alt={r.image.filename} className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center"><Image className="w-8 h-8 text-gray-400" /></div>
                    )}
                  </div>
                  {/* Info */}
                  <div className="p-2 space-y-1">
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{r.image.filename}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-gray-400">d = {r.distance.toFixed(4)}</span>
                      {r.image.category_name && (
                        <span className="text-[10px] text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950 px-1.5 py-0.5 rounded">{r.image.category_name}</span>
                      )}
                    </div>
                    {/* Judgment toggle */}
                    <div className="flex gap-1 pt-1">
                      <button onClick={() => setJudgments(p => ({ ...p, [r.image_id]: p[r.image_id] === 'relevant' ? 'neutral' : 'relevant' }))}
                        aria-pressed={judgment === 'relevant'} className={`flex-1 py-1 rounded text-[10px] font-medium transition ${judgment === 'relevant' ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-green-100 dark:hover:bg-green-950'}`}>
                        ✓ Pertinent
                      </button>
                      <button onClick={() => setJudgments(p => ({ ...p, [r.image_id]: p[r.image_id] === 'non_relevant' ? 'neutral' : 'non_relevant' }))}
                        aria-pressed={judgment === 'non_relevant'} className={`flex-1 py-1 rounded text-[10px] font-medium transition ${judgment === 'non_relevant' ? 'bg-red-500 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 hover:bg-red-100 dark:hover:bg-red-950'}`}>
                        ✗ Non pertinent
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Feedback button */}
          <div className="flex justify-center">
            <button onClick={handleFeedback} disabled={feedbackLoading || relevantCount === 0}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium hover:from-violet-700 hover:to-purple-700 disabled:opacity-50 flex items-center gap-2 transition shadow-lg shadow-violet-500/20 text-sm">
              {feedbackLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
              Appliquer Re-weighting Type-1 (Itération {iteration + 1})
            </button>
          </div>
        </>
      )}

      {/* Weights Visualization */}
      {weights && weightChartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Weight bar chart */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-violet-500" /> Poids par groupe de descripteurs
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={weightChartData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={130} />
                <Tooltip formatter={(value) => [Number(value).toFixed(4), 'Poids moyen']} />
                <Bar dataKey="poids" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Precision/Recall evolution */}
          {historyChartData.length > 0 && (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-indigo-500" /> Évolution Précision / Rappel
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={historyChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="iteration" tick={{ fontSize: 11 }} />
                  <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => [`${value}%`]} />
                  <Legend />
                  <Line type="monotone" dataKey="Précision@K" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="Rappel@K" stroke="#a78bfa" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Iteration History */}
      {history.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Historique des itérations</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-800">
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Itération</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Pertinentes</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Non pertinentes</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Précision@K</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Rappel@K</th>
                  <th className="text-left py-2 px-3 text-gray-500 font-medium">Durée</th>
                </tr>
              </thead>
              <tbody>
                {history.map(h => (
                  <tr key={h.iteration} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-2 px-3 font-medium text-gray-900 dark:text-white">{h.iteration}</td>
                    <td className="py-2 px-3 text-green-600">{h.relevantCount}</td>
                    <td className="py-2 px-3 text-red-600">{h.nonRelevantCount}</td>
                    <td className="py-2 px-3 text-gray-700 dark:text-gray-300">{h.precisionAtK != null ? `${(h.precisionAtK * 100).toFixed(1)}%` : '—'}</td>
                    <td className="py-2 px-3 text-gray-700 dark:text-gray-300">{h.recallAtK != null ? `${(h.recallAtK * 100).toFixed(1)}%` : '—'}</td>
                    <td className="py-2 px-3 text-gray-400">{formatDuration(h.duration)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scientific Info */}
      <div className="bg-gradient-to-r from-indigo-50 to-violet-50 dark:from-indigo-950/50 dark:to-violet-950/50 rounded-xl border border-indigo-200 dark:border-indigo-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
          <Info className="w-5 h-5 text-indigo-500" /> Méthode : Re-weighting Type-1
        </h3>
        <div className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <p>
            La méthode Re-weighting Type-1 ajuste les poids des descripteurs visuels à chaque itération
            de retour de pertinence (relevance feedback) selon la formule :
          </p>
          <div className="bg-white dark:bg-gray-900 rounded-lg p-4 font-mono text-center text-base border border-indigo-100 dark:border-indigo-900">
            w<sub>i</sub><sup>(k+1)</sup> = (ε + σ<sub>Nr,i</sub><sup>k</sup>) / (ε + σ<sub>rel,i</sub><sup>k</sup>)
          </div>
          <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400 list-disc list-inside">
            <li><strong>ε = 0.0001</strong> — constante de lissage pour éviter la division par zéro</li>
            <li><strong>σ<sub>Nr</sub></strong> — écart-type sur <em>tous</em> les résultats retournés</li>
            <li><strong>σ<sub>rel</sub></strong> — écart-type sur les images marquées comme <em>pertinentes</em> uniquement</li>
            <li>Un poids élevé signifie que le descripteur est <strong>discriminant</strong> pour les images pertinentes</li>
            <li>La requête est mise à jour : Q<sub>new</sub> = moyenne des vecteurs des images pertinentes</li>
          </ul>
          <p className="text-xs text-gray-500 italic">
            Référence : Renuka Devi SM, « Reweighing Strategies for Relevance Feedback in CBIR », IJARCCE, 2016 — Équation 5
          </p>
        </div>
      </div>

      {/* Gallery Picker Modal */}
      {showPicker && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setShowPicker(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex items-center gap-3">
              <Search className="w-5 h-5 text-gray-400" />
              <input value={pickerSearch} onChange={e => { setPickerSearch(e.target.value); setPickerPage(1) }}
                placeholder="Rechercher une image..." autoFocus
                className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white outline-none" />
              <button onClick={() => setShowPicker(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-4 overflow-auto max-h-[65vh]">
              {pickerLoading ? (
                <div className="flex justify-center py-16"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
              ) : pickerImages.length === 0 ? (
                <p className="text-center text-gray-400 py-16">Aucune image trouvée.</p>
              ) : (
                <div className="grid grid-cols-4 sm:grid-cols-5 gap-3">
                  {pickerImages.map(img => (
                    <button key={img.id} onClick={() => { setQueryImage(img); setShowPicker(false) }}
                      className={`aspect-square rounded-lg overflow-hidden border-2 transition hover:border-indigo-500 ${queryImage?.id === img.id ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-transparent'}`}>
                      {img.thumbnail_url ? <ProtectedImage src={img.thumbnail_url} alt={img.filename} className="w-full h-full object-cover" loading="lazy" /> : <div className="w-full h-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center"><Image className="w-6 h-6 text-gray-400" /></div>}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {pickerPages > 1 && (
              <div className="p-3 border-t border-gray-200 dark:border-gray-800 flex justify-center items-center gap-2">
                <button onClick={() => setPickerPage(p => Math.max(1, p - 1))} disabled={pickerPage === 1}
                  className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"><ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" /></button>
                <span className="text-xs text-gray-500">Page {pickerPage} / {pickerPages}</span>
                <button onClick={() => setPickerPage(p => Math.min(pickerPages, p + 1))} disabled={pickerPage === pickerPages}
                  className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30"><ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" /></button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
