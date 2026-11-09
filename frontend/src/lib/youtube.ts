const ID_RE = /^[A-Za-z0-9_-]{6,20}$/

/** Trích video id từ các dạng URL YouTube phổ biến; null nếu không trích được. */
export function extractVideoId(url: string): string | null {
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return null
  }
  const host = parsed.hostname.replace(/^www\.|^m\./, "")
  let id: string | null = null
  if (host === "youtu.be") {
    id = parsed.pathname.split("/")[1] ?? null
  } else if (host === "youtube.com" || host === "youtube-nocookie.com") {
    if (parsed.pathname === "/watch") {
      id = parsed.searchParams.get("v")
    } else {
      const m = parsed.pathname.match(/^\/(?:embed|shorts|v)\/([^/?]+)/)
      id = m ? m[1] : null
    }
  }
  return id && ID_RE.test(id) ? id : null
}

export function thumbnailUrl(id: string): string {
  return `https://i.ytimg.com/vi/${id}/mqdefault.jpg`
}

export function embedUrl(id: string): string {
  return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0`
}

export function watchUrl(id: string): string {
  return `https://www.youtube.com/watch?v=${id}`
}
