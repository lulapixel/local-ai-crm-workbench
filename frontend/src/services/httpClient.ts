export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const METODOS_MUTAVEIS = new Set(["POST", "PUT", "PATCH", "DELETE"])
let tokenCsrfPendente: Promise<string> | null = null

function eApiLocalSameOrigin(input: RequestInfo | URL): boolean {
  if (typeof window === "undefined") return false
  try {
    const url = new URL(typeof input === "string" ? input : input.toString(), window.location.href)
    return url.origin === window.location.origin && url.pathname.startsWith("/api/")
  } catch {
    return false
  }
}

async function obterTokenCsrf(): Promise<string> {
  if (!tokenCsrfPendente) {
    tokenCsrfPendente = fetch("/api/csrf-token", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Não foi possível iniciar a proteção CSRF (${response.status}).`)
        const dados = (await response.json()) as { csrf_token?: unknown }
        if (typeof dados.csrf_token !== "string" || dados.csrf_token.length < 32) {
          throw new Error("O servidor não entregou um token anti-CSRF válido.")
        }
        return dados.csrf_token
      })
      .catch((erro) => {
        tokenCsrfPendente = null
        throw erro
      })
  }
  return tokenCsrfPendente
}

/**
 * Fetch local com o handshake anti-CSRF para mutações feitas pelo navegador.
 * Chamadas externas (por exemplo, Nominatim) e clientes não-browser não são
 * alteradas por este helper.
 */
export async function fetchWithCsrf(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const method = (init.method || "GET").toUpperCase()
  const headers = new Headers(init.headers)

  if (!headers.has("Content-Type") && init.body !== undefined) {
    headers.set("Content-Type", "application/json")
  }

  if (METODOS_MUTAVEIS.has(method) && eApiLocalSameOrigin(input)) {
    headers.set("X-CSRF-Token", await obterTokenCsrf())
  }

  return fetch(input, {
    ...init,
    credentials: init.credentials || "same-origin",
    headers,
  })
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetchWithCsrf(url, options)
  } catch {
    throw new ApiError(
      "Não foi possível falar com o servidor. Confira se o `py app.py` ainda está rodando.",
      0
    )
  }

  if (!response.ok) {
    let mensagem = `Erro do servidor (${response.status}).`
    try {
      const dados = await response.clone().json()
      if (dados?.erro) mensagem = dados.erro
    } catch {
      // resposta não era JSON, mantém a mensagem genérica
    }
    throw new ApiError(mensagem, response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const httpClient = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
}
