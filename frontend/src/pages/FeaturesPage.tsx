import ProtectedImage from '../components/ProtectedImage'
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Grid3x3, Hash, Scan } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { featureService } from '../services/featureService'
import { imageService } from '../services/imageService'
import type { ImageData } from '../types'
import toast from 'react-hot-toast'

interface ColorMomentDetail { mean: number; std: number; skewness: number }
interface DominantColor { rgb: number[]; hex: string; percentage: number }
interface GLCMDetails { contrast: number; correlation: number; energy: number; homogeneity: number; dissimilarity: number; asm: number }
interface FeatureData {
  vector: number[]
  color_histogram: { histogram: number[]; h_hist: number[]; s_hist: number[]; v_hist: number[]; params: { h_bins: number; s_bins: number; v_bins: number } }
  color_moments: { moments: number[]; details: { H: ColorMomentDetail; S: ColorMomentDetail; V: ColorMomentDetail } }
  dominant_colors: { colors: DominantColor[]; feature_vector: number[] }
  glcm: { features: number[]; details: GLCMDetails; params: { distances: number[]; angles: number; levels: number } }
  lbp: { histogram: number[]; params: { P: number; R: number; method: string; n_bins: number } }
}

const TABS = ['Histogramme HSV', 'Moments couleur', 'Couleurs dominantes', 'GLCM', 'LBP'] as const

