const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL;

function getApiBase(): string {
  if (configuredApiBase) return configuredApiBase.replace(/\/$/, '');
  if (
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ) {
    return 'http://localhost:8010/api/v1';
  }
  return '/api/v1';
}

export class AppApiError extends Error {
  code: string;
  diagnosticId?: string;
  details: Array<Record<string, unknown>>;

  constructor({
    code,
    message,
    diagnosticId,
    details = [],
  }: {
    code: string;
    message: string;
    diagnosticId?: string;
    details?: Array<Record<string, unknown>>;
  }) {
    super(message);
    this.name = 'AppApiError';
    this.code = code;
    this.diagnosticId = diagnosticId;
    this.details = details;
  }
}

export type GenerationTask = {
  id: string;
  state: string;
  original_prompt?: string;
  asset_type: 'prop' | 'character';
  provider: string;
  diagnostic_id: string;
  error_code: string | null;
  error_message: string | null;
  concept_bundle_id: string | null;
  reference_files: ReferenceFile[];
  accessory_reference_files: Array<{ name: string; reference_file: ReferenceFile }>;
  candidates: Array<{
    id: string;
    position: number;
    asset_role: string;
    asset_name: string | null;
    state: string;
    model_url: string | null;
    preview_url: string | null;
    metrics: Record<string, unknown>;
    error_code: string | null;
  }>;
};

export type ClarificationQuestion = {
  id: 'subject' | 'style' | 'material' | 'features' | 'appearance' | 'pose';
  question: string;
  answer_hint: string;
  options: Array<{
    value: string;
    label: string;
    description: string;
  }>;
  required: boolean;
};

export type PromptAnalysis = {
  ready_to_generate: boolean;
  clarity_score: number;
  detected_asset_type: 'prop' | 'character';
  clarifying_questions: ClarificationQuestion[];
  detected_accessories: string[];
  concept_image_count: number;
};

export type ReferenceFile = {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  width: number;
  height: number;
  preview_url: string;
};

export type ConceptImage = {
  id: string;
  reference_file: ReferenceFile;
  views: Array<{
    view: 'front' | 'left' | 'back' | 'right';
    reference_file: ReferenceFile;
  }>;
  accessories: Array<{
    name: string;
    reference_file: ReferenceFile;
  }>;
  model: string;
  usage_tokens: number | null;
  estimated_cost_cny: number;
  ready_for_3d: boolean;
  quality_warnings: string[];
};

export type Capabilities = {
  provider: string;
  candidate_counts: number[];
  quality_profiles?: Array<{
    id: 'standard' | 'high';
    label: string;
    face_limit: number;
    default: boolean;
  }>;
};

export type Project = {
  id: string;
  name: string;
  engine: 'unity' | 'unreal' | 'godot' | 'roblox';
  platform: 'mobile' | 'pc' | 'generic_low_poly';
  locale: 'zh-CN' | 'en';
  spec_profile: Record<string, unknown>;
};

export type GenerationTaskEvent = {
  type?: string;
  task_id: string;
  state?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(getApiBase() + path, {
    ...init,
    headers,
  });
  const payload = (await response.json().catch(() => ({}))) as {
    data?: T;
    error?: {
      code?: string;
      message?: string;
      diagnostic_id?: string;
      details?: Array<Record<string, unknown>>;
    };
  };
  if (!response.ok) {
    throw new AppApiError({
      code: payload.error?.code ?? `HTTP_${response.status}`,
      message: payload.error?.message ?? 'Request failed',
      diagnosticId: payload.error?.diagnostic_id,
      details: payload.error?.details,
    });
  }
  if (payload.data === undefined) {
    throw new Error('Response data is missing');
  }
  return payload.data;
}

export function getCapabilities(): Promise<Capabilities> {
  return request<Capabilities>('/capabilities');
}

export function analyzePrompt(
  prompt: string,
  locale: 'zh-CN' | 'en',
  assetType: 'prop' | 'character' | 'auto' = 'auto',
  hasReferenceImage = false,
): Promise<PromptAnalysis> {
  return request<PromptAnalysis>('/prompts/analyze', {
    method: 'POST',
    body: JSON.stringify({
      prompt,
      locale,
      asset_type: assetType,
      has_reference_image: hasReferenceImage,
    }),
  });
}

export function uploadReferenceImage(file: File): Promise<ReferenceFile> {
  const body = new FormData();
  body.append('file', file);
  return request<ReferenceFile>('/files/reference-images', { method: 'POST', body });
}

