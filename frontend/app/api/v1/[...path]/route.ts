import { env } from "cloudflare:workers";

type RouteContext = {
  params: Promise<{ path: string[] }> | { path: string[] };
};

const methodsWithoutBody = new Set(["GET", "HEAD"]);

async function proxyToBackend(request: Request, context: RouteContext) {
  const workerEnv = env as unknown as { ASSETFORGE_BACKEND_URL?: string };
  const configuredBackend = (workerEnv.ASSETFORGE_BACKEND_URL ?? process.env.ASSETFORGE_BACKEND_URL)
    ?.trim()
    .replace(/\/$/, "");
  if (!configuredBackend) {
    return Response.json(
      {
        error: {
          code: "BACKEND_NOT_CONFIGURED",
          message: "上传服务尚未配置",
        },
      },
      { status: 503 },
    );
  }

  const params = await context.params;
  const sourceUrl = new URL(request.url);
  const targetUrl = new URL(`/api/v1/${params.path.map(encodeURIComponent).join("/")}`, configuredBackend);
  targetUrl.search = sourceUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("cookie");
  headers.delete("oai-sites-authorization");

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body: methodsWithoutBody.has(request.method) ? undefined : await request.arrayBuffer(),
    redirect: "manual",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("set-cookie");
  responseHeaders.set("cache-control", "no-store");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxyToBackend;
export const POST = proxyToBackend;
export const PUT = proxyToBackend;
export const PATCH = proxyToBackend;
export const DELETE = proxyToBackend;
export const OPTIONS = proxyToBackend;
