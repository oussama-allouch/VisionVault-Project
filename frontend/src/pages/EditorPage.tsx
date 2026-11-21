import ProtectedImage, { useProtectedImage } from '../components/ProtectedImage'
import { useState, useEffect, useRef, type PointerEvent } from 'react'
import { saveDownload } from '../utils/download'
import { useParams, useNavigate } from 'react-router-dom'
import { RotateCw, FlipHorizontal, FlipVertical, Crop, Maximize2, Save, Download, ArrowLeft, RefreshCw } from 'lucide-react'
import { imageService } from '../services/imageService'
import { processingService } from '../services/processingService'
import type { ImageData } from '../types'
import toast from 'react-hot-toast'

export default function EditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [image, setImage] = useState<ImageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [mode, setMode] = useState<'none' | 'crop' | 'resize'>('none')
  const [cropX, setCropX] = useState(0)
  const [cropY, setCropY] = useState(0)
  const [cropW, setCropW] = useState(200)
  const [cropH, setCropH] = useState(200)
  const [resizeW, setResizeW] = useState(0)
  const [resizeH, setResizeH] = useState(0)
  const [keepAspect, setKeepAspect] = useState(true)
  const [result, setResult] = useState<ImageData | null>(null)
  const originalUrl = useProtectedImage(image?.image_url)
  const cropAnchor = useRef<{ x: number; y: number } | null>(null)

  const cropPoint = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    const width = image?.width ?? 1
    const height = image?.height ?? 1
    return {
      x: Math.round(Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width)) * width),
      y: Math.round(Math.min(1, Math.max(0, (event.clientY - bounds.top) / bounds.height)) * height),
    }
  }

  const startCrop = (event: PointerEvent<HTMLDivElement>) => {
    if (mode !== 'crop' || !originalUrl) return
    event.currentTarget.setPointerCapture(event.pointerId)
    cropAnchor.current = cropPoint(event)
  }

  const moveCrop = (event: PointerEvent<HTMLDivElement>) => {
    const start = cropAnchor.current
    if (!start) return
    const end = cropPoint(event)
    setCropX(Math.min(start.x, end.x))
    setCropY(Math.min(start.y, end.y))
    setCropW(Math.max(1, Math.abs(start.x - end.x)))
    setCropH(Math.max(1, Math.abs(start.y - end.y)))
  }

  useEffect(() => {
    if (!id) return
    imageService.get(Number(id)).then(img => {
      setImage(img); setResizeW(img.width || 400); setResizeH(img.height || 400)
      setCropW(Math.min(img.width || 200, 200)); setCropH(Math.min(img.height || 200, 200))
      setCropX(0); setCropY(0); setResult(null)
    }).catch(() => toast.error('Image introuvable.')).finally(() => setLoading(false))
  }, [id])

  const handleCrop = async () => {
    if (!image) return
    setProcessing(true)
    try {
      const res = await processingService.crop(image.id, cropX, cropY, cropW, cropH)
      setResult(res); toast.success('Recadrage effectué !')
    } catch { toast.error('Erreur de recadrage.') }
    finally { setProcessing(false) }
  }

  const handleResize = async () => {
    if (!image) return
    setProcessing(true)
    try {
      const res = await processingService.resize(image.id, resizeW, resizeH, keepAspect)
      setResult(res); toast.success('Redimensionnement effectué !')
    } catch { toast.error('Erreur de redimensionnement.') }
    finally { setProcessing(false) }
  }

  const handleTransform = async (ops: { type: string; angle?: number; direction?: string }[]) => {
    if (!image) return
    setProcessing(true)
    try {
      const res = await processingService.transform(image.id, ops)
      setResult(res); toast.success('Transformation effectuée !')
    } catch { toast.error('Erreur de transformation.') }
    finally { setProcessing(false) }
  }

  if (loading) return <div className="flex justify-center py-16"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
  if (!image) return <p className="text-center text-gray-500 py-16">Image introuvable.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" /></button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Éditeur d'images</h1>
          <p className="text-sm text-gray-500">{image.filename}</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Original */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="p-3 border-b border-gray-200 dark:border-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300">Original</div>
          <div className="bg-gray-100 dark:bg-gray-800 flex items-center justify-center min-h-64 p-4">
            {originalUrl && (
              <div className={`relative max-w-full select-none ${mode === 'crop' ? 'cursor-crosshair touch-none' : ''}`}
                data-testid="crop-surface" onPointerDown={startCrop} onPointerMove={moveCrop}
                onPointerUp={() => { cropAnchor.current = null }} onPointerCancel={() => { cropAnchor.current = null }}>
                <img src={originalUrl} alt={image.filename} draggable={false} className="block max-w-full max-h-96" />
                {mode === 'crop' && image.width && image.height && (
                  <div data-testid="crop-selection" className="pointer-events-none absolute border-2 border-white bg-indigo-400/20 outline outline-indigo-500"
                    style={{ left: `${100 * cropX / image.width}%`, top: `${100 * cropY / image.height}%`,
                      width: `${100 * cropW / image.width}%`, height: `${100 * cropH / image.height}%` }} />
                )}
              </div>
            )}
          </div>
        </div>

        {/* Result */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="p-3 border-b border-gray-200 dark:border-gray-800 text-sm font-medium text-gray-700 dark:text-gray-300">Résultat</div>
          <div className="bg-gray-100 dark:bg-gray-800 flex items-center justify-center min-h-64 p-4">
            {result?.image_url ? <ProtectedImage src={result.image_url} alt="result" className="max-w-full max-h-96 object-contain" /> : <p className="text-gray-400 text-sm">Appliquez une transformation</p>}
          </div>
        </div>
      </div>

      {/* Tools */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Outils</h3>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setMode('crop')} className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${mode === 'crop' ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200'}`}><Crop className="w-4 h-4" /> Recadrer</button>
          <button onClick={() => setMode('resize')} className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${mode === 'resize' ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200'}`}><Maximize2 className="w-4 h-4" /> Redimensionner</button>
          <button onClick={() => handleTransform([{ type: 'rotate', angle: 90 }])} disabled={processing} className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium flex items-center gap-2 hover:bg-gray-200 disabled:opacity-50"><RotateCw className="w-4 h-4" /> Rotation 90°</button>
          <button onClick={() => handleTransform([{ type: 'flip', direction: 'horizontal' }])} disabled={processing} className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium flex items-center gap-2 hover:bg-gray-200 disabled:opacity-50"><FlipHorizontal className="w-4 h-4" /> Miroir H</button>
          <button onClick={() => handleTransform([{ type: 'flip', direction: 'vertical' }])} disabled={processing} className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium flex items-center gap-2 hover:bg-gray-200 disabled:opacity-50"><FlipVertical className="w-4 h-4" /> Miroir V</button>
          <button onClick={() => setResult(null)} className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium flex items-center gap-2 hover:bg-gray-200"><RefreshCw className="w-4 h-4" /> Réinitialiser</button>
        </div>

        {mode === 'crop' && (
          <div className="flex flex-wrap gap-3 items-end">
            {[['X', cropX, setCropX], ['Y', cropY, setCropY], ['Largeur', cropW, setCropW], ['Hauteur', cropH, setCropH]].map(([label, val, setter]) => (
              <div key={label as string}>
                <label htmlFor={`crop-${label}`} className="text-xs text-gray-500">{label as string}</label>
                <input id={`crop-${label}`} type="number" value={val as number} onChange={e => (setter as (v: number) => void)(Number(e.target.value))}
                  className="w-24 px-2 py-1.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white" />
              </div>
            ))}
            <button onClick={handleCrop} disabled={processing} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"><Save className="w-4 h-4" /> Appliquer</button>
          </div>
        )}

        {mode === 'resize' && (
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label htmlFor="resize-width" className="text-xs text-gray-500">Largeur</label>
              <input id="resize-width" type="number" value={resizeW} onChange={e => setResizeW(Number(e.target.value))}
                className="w-24 px-2 py-1.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white" />
            </div>
            <div>
              <label htmlFor="resize-height" className="text-xs text-gray-500">Hauteur</label>
              <input id="resize-height" type="number" value={resizeH} onChange={e => setResizeH(Number(e.target.value))}
                className="w-24 px-2 py-1.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white" />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <input type="checkbox" checked={keepAspect} onChange={e => setKeepAspect(e.target.checked)} className="rounded border-gray-300" />
              Conserver proportions
            </label>
            <button onClick={handleResize} disabled={processing} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"><Save className="w-4 h-4" /> Appliquer</button>
          </div>
        )}
      </div>

      {result && (
        <div className="flex gap-3">
          <button onClick={() => navigate(`/gallery`)} className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 flex items-center gap-2"><Save className="w-4 h-4" /> Voir dans la galerie</button>
          <button onClick={() => imageService.download(result.id).then(blob => saveDownload(blob, result.filename)).catch(() => toast.error('Erreur de téléchargement.'))} className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-2"><Download className="w-4 h-4" /> Télécharger</button>
        </div>
      )}
    </div>
  )
}
