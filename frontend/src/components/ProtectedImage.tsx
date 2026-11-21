import { useEffect, useState, type ImgHTMLAttributes } from 'react'
import api from '../services/api'

export function useProtectedImage(path: string | null | undefined) {
  const [loaded, setLoaded] = useState<{ path: string; url: string } | null>(null)
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    let url: string | undefined
    api.get<Blob>(path.replace(/^\/api\/v1/, ''), { responseType: 'blob', signal: controller.signal })
      .then(({ data }) => {
        if (!controller.signal.aborted) {
          url = URL.createObjectURL(data)
          setLoaded({ path, url })
        }
      })
      .catch(() => {})
    return () => {
      controller.abort()
      if (url) URL.revokeObjectURL(url)
    }
  }, [path])
  return loaded?.path === path ? loaded?.url : undefined
}

export default function ProtectedImage({ src, ...props }: ImgHTMLAttributes<HTMLImageElement>) {
  const url = useProtectedImage(src)
  return <img {...props} src={url} />
}