export default function FeaturesPage() {
  const { id } = useParams()
  const [image, setImage] = useState<ImageData | null>(null)
  const [features, setFeatures] = useState<FeatureData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    if (!id) return
    const imgId = Number(id)
    Promise.all([
      imageService.get(imgId),
      featureService.getAll(imgId),
    ]).then(([img, feat]) => {
      setImage(img)
      setFeatures(feat as FeatureData)
    }).catch(() => toast.error('Impossible de charger les descripteurs.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex justify-center py-16"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
  if (!image || !features) return <div className="text-center py-16 text-gray-500">Image ou descripteurs introuvables.</div>

  // Prepare histogram data
  const hHistData = features.color_histogram.h_hist.map((v, i) => ({ bin: i, valeur: parseFloat(v.toFixed(4)) }))
  const sHistData = features.color_histogram.s_hist.map((v, i) => ({ bin: i, valeur: parseFloat(v.toFixed(4)) }))
  const vHistData = features.color_histogram.v_hist.map((v, i) => ({ bin: i, valeur: parseFloat(v.toFixed(4)) }))

  // LBP data
  const lbpData = features.lbp.histogram.map((v, i) => ({ bin: i, valeur: parseFloat(v.toFixed(4)) }))

  const moments = features.color_moments.details

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/gallery" className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition">
          <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Descripteurs visuels</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{image.filename}</p>
        </div>
      </div>

      {/* Image info + Feature vector summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Image card */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-sm">
          <div className="bg-gray-100 dark:bg-gray-800 flex items-center justify-center h-56">
            {image.image_url ? <ProtectedImage src={image.image_url} alt={image.filename} className="max-w-full max-h-full object-contain" /> : <Grid3x3 className="w-12 h-12 text-gray-400" />}
          </div>
          <div className="p-4 space-y-2 text-sm">
            <p className="font-medium text-gray-900 dark:text-white">{image.filename}</p>
            {image.category_name && <p className="text-indigo-600 dark:text-indigo-400">{image.category_name}</p>}
            {image.width && image.height && <p className="text-gray-500">{image.width} × {image.height} px</p>}
            <div className="flex items-center gap-2 pt-2">
              {image.is_indexed ? (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 font-medium">Indexée</span>
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 font-medium">Non indexée</span>
              )}
            </div>
          </div>
        </div>

        {/* Feature vector summary */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Hash className="w-5 h-5 text-indigo-500" /> Vecteur de caractéristiques
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Dimensions totales', value: features.vector.length },
              { label: 'Hist. couleur', value: '48 dim' },
              { label: 'Moments', value: '9 dim' },
              { label: 'Dominantes', value: '20 dim' },
              { label: 'GLCM + LBP', value: '16 dim' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{value}</p>
                <p className="text-[10px] text-gray-500 dark:text-gray-400">{label}</p>
              </div>
            ))}
          </div>
          {/* Action links */}
          <div className="flex gap-2 mt-4">
            <Link to={`/search?query=${image.id}`} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 flex items-center gap-2 transition">
              <Scan className="w-4 h-4" /> Recherche CBIR
            </Link>
            <Link to="/gallery" className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-2 transition">
              Retour galerie
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="flex border-b border-gray-200 dark:border-gray-800 overflow-x-auto">
          {TABS.map((tab, i) => (
            <button key={tab} onClick={() => setActiveTab(i)}
              className={`px-5 py-3 text-sm font-medium whitespace-nowrap transition ${activeTab === i ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/30' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}>
              {tab}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* Tab 0: HSV Histogram */}
          {activeTab === 0 && (
            <div className="space-y-6">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Histogramme de couleur dans l'espace HSV, avec 16 classes par canal. H couvre [0, 180[, S et V couvrent [0, 256[ (codage OpenCV).
              </p>
              {[
                { title: 'Canal H (Teinte)', data: hHistData, color: '#f97316' },
                { title: 'Canal S (Saturation)', data: sHistData, color: '#22c55e' },
                { title: 'Canal V (Valeur)', data: vHistData, color: '#3b82f6' },
              ].map(({ title, data, color }) => (
                <div key={title}>
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{title}</h4>
                  <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={data}>
                      <XAxis dataKey="bin" tick={{ fontSize: 9 }} />
                      <YAxis tick={{ fontSize: 9 }} />
                      <Tooltip formatter={(value) => [Number(value).toFixed(4), 'Valeur']} />
                      <Bar dataKey="valeur" fill={color} radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ))}
            </div>
          )}

          {/* Tab 1: Color Moments */}
          {activeTab === 1 && (
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Trois moments statistiques (moyenne, écart-type, asymétrie) calculés pour chaque canal HSV.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-800">
                      <th className="text-left py-3 px-4 font-medium text-gray-500">Canal</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Moyenne (μ)</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Écart-type (σ)</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Asymétrie (γ)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(['H', 'S', 'V'] as const).map(ch => (
                      <tr key={ch} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{ch} ({ch === 'H' ? 'Teinte' : ch === 'S' ? 'Saturation' : 'Valeur'})</td>
                        <td className="py-3 px-4 text-right font-mono text-gray-700 dark:text-gray-300">{moments[ch].mean.toFixed(6)}</td>
                        <td className="py-3 px-4 text-right font-mono text-gray-700 dark:text-gray-300">{moments[ch].std.toFixed(6)}</td>
                        <td className="py-3 px-4 text-right font-mono text-gray-700 dark:text-gray-300">{moments[ch].skewness.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 2: Dominant Colors */}
          {activeTab === 2 && (
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Les {features.dominant_colors.colors.length} couleurs dominantes extraites par K-Means.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-5 gap-4">
                {features.dominant_colors.colors.map((c, i) => (
                  <div key={i} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-center space-y-3">
                    <div className="w-16 h-16 rounded-full mx-auto border-4 border-white dark:border-gray-700 shadow-md" style={{ backgroundColor: c.hex }} />
                    <div>
                      <p className="text-sm font-mono font-bold text-gray-900 dark:text-white">{c.hex}</p>
                      <p className="text-xs text-gray-500">RGB({c.rgb.join(', ')})</p>
                      <p className="text-xs text-indigo-600 dark:text-indigo-400 font-medium mt-1">{(c.percentage * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 3: GLCM */}
          {activeTab === 3 && (
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Matrice de co-occurrence des niveaux de gris (GLCM) — {features.glcm.params.levels} niveaux, {features.glcm.params.angles} angles.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-800">
                      <th className="text-left py-3 px-4 font-medium text-gray-500">Propriété</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Valeur</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ['Contraste', features.glcm.details.contrast],
                      ['Corrélation', features.glcm.details.correlation],
                      ['Énergie', features.glcm.details.energy],
                      ['Homogénéité', features.glcm.details.homogeneity],
                      ['Dissimilarité', features.glcm.details.dissimilarity],
                      ['ASM', features.glcm.details.asm],
                    ].map(([label, val]) => (
                      <tr key={label as string} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-3 px-4 font-medium text-gray-900 dark:text-white">{label as string}</td>
                        <td className="py-3 px-4 text-right font-mono text-gray-700 dark:text-gray-300">{(val as number).toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-3">Paramètres : distances = [{features.glcm.params.distances.join(', ')}], niveaux = {features.glcm.params.levels}</p>
            </div>
          )}

          {/* Tab 4: LBP */}
          {activeTab === 4 && (
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Local Binary Pattern (LBP) — méthode {features.lbp.params.method}, P={features.lbp.params.P}, R={features.lbp.params.R}, {features.lbp.params.n_bins} bins.
              </p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={lbpData}>
                  <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [Number(value).toFixed(4), 'Fréquence']} />
                  <Bar dataKey="valeur" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