export function deleteReferenceImage(fileId: string): Promise<{ id: string; deleted: boolean }> {
  return request<{ id: string; deleted: boolean }>(`/files/reference-images/${fileId}`, {
    method: 'DELETE',
  });
}

export function createConceptImage(
  prompt: string,
  assetType: 'prop' | 'character',
  locale: 'zh-CN' | 'en',
): Promise<ConceptImage> {
  return request<ConceptImage>('/concept-images', {
    method: 'POST',
    body: JSON.stringify({ prompt, asset_type: assetType, locale }),
  });
}

export function getLatestConceptImage(): Promise<ConceptImage> {
  return request<ConceptImage>('/concept-images/latest');
}

export function getLatestGenerationTask(): Promise<GenerationTask> {
  return request<GenerationTask>('/generation-tasks/latest');
}

export function getGenerationTasks(limit = 20): Promise<GenerationTask[]> {
  return request<GenerationTask[]>(`/generation-tasks?limit=${limit}`);
}

export function getGenerationTask(taskId: string): Promise<GenerationTask> {
  return request<GenerationTask>(`/generation-tasks/${taskId}`);
}

export function getCandidateDownloadUrl(taskId: string, position: number): string {
  return `${getApiBase()}/generation-tasks/${encodeURIComponent(taskId)}/candidates/${position}/download`;
}

export function cancelGenerationTask(taskId: string): Promise<GenerationTask> {
  return request<GenerationTask>(`/generation-tasks/${taskId}/cancel`, { method: 'POST' });
}

export async function getOrCreateAlphaProject(locale: 'zh-CN' | 'en'): Promise<Project> {
  const projects = await request<Project[]>('/projects');
  const existing = projects.find(
    (project) =>
      project.engine === 'unity' &&
      project.platform === 'mobile',
  );
  if (existing) return existing;

  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: 'Unity URP Mobile',
      engine: 'unity',
      platform: 'mobile',
      locale,
      spec_profile: { template: 'unity_urp_mobile', triangle_budget: 20000 },
    }),
  });
}

export async function createGenerationTask(
  prompt: string,
  locale: 'zh-CN' | 'en',
  candidateCount: 1 | 2 | 4,
  assetType: 'prop' | 'character',
  referenceFileId?: string,
  referenceFileIds: string[] = referenceFileId ? [referenceFileId] : [],
  qualityTier: 'standard' | 'high' = 'high',
  conceptBundleId?: string,
  accessoryReferences: Array<{ name: string; file_id: string }> = [],
  idempotencyKey = crypto.randomUUID(),
): Promise<GenerationTask> {
  const project = await getOrCreateAlphaProject(locale);
  return request<GenerationTask>('/generation-tasks', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({
      project_id: project.id,
      asset_type: assetType,
      prompt,
      reference_file_id: referenceFileId,
      reference_file_ids: referenceFileIds,
      concept_bundle_id: conceptBundleId,
      accessory_references: accessoryReferences,
      candidate_count: candidateCount,
      quality_tier: qualityTier,
    }),
  });
}

export function subscribeGenerationTaskEvents(
  taskId: string,
  handlers: {
    onOpen?: () => void;
    onChunk?: (event: GenerationTaskEvent) => void;
    onDone?: (event: GenerationTaskEvent) => void;
    onTaskError?: (error: AppApiError) => void;
    onDisconnect?: () => void;
  },
): () => void {
  const source = new EventSource(`${getApiBase()}/generation-tasks/${taskId}/events`);
  source.onopen = () => handlers.onOpen?.();

  source.addEventListener('chunk', (event) => {
    try {
      handlers.onChunk?.(JSON.parse(event.data) as GenerationTaskEvent);
    } catch {
      handlers.onDisconnect?.();
    }
  });

  source.addEventListener('done', (event) => {
    try {
      handlers.onDone?.(JSON.parse(event.data) as GenerationTaskEvent);
    } finally {
      source.close();
    }
  });

  source.addEventListener('error', (event) => {
    const messageEvent = event as MessageEvent<string>;
    if (typeof messageEvent.data === 'string' && messageEvent.data) {
      try {
        const payload = JSON.parse(messageEvent.data) as {
          error?: { code?: string; message?: string; diagnostic_id?: string };
        };
        handlers.onTaskError?.(
          new AppApiError({
            code: payload.error?.code ?? 'TASK_STREAM_FAILED',
            message: payload.error?.message ?? 'Task stream failed',
            diagnosticId: payload.error?.diagnostic_id,
          }),
        );
      } catch {
        handlers.onDisconnect?.();
      }
    } else {
      handlers.onDisconnect?.();
    }
    source.close();
  });

  return () => source.close();
}
