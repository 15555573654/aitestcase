export const extractErrorMessage = async (response: Response, fallback: string) => {
  try {
    const payload = await response.json()
    if (typeof payload.detail === 'string') return payload.detail
    if (Array.isArray(payload.detail)) return fallback
    return fallback
  } catch {
    return fallback
  }
}

export const requestJson = async <T>(input: string, init: RequestInit, fallback: string): Promise<T> => {
  const response = await fetch(input, init)
  if (!response.ok) throw new Error(await extractErrorMessage(response, fallback))
  return response.json() as Promise<T>
}

export const splitLines = (value: string) =>
  value
    .split(/\n|,|，/)
    .map(item => item.trim())
    .filter(Boolean)
