'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Box,
  Check,
  ChevronDown,
  CircleHelp,
  CloudOff,
  Download,
  Grid3X3,
  Languages,
  Layers3,
  LoaderCircle,
  Menu,
  Mic,
  MessageCircleQuestion,
  Play,
  Plus,
  Radio,
  RefreshCw,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  UserRound,
  WandSparkles,
  X,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { TaskStatusCard } from '@/components/task-status-card';
import { TaskCenterPanel } from '@/components/task-center-panel';
import { AssetLibraryPanel } from '@/components/asset-library-panel';
import {
  HelpCenterDialog,
  ProjectSettingsDialog,
  WorkspaceMenuSheet,
  type WorkspaceView,
} from '@/components/workspace-overlays';
import {
  cancelGenerationTask,
  createGenerationTask,
  analyzePrompt,
  createConceptImage,
  deleteReferenceImage,
  getCapabilities,
  getCandidateDownloadUrl,
  getGenerationTasks,
  getGenerationTask,
  subscribeGenerationTaskEvents,
  uploadReferenceImage,
  type ClarificationQuestion,
  type ConceptImage,
  type GenerationTask,
  type ReferenceFile,
} from '@/lib/api';
import { isTerminalTaskState, mapTaskState, taskStateLabel } from '@/lib/task-state';

type Locale = 'zh-CN' | 'en';
type AssetType = 'prop' | 'character';
type QualityTier = 'standard' | 'high';
type GenerationState =
  | 'idle'
  | 'analyzing'
  | 'clarifying'
  | 'reviewing'
  | 'concept_submitting'
  | 'concept_ready'
  | 'submitting'
  | 'queued'
  | 'running'
  | 'streaming'
  | 'partial'
  | 'ready'
  | 'cancelled'
  | 'disconnected'
  | 'error';
type UploadState = 'idle' | 'uploading' | 'ready' | 'error';
type TaskConnection = 'idle' | 'live' | 'polling' | 'disconnected';

const AssetPreview = dynamic(
  () => import('@/components/asset-preview').then((module) => module.AssetPreview),
  {
    ssr: false,
    loading: () => (
      <div className="grid size-full place-items-center text-xs text-white/40">
        3D Preview
      </div>
    ),
  },
);

const copy = {
  'zh-CN': {
    project: 'Unity URP Mobile',
    generator: '生成器',
    taskCenter: '任务中心',
    assets: '资产库',
    promptLabel: '描述你需要的游戏资产',
    prompt: '低多边形风格的古代青铜宝箱，兽首锁扣，边角有轻微磨损，适合俯视角动作游戏',
    image: '添加参考图',
    imageHint: 'PNG、JPG 或 WebP，单张不超过 20 MB',
    specs: '项目规格',
    triangle: '几何面数上限',
    texture: '纹理',
    axis: '轴向',
    candidates: '候选数量',
    generateMock: '模拟生成 4 个候选',
    generateReal: '生成 1 个真实候选',
    preview: '候选预览',
    previewHint: '拖动旋转 · 滚轮缩放 · W 切换线框',
    wireframe: '线框',
    material: '材质',
    selected: '已选择',
    metrics: '模型指标',
    qa: '技术 QA',
    ready: '可以进入游戏引擎',
    geometry: '几何完整性',
    budget: '面数预算',
    pbr: 'PBR 通道',
    naming: '命名规范',
    license: '来源声明',
    export: '导出 GLB',
    mock: 'Mock 模式',
    saved: '状态已持久化',
    version: '版本 v001',
    tris: '8,420 三角面',
    materials: '2 个材质',
    size: '1.2 × 0.8 × 0.9 m',
  },
  en: {
    project: 'Unity URP Mobile',
    generator: 'Generator',
    taskCenter: 'Tasks',
    assets: 'Assets',
    promptLabel: 'Describe the game asset you need',
    prompt: 'Low-poly ancient bronze chest with a beast-head clasp and lightly worn edges, designed for a top-down action game',
    image: 'Add reference image',
    imageHint: 'PNG, JPG or WebP, up to 20 MB',
    specs: 'Project spec',
    triangle: 'Face limit',
    texture: 'Textures',
    axis: 'Axis',
    candidates: 'Candidates',
    generateMock: 'Simulate 4 candidates',
    generateReal: 'Generate 1 real candidate',
    preview: 'Candidate preview',
    previewHint: 'Drag to orbit · Scroll to zoom · W for wireframe',
    wireframe: 'Wireframe',
    material: 'Material',
    selected: 'Selected',
    metrics: 'Model metrics',
    qa: 'Technical QA',
    ready: 'Ready for the game engine',
    geometry: 'Geometry integrity',
    budget: 'Triangle budget',
    pbr: 'PBR channels',
    naming: 'Naming',
    license: 'Source declaration',
    export: 'Export GLB',
    mock: 'Mock mode',
    saved: 'State persisted',
    version: 'Version v001',
    tris: '8,420 triangles',
    materials: '2 materials',
    size: '1.2 × 0.8 × 0.9 m',
  },
} satisfies Record<Locale, Record<string, string>>;

const candidateVisuals = [
  { id: 1, tris: '8.4K', tone: 'from-[#08233b] via-[#11667d] to-[#55e5df]' },
  { id: 2, tris: '9.1K', tone: 'from-[#111a3d] via-[#3b3b8f] to-[#9c72ff]' },
  { id: 3, tris: '7.8K', tone: 'from-[#092d35] via-[#087f8c] to-[#58d8ff]' },
  { id: 4, tris: '8.9K', tone: 'from-[#15143b] via-[#4841a8] to-[#61e4dc]' },
];

export default function Home() {
  const [locale, setLocale] = useState<Locale>('zh-CN');
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('generator');
  const [menuOpen, setMenuOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selected, setSelected] = useState(1);
  const [wireframe, setWireframe] = useState(false);
  const [materialMode, setMaterialMode] = useState<'pbr' | 'clay'>('pbr');
  const [cameraResetKey, setCameraResetKey] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [generatorStarted, setGeneratorStarted] = useState(false);
  const [assetType, setAssetType] = useState<AssetType>('prop');
  const [qualityTier, setQualityTier] = useState<QualityTier>('high');
  const [referenceFile, setReferenceFile] = useState<ReferenceFile | null>(null);
  const [conceptImage, setConceptImage] = useState<ConceptImage | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadError, setUploadError] = useState('');
  const [generationState, setGenerationState] = useState<GenerationState>('idle');
  const [provider, setProvider] = useState('mock');
  const [highFaceLimit, setHighFaceLimit] = useState(2_000_000);
  const [generatedTask, setGeneratedTask] = useState<GenerationTask | null>(null);
  const [taskHistory, setTaskHistory] = useState<GenerationTask[]>([]);
  const [taskHistoryLoading, setTaskHistoryLoading] = useState(true);
  const [taskHistoryError, setTaskHistoryError] = useState('');
  const [cancellingTaskId, setCancellingTaskId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [taskConnection, setTaskConnection] = useState<TaskConnection>('idle');
  const [isCancelling, setIsCancelling] = useState(false);
  const [clarificationQuestions, setClarificationQuestions] = useState<ClarificationQuestion[]>([]);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const [customClarification, setCustomClarification] = useState<Record<string, boolean>>({});
  const [clarificationError, setClarificationError] = useState('');
  const [diagnosticId, setDiagnosticId] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [plannedAccessories, setPlannedAccessories] = useState<string[]>([]);
  const [plannedConceptCount, setPlannedConceptCount] = useState(1);
  const [lightboxImage, setLightboxImage] = useState<ReferenceFile | null>(null);
  const [conceptReviewed, setConceptReviewed] = useState(false);
  const [notice, setNotice] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingIdempotencyKeyRef = useRef<string | null>(null);
  const generationSubmissionInFlightRef = useRef(false);
  const conceptSubmissionInFlightRef = useRef(false);
  const t = copy[locale];
  const candidateCount: 1 | 4 = provider === 'mock' ? 4 : 1;
  const generationReference = referenceFile ?? conceptImage?.reference_file ?? null;
  const generationReferenceIds = referenceFile
    ? [referenceFile.id]
    : conceptImage?.views.map((item) => item.reference_file.id) ?? [];
  const threeDProviderLabel = provider === 'tripo_official'
    ? qualityTier === 'high'
      ? 'Tripo v3.1 Ultra'
      : 'Tripo P1'
    : 'HY-3D 3.1';
  const selectedFaceLimit = qualityTier === 'high' ? highFaceLimit : 20_000;
  const highFaceLimitLabel = highFaceLimit >= 1_000_000
    ? `${highFaceLimit / 1_000_000}M`
    : `${highFaceLimit / 1_000}K`;
  const selectedFaceLimitLabel = selectedFaceLimit >= 1_000_000
    ? `${selectedFaceLimit / 1_000_000}M`
    : `${selectedFaceLimit / 1_000}K`;
  const displayedCandidates = generatedTask?.candidates ?? [];
  const selectedCandidate = generatedTask?.candidates.find((candidate) => candidate.position === selected);
  const triangleCount = selectedCandidate?.metrics.triangle_count;
  const targetTriangleCount = selectedCandidate?.metrics.target_triangle_count;
  const materialCount = selectedCandidate?.metrics.material_count;
  const textureResolution = selectedCandidate?.metrics.texture_resolution;
  const pendingMetric = locale === 'zh-CN' ? '待检测' : 'Pending';
  const metricValues = [
    typeof triangleCount === 'number'
      ? `${triangleCount.toLocaleString()} ${locale === 'zh-CN' ? '三角面' : 'triangles'}`
      : typeof targetTriangleCount === 'number'
        ? `${locale === 'zh-CN' ? '目标' : 'Target'} ${targetTriangleCount.toLocaleString()}`
        : pendingMetric,
    typeof materialCount === 'number'
      ? `${materialCount} ${locale === 'zh-CN' ? '个材质' : 'materials'}`
      : pendingMetric,
    typeof textureResolution === 'number' ? `${textureResolution}px` : pendingMetric,
    pendingMetric,
  ];
  const hasInspectedModel = typeof triangleCount === 'number';
  const triangleBudgetPassed = selectedCandidate?.metrics.triangle_budget_passed;
  const qaResults = [
    [t.geometry, hasInspectedModel && Number(selectedCandidate?.metrics.mesh_count ?? 0) > 0],
    [t.budget, triangleBudgetPassed === true],
    [t.pbr, hasInspectedModel && Number(selectedCandidate?.metrics.material_count ?? 0) > 0],
    [t.naming, Boolean(selectedCandidate?.model_url?.endsWith('.glb'))],
    [t.license, hasInspectedModel && Boolean(generatedTask?.provider)],
  ] as const;
  const completedQaCount = qaResults.filter(([, passed]) => passed).length;
  const qaScore = hasInspectedModel ? completedQaCount * 20 : null;
  const visualStageActive = workspaceView === 'generator' && !generatedTask;
  const canExportSelectedCandidate = Boolean(
    generatedTask && selectedCandidate?.state === 'ready' && selectedCandidate.model_url,
  );
  const isHistoricalTaskReference = Boolean(
    generatedTask && conceptImage?.id === `legacy-${generatedTask.id}`,
  );

  const applyGenerationTask = useCallback((task: GenerationTask) => {
    setGeneratorStarted(true);
    setGeneratedTask(task);
    setTaskHistory((current) => [task, ...current.filter((item) => item.id !== task.id)].slice(0, 20));
    setAssetType(task.asset_type);
    setDiagnosticId(task.diagnostic_id);
    if (task.candidates.length > 0) {
      setSelected((current) =>
        task.candidates.some((candidate) => candidate.position === current)
          ? current
          : task.candidates[0].position,
      );
    }

    const state = mapTaskState(task.state);
    if (state === 'succeeded') setGenerationState('ready');
    else if (state === 'partially_succeeded') setGenerationState('partial');
    else if (state === 'failed') {
      setGenerationState('error');
      setErrorMessage(task.error_message ?? '生成任务失败');
    } else if (state === 'cancelled') setGenerationState('cancelled');
    else if (state === 'queued') setGenerationState('queued');
    else if (state === 'running') setGenerationState('running');
    else if (state === 'stale') setGenerationState('disconnected');
    else setGenerationState('submitting');
  }, []);

  const setTaskUrl = useCallback((taskId: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set('task', taskId);
    window.history.replaceState({}, '', url);
  }, []);

  const restoreTaskReferences = useCallback((task: GenerationTask) => {
    if (!task.reference_files.length) return;
    const labels = ['front', 'left', 'back', 'right'] as const;
    setConceptImage((current) => current ?? {
      id: task.concept_bundle_id ?? `legacy-${task.id}`,
      reference_file: task.reference_files[0],
      views: task.reference_files.map((reference_file, index) => ({
        view: labels[index] ?? 'front',
        reference_file,
      })),
      accessories: task.accessory_reference_files.map((item) => ({
        name: item.name,
        reference_file: item.reference_file,
      })),
      model: task.provider,
      usage_tokens: null,
      estimated_cost_cny: 0,
      ready_for_3d: false,
      quality_warnings: ['历史参考图未经过新版质量门禁，仅供查看'],
    });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.appReady = 'true';
    return () => {
      delete document.documentElement.dataset.appReady;
    };
  }, []);

  useEffect(() => {
    getCapabilities()
      .then((capabilities) => {
        setProvider(capabilities.provider);
        const highProfile = capabilities.quality_profiles?.find((profile) => profile.id === 'high');
        if (highProfile) setHighFaceLimit(highProfile.face_limit);
      })
      .catch(() => setProvider('mock'));
    getGenerationTasks()
      .then((tasks) => {
        setTaskHistory(tasks);
        setTaskHistoryError('');
      })
      .catch(() => setTaskHistoryError('暂时无法连接任务服务 / Task service unavailable'))
      .finally(() => setTaskHistoryLoading(false));
    const savedLocale = window.localStorage.getItem('assetforge-locale');
    if (savedLocale === 'en' || savedLocale === 'zh-CN') {
      queueMicrotask(() => setLocale(savedLocale));
    }

    const taskId = new URL(window.location.href).searchParams.get('task');
    if (!taskId) return;

    getGenerationTask(taskId)
      .then((task) => {
        applyGenerationTask(task);
        restoreTaskReferences(task);
        if (!isTerminalTaskState(task.state)) setActiveTaskId(task.id);
      })
      .catch(() => undefined);
  }, [applyGenerationTask, restoreTaskReferences]);

  useEffect(() => {
    window.localStorage.setItem('assetforge-locale', locale);
    document.documentElement.lang = locale;
  }, [locale]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches('input, textarea, select, [contenteditable="true"]')) return;
      if (event.key.toLowerCase() === 'w') setWireframe((value) => !value);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 2400);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    if (!activeTaskId) return;
    let stopped = false;
    let closeStream: (() => void) | undefined;
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let pollingStarted = false;

    const refreshTask = async () => {
      const task = await getGenerationTask(activeTaskId);
      if (stopped) return true;
      applyGenerationTask(task);
      restoreTaskReferences(task);
      if (isTerminalTaskState(task.state)) {
        setTaskConnection('idle');
        setActiveTaskId(null);
        closeStream?.();
        return true;
      }
      return false;
    };

    const beginPolling = () => {
      if (stopped || pollingStarted) return;
      pollingStarted = true;
      setTaskConnection('polling');
      const poll = async () => {
        try {
          const terminal = await refreshTask();
          if (terminal || stopped) return;
        } catch {
          if (!stopped) {
            setTaskConnection('disconnected');
            setGenerationState('disconnected');
          }
        }
        if (!stopped) pollTimer = setTimeout(poll, provider === 'mock' ? 1000 : 3000);
      };
      void poll();
    };

    if (typeof EventSource === 'undefined') {
      beginPolling();
    } else {
      closeStream = subscribeGenerationTaskEvents(activeTaskId, {
        onOpen: () => {
          if (!stopped) setTaskConnection('live');
        },
        onChunk: () => {
          if (!stopped) {
            setGenerationState('streaming');
            void refreshTask();
          }
        },
        onDone: () => void refreshTask(),
        onTaskError: (error) => {
          if (stopped) return;
          setErrorMessage(error.message);
          beginPolling();
        },
        onDisconnect: beginPolling,
      });
    }

    return () => {
      stopped = true;
      closeStream?.();
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [activeTaskId, applyGenerationTask, provider, restoreTaskReferences]);

  useEffect(() => {
    if (!lightboxImage) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setLightboxImage(null);
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [lightboxImage]);

  function toggleLocale() {
    const next = locale === 'zh-CN' ? 'en' : 'zh-CN';
    setLocale(next);
    if (prompt === copy[locale].prompt) setPrompt(copy[next].prompt);
  }

  async function refreshTaskHistory() {
    setTaskHistoryLoading(true);
    try {
      const tasks = await getGenerationTasks();
      setTaskHistory(tasks);
      setTaskHistoryError('');
    } catch {
      setTaskHistoryError(locale === 'zh-CN' ? '暂时无法连接任务服务，已显示本地已知任务。' : 'Task service is unavailable; showing locally known tasks.');
    } finally {
      setTaskHistoryLoading(false);
    }
  }

  function navigateWorkspace(view: WorkspaceView) {
    setWorkspaceView(view);
    if (view !== 'generator') void refreshTaskHistory();
  }

  function openTask(task: GenerationTask, candidatePosition?: number) {
    setGeneratorStarted(true);
    applyGenerationTask(task);
    restoreTaskReferences(task);
    setTaskUrl(task.id);
    if (typeof candidatePosition === 'number') setSelected(candidatePosition);
    if (!isTerminalTaskState(task.state)) setActiveTaskId(task.id);
    setWorkspaceView('generator');
    setNotice(locale === 'zh-CN' ? '已恢复任务状态' : 'Task state restored');
  }

  async function cancelTaskFromCenter(task: GenerationTask) {
    setCancellingTaskId(task.id);
    try {
      const cancelled = await cancelGenerationTask(task.id);
      applyGenerationTask(cancelled);
      if (generatedTask?.id === task.id) {
        setActiveTaskId(null);
        setTaskConnection('idle');
      }
      setNotice(locale === 'zh-CN' ? '任务已取消' : 'Task cancelled');
    } catch (error) {
      setNotice(error instanceof Error ? error.message : locale === 'zh-CN' ? '取消失败' : 'Cancellation failed');
    } finally {
      setCancellingTaskId(null);
    }
  }

  async function submitGeneration(
    targetPrompt: string,
    targetAssetType: AssetType = assetType,
    targetReferenceFileId: string | undefined = generationReference?.id,
    targetReferenceFileIds: string[] = generationReferenceIds,
  ) {
    if (generationSubmissionInFlightRef.current || generatedTask) return;
    generationSubmissionInFlightRef.current = true;
    setGenerationState('submitting');
    try {
      const idempotencyKey = pendingIdempotencyKeyRef.current ?? crypto.randomUUID();
      pendingIdempotencyKeyRef.current = idempotencyKey;
      const task = await createGenerationTask(
        targetPrompt,
        locale,
        candidateCount,
        targetAssetType,
        targetReferenceFileId,
        targetReferenceFileIds,
        qualityTier,
        conceptImage?.id,
        conceptImage?.accessories.map((item) => ({
          name: item.name,
          file_id: item.reference_file.id,
        })) ?? [],
        idempotencyKey,
      );
      pendingIdempotencyKeyRef.current = null;
      applyGenerationTask(task);
      setTaskUrl(task.id);
      if (!isTerminalTaskState(task.state)) setActiveTaskId(task.id);
    } catch (error) {
      setGenerationState('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : locale === 'zh-CN'
            ? '任务失败'
            : 'Task failed',
      );
    } finally {
      generationSubmissionInFlightRef.current = false;
    }
  }

  async function cancelActiveTask() {
    if (!generatedTask || isTerminalTaskState(generatedTask.state)) return;
    setIsCancelling(true);
    try {
      const task = await cancelGenerationTask(generatedTask.id);
      applyGenerationTask(task);
      setActiveTaskId(null);
      setTaskConnection('idle');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '取消任务失败');
    } finally {
      setIsCancelling(false);
    }
  }

  async function generateConcept() {
    if (conceptSubmissionInFlightRef.current || generatedTask) return;
    conceptSubmissionInFlightRef.current = true;
    setGenerationState('concept_submitting');
    setErrorMessage('');
    try {
      const concept = await createConceptImage(prompt, assetType, locale);
      setConceptImage(concept);
      setConceptReviewed(false);
      setGenerationState('concept_ready');
    } catch (error) {
      setGenerationState('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : locale === 'zh-CN'
            ? '概念图生成失败'
            : 'Concept image generation failed',
      );
    } finally {
      conceptSubmissionInFlightRef.current = false;
    }
  }

  async function generate() {
    if (!prompt.trim() && !referenceFile) {
      setGenerationState('error');
      setErrorMessage(locale === 'zh-CN' ? '请先输入资产描述' : 'Enter an asset description first');
      return;
    }
    setGenerationState('analyzing');
    setDiagnosticId('');
    setErrorMessage('');
    setClarificationError('');
    try {
      const analysis = await analyzePrompt(
        prompt,
        locale,
        referenceFile ? assetType : 'auto',
        Boolean(referenceFile),
      );
      setAssetType(analysis.detected_asset_type);
      setPlannedAccessories(analysis.detected_accessories);
      setPlannedConceptCount(analysis.concept_image_count);
      if (!analysis.ready_to_generate) {
        setClarificationQuestions(analysis.clarifying_questions);
        setClarificationAnswers({});
        setCustomClarification({});
        setGenerationState('clarifying');
        return;
      }
      setClarificationQuestions([]);
      setGenerationState('reviewing');
    } catch (error) {
      setGenerationState('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : locale === 'zh-CN'
            ? '任务失败'
            : 'Task failed',
      );
    }
  }

  function startAgentGeneration() {
    if (!prompt.trim() && !referenceFile) {
      setGenerationState('error');
      setErrorMessage(locale === 'zh-CN' ? '先描述你想生成的资产，或上传一张参考图。' : 'Describe an asset or upload a reference image first.');
      return;
    }
    setGeneratorStarted(true);
    void generate();
  }

  async function handleReferenceImage(file: File) {
    const supportedTypes = ['image/png', 'image/jpeg', 'image/webp'];
    if (!supportedTypes.includes(file.type)) {
      setUploadState('error');
      setUploadError(locale === 'zh-CN' ? '仅支持 PNG、JPG 和 WebP' : 'Only PNG, JPG, and WebP are supported');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadState('error');
      setUploadError(locale === 'zh-CN' ? '参考图不能超过 20 MB' : 'Reference image must be under 20 MB');
      return;
    }

    setUploadState('uploading');
    setUploadError('');
    try {
      if (referenceFile) await deleteReferenceImage(referenceFile.id);
      const uploaded = await uploadReferenceImage(file);
      setReferenceFile(uploaded);
      setConceptImage(null);
      setUploadState('ready');
      setClarificationQuestions([]);
      setClarificationAnswers({});
      setCustomClarification({});
      setGenerationState('idle');
    } catch (error) {
      setUploadState('error');
      setUploadError(
        error instanceof Error
          ? error.message
          : locale === 'zh-CN'
            ? '上传失败'
            : 'Upload failed',
      );
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function removeReferenceImage() {
    if (!referenceFile) return;
    setUploadError('');
    try {
      await deleteReferenceImage(referenceFile.id);
      setReferenceFile(null);
      setUploadState('idle');
      setGenerationState('idle');
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : '移除参考图失败');
    }
  }

  async function continueWithClarifications() {
    const unanswered = clarificationQuestions.some(
      (question) => !clarificationAnswers[question.id]?.trim(),
    );
    if (unanswered) {
      setClarificationError(
        locale === 'zh-CN' ? '请回答所有问题后再继续' : 'Answer every question before continuing',
      );
      return;
    }
    const heading = locale === 'zh-CN' ? '补充需求' : 'Additional requirements';
    const additions = clarificationQuestions
      .map((question) => `${question.question} ${clarificationAnswers[question.id].trim()}`)
      .join('\n');
    const enrichedPrompt = `${prompt.trim()}\n${heading}：\n${additions}`;
    setPrompt(enrichedPrompt);
    setClarificationError('');
    setGenerationState('analyzing');
    try {
      const analysis = await analyzePrompt(enrichedPrompt, locale, 'auto', false);
      setAssetType(analysis.detected_asset_type);
      setPlannedAccessories(analysis.detected_accessories);
      setPlannedConceptCount(analysis.concept_image_count);
      if (!analysis.ready_to_generate) {
        setClarificationQuestions(analysis.clarifying_questions);
        setClarificationAnswers({});
        setCustomClarification({});
        setGenerationState('clarifying');
        return;
      }
      setClarificationQuestions([]);
      setClarificationAnswers({});
      setCustomClarification({});
      setGenerationState('reviewing');
    } catch (error) {
      setGenerationState('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : locale === 'zh-CN'
            ? '需求确认失败'
            : 'Requirement review failed',
      );
    }
  }

  return (
    <main className="app-shell min-h-screen bg-background text-foreground">
      <header className="command-header flex h-14 items-center justify-between border-b border-border px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" aria-label={locale === 'zh-CN' ? '打开菜单' : 'Open menu'} onClick={() => setMenuOpen(true)}>
            <Menu />
          </Button>
          <div className="flex items-center gap-2">
            <div className="tech-logo grid size-8 place-items-center rounded-lg text-primary-foreground">
              <Box className="size-4" strokeWidth={2.2} />
            </div>
            <div>
              <p className="font-semibold leading-none tracking-[-0.02em]">AssetForge</p>
              <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                Alpha Lab
              </p>
            </div>
          </div>
          <div className="mx-2 hidden h-5 w-px bg-border sm:block" />
          <button aria-label={locale === 'zh-CN' ? '打开项目规格' : 'Open project specifications'} onClick={() => setSettingsOpen(true)} className="hidden items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:flex">
            {t.project}
            <ChevronDown className="size-3.5" />
          </button>
          <Badge variant="outline" className="hidden border-cyan-300/15 bg-cyan-300/5 font-mono text-[9px] tracking-[0.12em] text-cyan-200/70 lg:flex">
            STAGE 02 · NEURAL FORGE
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={
              provider === 'mock'
                ? 'hidden border-amber-400/25 bg-amber-400/8 text-amber-300 sm:flex'
                : 'hidden border-emerald-400/25 bg-emerald-400/8 text-emerald-300 sm:flex'
            }
          >
            <span
              className={provider === 'mock' ? 'size-1.5 rounded-full bg-amber-500' : 'size-1.5 rounded-full bg-emerald-500'}
            />
            {provider === 'mock' ? t.mock : threeDProviderLabel}
          </Badge>
          <Badge variant="outline" className="hidden text-muted-foreground md:flex">
            <ShieldCheck />
            {t.saved}
          </Badge>
          {generatedTask && (
            <Badge
              variant="outline"
              className={
                generatedTask.state === 'FAILED'
                  ? 'hidden border-destructive/30 bg-destructive/8 text-destructive md:flex'
                  : generatedTask.state === 'READY'
                    ? 'hidden border-emerald-400/25 bg-emerald-400/8 text-emerald-300 md:flex'
                    : 'hidden border-cyan-400/25 bg-cyan-400/8 text-cyan-200 md:flex'
              }
            >
              {taskConnection === 'live' ? (
                <Radio className="animate-pulse" />
              ) : taskConnection === 'disconnected' ? (
                <CloudOff />
              ) : (
                <RefreshCw className={taskConnection === 'polling' ? 'animate-spin' : ''} />
              )}
              {taskStateLabel(generatedTask.state, locale)}
            </Badge>
          )}
          <Button variant="ghost" size="sm" onClick={toggleLocale}>
            <Languages />
            {locale === 'zh-CN' ? 'EN' : '中文'}
          </Button>
          <Button variant="ghost" size="icon" aria-label={locale === 'zh-CN' ? '打开帮助中心' : 'Open help center'} onClick={() => setHelpOpen(true)}>
            <CircleHelp />
          </Button>
        </div>
      </header>

      {workspaceView === 'generator' && !generatorStarted ? (
        <section className="agent-entry relative min-h-[calc(100vh-3.5rem)] overflow-hidden px-4 py-8 sm:px-8 lg:py-14">
          <div className="asset-grid absolute inset-0 opacity-35" aria-hidden="true" />
          <div className="agent-entry-orb" aria-hidden="true" />
          <nav className="relative z-10 mx-auto flex w-fit items-center gap-1 rounded-full border border-white/10 bg-[#0a1120]/75 p-1 shadow-2xl backdrop-blur-xl" aria-label={locale === 'zh-CN' ? '工作区' : 'Workspace'}>
            <Button size="sm" className="rounded-full" aria-current="page"><WandSparkles />{t.generator}</Button>
            <Button size="sm" variant="ghost" className="rounded-full text-muted-foreground" onClick={() => navigateWorkspace('tasks')}>{t.taskCenter}</Button>
            <Button size="sm" variant="ghost" className="rounded-full text-muted-foreground" onClick={() => navigateWorkspace('assets')}>{t.assets}</Button>
          </nav>

          <div className="relative z-10 mx-auto mt-16 max-w-6xl text-center sm:mt-24">
            <Badge variant="outline" className="border-cyan-300/20 bg-cyan-300/5 font-mono tracking-[0.16em] text-cyan-100/70">
              AGENTIC 3D WORKFLOW
            </Badge>
            <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-semibold tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
              {locale === 'zh-CN' ? '把你的想法，锻造成游戏资产' : 'Forge your idea into a game-ready asset'}
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-sm leading-7 text-white/48 sm:text-base">
              {locale === 'zh-CN'
                ? '描述一个角色、道具或场景件。Agent 会先理解需求、生成视觉参考，再交付可检查的 3D 候选。'
                : 'Describe a character, prop, or environment piece. The agent plans, creates visual references, and delivers inspectable 3D candidates.'}
            </p>

            <div className="agent-composer mx-auto mt-10 max-w-5xl rounded-[28px] border border-white/14 p-3 text-left sm:p-4">
              <Textarea
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setGenerationState('idle');
                  setErrorMessage('');
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    startAgentGeneration();
                  }
                }}
                placeholder={locale === 'zh-CN' ? '上传一张图片，或描述你想制作的角色、道具、场景件…' : 'Upload an image, or describe the character, prop, or environment piece you want…'}
                aria-label={locale === 'zh-CN' ? '描述你想生成的资产' : 'Describe the asset you want to generate'}
                className="min-h-36 resize-none border-0 bg-transparent px-4 py-4 text-base leading-7 text-white shadow-none placeholder:text-white/28 focus-visible:ring-0 sm:text-lg"
              />
              {referenceFile && (
                <div className="mx-3 mb-3 flex items-center gap-3 rounded-xl border border-cyan-300/15 bg-cyan-300/6 p-2.5">
                  <div className="relative size-12 overflow-hidden rounded-lg bg-black/30">
                    <Image src={referenceFile.preview_url} alt={referenceFile.original_name} fill unoptimized className="object-cover" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-white/85">{referenceFile.original_name}</p>
                    <p className="mt-1 text-[10px] text-white/38">{referenceFile.width} × {referenceFile.height}</p>
                  </div>
                  <Button variant="ghost" size="icon" aria-label={locale === 'zh-CN' ? '移除参考图' : 'Remove reference'} onClick={() => void removeReferenceImage()}><X /></Button>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleReferenceImage(file);
                }}
              />
              <div className="flex items-center justify-between border-t border-white/8 px-2 pt-3">
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="rounded-full text-white/65 hover:bg-white/8 hover:text-white" aria-label={locale === 'zh-CN' ? '上传参考图' : 'Upload reference'} onClick={() => fileInputRef.current?.click()} disabled={uploadState === 'uploading'}>
                    {uploadState === 'uploading' ? <LoaderCircle className="animate-spin" /> : <Plus />}
                  </Button>
                  <Button variant="ghost" size="sm" className="rounded-full text-white/55 hover:bg-white/8 hover:text-white" onClick={() => setNotice(locale === 'zh-CN' ? '智能路由会根据文字与图片自动选择生成链路' : 'Smart routing selects the workflow from your text and images')}>
                    <Bot />{locale === 'zh-CN' ? '智能路由' : 'Smart route'}<ChevronDown />
                  </Button>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" className="rounded-full text-white/45 hover:bg-white/8 hover:text-white" aria-label={locale === 'zh-CN' ? '语音输入' : 'Voice input'} onClick={() => setNotice(locale === 'zh-CN' ? '语音输入将在浏览器权限适配完成后开放' : 'Voice input unlocks after browser permission support')}><Mic /></Button>
                  <Button size="icon" className="rounded-full shadow-[0_0_24px_rgba(99,232,238,.28)]" aria-label={locale === 'zh-CN' ? '发送并开始生成' : 'Send and start generation'} onClick={startAgentGeneration}><ArrowUp /></Button>
                </div>
              </div>
            </div>
            <div className="mx-auto mt-4 flex w-fit max-w-full flex-wrap items-center justify-center gap-2 rounded-full border border-white/9 bg-[#08111d]/65 p-1.5 backdrop-blur-xl" role="radiogroup" aria-label={locale === 'zh-CN' ? '输出质量' : 'Output quality'}>
              {(['high', 'standard'] as const).map((tier) => {
                const active = qualityTier === tier;
                return (
                  <label
                    key={tier}
                    className={`cursor-pointer rounded-full px-4 py-2 text-[11px] font-semibold transition-all ${active ? 'bg-primary text-primary-foreground shadow-[0_0_20px_rgba(99,232,238,.18)]' : 'text-white/48 hover:bg-white/6 hover:text-white'}`}
                  >
                    <input type="radio" name="entry-quality" value={tier} checked={active} onChange={() => setQualityTier(tier)} className="sr-only" />
                    {tier === 'high'
                      ? locale === 'zh-CN' ? `高模源文件 · 最高 ${highFaceLimitLabel} 面（默认）` : `High-poly source · up to ${highFaceLimitLabel} faces (default)`
                      : locale === 'zh-CN' ? '游戏就绪 · 最高 20K 面' : 'Game-ready · up to 20K faces'}
                  </label>
                );
              })}
            </div>
            {(uploadError || (generationState === 'error' && errorMessage)) && (
              <p className="mt-3 text-xs text-red-300">{uploadError || errorMessage}</p>
            )}

            <div className="mx-auto mt-8 flex max-w-5xl flex-wrap justify-center gap-2">
              {(
                locale === 'zh-CN'
                  ? ['图片转 3D', '设计游戏道具', '创建角色四视图', '生成场景组件', '制作 Boss 装备']
                  : ['Image to 3D', 'Design a game prop', 'Create character views', 'Generate environment kit', 'Forge boss gear']
              ).map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => setPrompt(suggestion)} className="rounded-full border border-white/9 bg-white/[0.035] px-4 py-2.5 text-xs text-white/58 transition-all hover:-translate-y-0.5 hover:border-cyan-200/25 hover:bg-cyan-200/7 hover:text-white">
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </section>
      ) : (
      <div className={`grid min-h-[calc(100vh-3.5rem)] grid-cols-1 ${workspaceView === 'generator' ? 'xl:grid-cols-[390px_minmax(620px,1fr)]' : 'xl:grid-cols-[318px_minmax(520px,1fr)_316px]'}`}>
        <aside className="control-panel border-b border-border xl:border-b-0 xl:border-r">
          <div className="flex h-12 items-center gap-1 border-b border-border px-4">
            {([
              ['generator', t.generator],
              ['tasks', t.taskCenter],
              ['assets', t.assets],
            ] as const).map(([view, label]) => (
              <button
                key={view}
                type="button"
                onClick={() => navigateWorkspace(view)}
                aria-pressed={workspaceView === view}
                className={
                  'rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ' +
                  (workspaceView === view
                    ? 'bg-secondary text-foreground'
                    : 'text-muted-foreground hover:text-foreground')
                }
              >
                {label}
              </button>
            ))}
            {workspaceView === 'generator' && (
              <button
                type="button"
                onClick={() => {
                  setGeneratorStarted(false);
                  setGenerationState('idle');
                  setGeneratedTask(null);
                  setActiveTaskId(null);
                  setConceptImage(null);
                  setReferenceFile(null);
                  setPrompt('');
                  setClarificationQuestions([]);
                  setClarificationAnswers({});
                  pendingIdempotencyKeyRef.current = null;
                  generationSubmissionInFlightRef.current = false;
                  conceptSubmissionInFlightRef.current = false;
                  const url = new URL(window.location.href);
                  url.searchParams.delete('task');
                  window.history.replaceState({}, '', url);
                }}
                className="ml-auto flex items-center gap-1 rounded-md px-2 py-1.5 text-[10px] font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <ArrowLeft className="size-3" />
                {locale === 'zh-CN' ? '新建' : 'New'}
              </button>
            )}
          </div>

          {workspaceView === 'generator' ? (
          <div className="space-y-6 p-5">
            <section>
              <div className="mb-5 space-y-3" aria-label={locale === 'zh-CN' ? '生成对话' : 'Generation conversation'}>
                <div className="flex items-start gap-2.5">
                  <span className="grid size-7 shrink-0 place-items-center rounded-full border border-cyan-300/20 bg-cyan-300/10 text-cyan-200"><Bot className="size-3.5" /></span>
                  <div className="rounded-2xl rounded-tl-sm border border-border bg-background/55 px-3 py-2.5 text-[11px] leading-5 text-muted-foreground">
                    {locale === 'zh-CN' ? '我会先理解需求并生成视觉参考；涉及真实付费调用前，会再次请你确认。' : 'I will interpret the brief and create visual references first. You will confirm before any paid generation call.'}
                  </div>
                </div>
                {prompt.trim() && (
                  <div className="flex justify-end">
                    <div className="max-w-[88%] rounded-2xl rounded-tr-sm bg-primary px-3 py-2.5 text-[11px] leading-5 text-primary-foreground shadow-[0_8px_24px_rgba(39,205,214,.12)]">
                      {prompt.trim()}
                    </div>
                  </div>
                )}
                {generationState !== 'idle' && (
                  <div className="flex items-center gap-2 pl-9 text-[10px] text-cyan-200/65">
                    {(generationState === 'analyzing' || generationState === 'concept_submitting' || generationState === 'submitting' || generationState === 'queued' || generationState === 'running' || generationState === 'streaming') && <LoaderCircle className="size-3 animate-spin" />}
                    {generationState === 'analyzing'
                      ? locale === 'zh-CN' ? '正在解析主体、风格与交付规格…' : 'Parsing subject, style, and delivery spec…'
                      : generationState === 'clarifying'
                        ? locale === 'zh-CN' ? '还需要你补充几个决定性细节。' : 'A few decisive details are still needed.'
                        : generationState === 'reviewing'
                          ? locale === 'zh-CN' ? '需求已就绪，请确认生成路线。' : 'The brief is ready. Confirm the generation route.'
                          : generationState === 'concept_submitting'
                            ? locale === 'zh-CN' ? '正在生成视觉参考…' : 'Creating visual references…'
                            : generationState === 'concept_ready'
                              ? locale === 'zh-CN' ? '视觉参考已生成，请在右侧逐张检查。' : 'Visual references are ready. Review them on the right.'
                              : generationState === 'ready' || generationState === 'partial'
                                ? locale === 'zh-CN' ? '3D 候选已返回，可以检查模型。' : '3D candidates are ready for inspection.'
                                : generationState === 'error'
                                  ? locale === 'zh-CN' ? '生成服务暂时不可用，请检查连接后重试。' : 'Generation service is unavailable. Check the connection and retry.'
                                  : locale === 'zh-CN' ? '任务正在后台执行…' : 'The task is running in the background…'}
                  </div>
                )}
              </div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="asset-prompt" className="text-xs font-semibold">
                  {locale === 'zh-CN' ? '继续补充或修改需求' : 'Continue or revise the brief'}
                </label>
                <Badge variant="secondary">AI</Badge>
              </div>
              <Textarea
                id="asset-prompt"
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setClarificationQuestions([]);
                  setClarificationAnswers({});
                  setCustomClarification({});
                  setConceptImage(null);
                  setGenerationState('idle');
                }}
                className="min-h-32 resize-none border-border bg-background/60 text-sm leading-6"
              />
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleReferenceImage(file);
                }}
              />
              {!referenceFile ? (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadState === 'uploading'}
                  className="mt-2 flex w-full items-center gap-3 rounded-lg border border-dashed border-border p-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/3 disabled:cursor-wait disabled:opacity-60"
                >
                  <span className="grid size-8 place-items-center rounded-md bg-secondary">
                    {uploadState === 'uploading' ? (
                      <LoaderCircle className="size-4 animate-spin text-primary" />
                    ) : (
                      <Upload className="size-4 text-muted-foreground" />
                    )}
                  </span>
                  <span>
                    <span className="block text-xs font-semibold">
                      {uploadState === 'uploading'
                        ? locale === 'zh-CN'
                          ? '正在上传并校验…'
                          : 'Uploading and validating…'
                        : t.image}
                    </span>
                    <span className="mt-0.5 block text-[10px] text-muted-foreground">{t.imageHint}</span>
                  </span>
                </button>
              ) : (
                <div className="mt-3 overflow-hidden rounded-xl border border-border bg-background/55">
                  <div className="flex gap-3 p-3">
                    <div className="relative h-20 w-16 shrink-0 overflow-hidden rounded-md bg-secondary">
                      <Image
                        src={referenceFile.preview_url}
                        alt={referenceFile.original_name}
                        fill
                        unoptimized
                        className="object-cover"
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold">{referenceFile.original_name}</p>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {referenceFile.width} × {referenceFile.height} · {(referenceFile.size_bytes / 1024 / 1024).toFixed(1)} MB
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-xs"
                          aria-label={locale === 'zh-CN' ? '移除参考图' : 'Remove reference image'}
                          onClick={() => void removeReferenceImage()}
                        >
                          <X />
                        </Button>
                      </div>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="mt-3 text-[10px] font-semibold text-primary hover:underline"
                      >
                        {locale === 'zh-CN' ? '替换图片' : 'Replace image'}
                      </button>
                    </div>
                  </div>
                  <div className="border-t border-border p-3">
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border border-primary bg-primary/10">
                        <span className="size-2 rounded-full bg-primary" />
                      </span>
                      <div>
                        <p className="text-[11px] font-semibold">
                          {locale === 'zh-CN' ? '根据图片主体生成 3D 模型' : 'Generate a 3D model from the subject'}
                        </p>
                        <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                          {locale === 'zh-CN'
                            ? '参考主体轮廓、外观、服装/材质与配色'
                            : 'Use the subject silhouette, appearance, outfit/materials, and colors'}
                        </p>
                      </div>
                    </div>
                    <p className="mt-3 text-[10px] font-semibold text-muted-foreground">
                      {locale === 'zh-CN' ? '这张图的主体类型' : 'Subject type'}
                    </p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setAssetType('character')}
                        className={`flex items-center gap-2 rounded-md border px-2.5 py-2 text-left text-[10px] font-semibold transition-colors ${
                          assetType === 'character'
                            ? 'border-primary bg-primary/8 text-primary'
                            : 'border-border hover:border-primary/30'
                        }`}
                      >
                        <UserRound className="size-3.5" />
                        {locale === 'zh-CN' ? '人物 / 角色' : 'Character'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setAssetType('prop')}
                        className={`flex items-center gap-2 rounded-md border px-2.5 py-2 text-left text-[10px] font-semibold transition-colors ${
                          assetType === 'prop'
                            ? 'border-primary bg-primary/8 text-primary'
                            : 'border-border hover:border-primary/30'
                        }`}
                      >
                        <Box className="size-3.5" />
                        {locale === 'zh-CN' ? '道具 / 环境件' : 'Prop / environment'}
                      </button>
                    </div>
                    {assetType === 'character' && (
                      <p className="mt-2 text-[10px] leading-4 text-amber-300">
                        {locale === 'zh-CN'
                          ? '人物图不再询问“材质”；会以外观、服装与姿态为主。'
                          : 'Character images focus on appearance, outfit, and pose—not material questions.'}
                      </p>
                    )}
                  </div>
                </div>
              )}
              {uploadError && <p className="mt-2 text-[10px] text-destructive">{uploadError}</p>}
              {generationState === 'clarifying' && (
                <div className="mt-3 rounded-xl border border-primary/25 bg-primary/5 p-3">
                  <div className="mb-3 flex items-start gap-2">
                    <MessageCircleQuestion className="mt-0.5 size-4 shrink-0 text-primary" />
                    <div>
                      <p className="text-xs font-semibold">
                        {locale === 'zh-CN' ? '还需要确认一些信息' : 'A few details are still needed'}
                      </p>
                      <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                        {locale === 'zh-CN'
                          ? '回答后才会提交生成，避免浪费调用次数。'
                          : 'Generation starts only after your answers, avoiding wasted calls.'}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {clarificationQuestions.map((question) => (
                      <div key={question.id}>
                        <p className="mb-1.5 text-[11px] font-medium">{question.question}</p>
                        <div className="space-y-1.5" role="radiogroup" aria-label={question.question}>
                          {question.options.map((option) => {
                            const selectedOption =
                              !customClarification[question.id] &&
                              clarificationAnswers[question.id] === option.value;
                            return (
                              <label
                                key={option.value}
                                aria-label={`${question.question}：${option.label}`}
                                className={`flex w-full cursor-pointer items-start gap-2 rounded-lg border p-2 text-left transition-colors ${
                                  selectedOption
                                    ? 'border-primary bg-primary/8'
                                    : 'border-border bg-background/60 hover:border-primary/35'
                                }`}
                              >
                                <input
                                  type="radio"
                                  name={`clarification-${question.id}`}
                                  value={option.value}
                                  checked={selectedOption}
                                  onChange={() => {
                                    setClarificationAnswers((current) => ({
                                      ...current,
                                      [question.id]: option.value,
                                    }));
                                    setCustomClarification((current) => ({
                                      ...current,
                                      [question.id]: false,
                                    }));
                                    setClarificationError('');
                                  }}
                                  className="sr-only"
                                />
                                <span
                                  className={`mt-0.5 size-3.5 shrink-0 rounded-full border ${
                                    selectedOption
                                      ? 'border-[4px] border-primary'
                                      : 'border-muted-foreground/45'
                                  }`}
                                />
                                <span>
                                  <span className="block text-[11px] font-semibold">{option.label}</span>
                                  <span className="mt-0.5 block text-[9px] leading-3.5 text-muted-foreground">
                                    {option.description}
                                  </span>
                                </span>
                              </label>
                            );
                          })}
                          <label
                            aria-label={`${question.question}：${locale === 'zh-CN' ? '其他 / 自定义' : 'Other / custom'}`}
                            className={`flex w-full cursor-pointer items-center gap-2 rounded-lg border p-2 text-left text-[11px] font-semibold transition-colors ${
                              customClarification[question.id]
                                ? 'border-primary bg-primary/8'
                                : 'border-border bg-background/60 hover:border-primary/35'
                            }`}
                          >
                            <input
                              type="radio"
                              name={`clarification-${question.id}`}
                              value="custom"
                              checked={Boolean(customClarification[question.id])}
                              onChange={() => {
                                setCustomClarification((current) => ({
                                  ...current,
                                  [question.id]: true,
                                }));
                                setClarificationAnswers((current) => ({
                                  ...current,
                                  [question.id]: '',
                                }));
                                setClarificationError('');
                              }}
                              className="sr-only"
                            />
                            <span
                              className={`size-3.5 shrink-0 rounded-full border ${
                                customClarification[question.id]
                                  ? 'border-[4px] border-primary'
                                  : 'border-muted-foreground/45'
                              }`}
                            />
                            {locale === 'zh-CN' ? '其他 / 自定义' : 'Other / custom'}
                          </label>
                        </div>
                        {customClarification[question.id] && (
                          <Input
                            value={clarificationAnswers[question.id] ?? ''}
                            placeholder={question.answer_hint}
                            maxLength={240}
                            onChange={(event) => {
                              setClarificationAnswers((current) => ({
                                ...current,
                                [question.id]: event.target.value,
                              }));
                              setClarificationError('');
                            }}
                            className="mt-2 bg-background"
                          />
                        )}
                      </div>
                    ))}
                  </div>
                  {clarificationError && (
                    <p className="mt-2 text-[10px] text-destructive">{clarificationError}</p>
                  )}
                  <Button className="mt-3 h-8 w-full" onClick={continueWithClarifications}>
                    <WandSparkles />
                    {locale === 'zh-CN' ? '补充并继续生成' : 'Add details and continue'}
                  </Button>
                </div>
              )}
              {generationState === 'reviewing' && (
                <div className="mt-3 rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-3">
                  <div className="flex items-start gap-2">
                    <ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                    <div>
                      <p className="text-xs font-semibold">
                        {locale === 'zh-CN' ? '生成前确认' : 'Review before generation'}
                      </p>
                      <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                        {locale === 'zh-CN'
                          ? '只有点击下方确认按钮后，才会创建 3D 任务。'
                          : 'A 3D task is created only after you confirm below.'}
                      </p>
                    </div>
                  </div>
                  <dl className="mt-3 space-y-2 rounded-lg border border-border bg-background/70 p-2.5 text-[10px]">
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-muted-foreground">{locale === 'zh-CN' ? '输入' : 'Input'}</dt>
                      <dd className="max-w-[180px] text-right font-medium">
                        {referenceFile
                          ? `${locale === 'zh-CN' ? '参考图' : 'Reference'} · ${referenceFile.original_name}`
                          : prompt.trim()}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">{locale === 'zh-CN' ? '主体类型' : 'Subject type'}</dt>
                      <dd className="font-medium">
                        {assetType === 'character'
                          ? locale === 'zh-CN'
                            ? '人物 / 角色'
                            : 'Character'
                          : locale === 'zh-CN'
                            ? '道具 / 环境件'
                            : 'Prop / environment'}
                      </dd>
                    </div>
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">{locale === 'zh-CN' ? '生成路由' : 'Generation route'}</dt>
                      <dd className="max-w-[190px] text-right font-medium">
                        {provider === 'mock'
                          ? 'Mock'
                          : referenceFile
                            ? assetType === 'character'
                              ? `${threeDProviderLabel} ${locale === 'zh-CN' ? '补全多视图' : 'multiview'} → ${qualityTier === 'high' ? 'v3.1 Ultra · no reduction' : 'P1 Game Ready'}`
                              : `${threeDProviderLabel} → ${qualityTier === 'high' ? 'v3.1 Ultra · no reduction' : 'P1 Game Ready'}`
                            : `Seedream 5 Pro (${plannedConceptCount}) → ${qualityTier === 'high' ? 'Tripo v3.1 Ultra · no reduction' : `${threeDProviderLabel} Game Ready`}`}
                      </dd>
                    </div>
                    {!referenceFile && plannedAccessories.length > 0 && (
                      <div className="flex items-start justify-between gap-3">
                        <dt className="text-muted-foreground">{locale === 'zh-CN' ? '独立配件' : 'Separate accessories'}</dt>
                        <dd className="max-w-[180px] text-right font-medium">{plannedAccessories.join('、')}</dd>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <dt className="text-muted-foreground">{locale === 'zh-CN' ? '验收目标' : 'Acceptance target'}</dt>
                      <dd className="font-medium">
                        {qualityTier === 'high'
                          ? `${selectedFaceLimitLabel} faces · Extreme PBR · source asset`
                          : '20K faces · Detailed PBR · game ready'}
                      </dd>
                    </div>
                  </dl>
                  {provider !== 'mock' && (
                    <p className="mt-2 text-[10px] leading-4 text-amber-300">
                      {!referenceFile
                        ? locale === 'zh-CN'
                          ? `本次生成 ${plannedConceptCount} 张参考图（${assetType === 'character' ? '正/左/后/右完整人物' : '主体'}${plannedAccessories.length ? ` + ${plannedAccessories.length} 个独立配件` : ''}），预计约 ¥${(plannedConceptCount * 0.3).toFixed(2)}；确认后才会另行提交 3D。`
                          : `This creates ${plannedConceptCount} references for about ¥${(plannedConceptCount * 0.3).toFixed(2)}; 3D requires a separate confirmation.`
                        : locale === 'zh-CN'
                          ? '确认后将调用 3D 模型并可能产生费用；只生成 1 个候选。'
                          : 'Confirmation calls the 3D provider and may incur cost; one candidate will be created.'}
                    </p>
                  )}
                  <div className="mt-3 grid grid-cols-[0.8fr_1.2fr] gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="h-8"
                      onClick={() => setGenerationState('idle')}
                    >
                      {locale === 'zh-CN' ? '返回修改' : 'Edit'}
                    </Button>
                    <Button
                      type="button"
                      className="h-8"
                      onClick={() =>
                        void (provider !== 'mock' && !referenceFile
                          ? generateConcept()
                          : submitGeneration(prompt, assetType))
                      }
                    >
                      <WandSparkles />
                      {provider !== 'mock' && !referenceFile
                        ? locale === 'zh-CN'
                          ? `生成 ${plannedConceptCount} 张参考图`
                          : `Generate ${plannedConceptCount} references`
                        : locale === 'zh-CN'
                          ? '确认并开始生成'
                          : 'Confirm and generate'}
                    </Button>
                  </div>
                </div>
              )}
              {(generationState === 'concept_submitting' || conceptImage) && (
                <div className="mt-3 overflow-hidden rounded-xl border border-primary/25 bg-primary/5">
                  <div className="p-3">
                    <div className="flex items-start gap-2">
                      {generationState === 'concept_submitting' ? (
                        <LoaderCircle className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
                      ) : (
                        <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                      )}
                      <div>
                        <p className="text-xs font-semibold">
                          {generationState === 'concept_submitting'
                            ? locale === 'zh-CN'
                              ? '正在生成概念图…'
                              : 'Generating concept image…'
                            : isHistoricalTaskReference
                              ? locale === 'zh-CN'
                                ? '历史任务参考图'
                                : 'Historical task reference'
                            : locale === 'zh-CN'
                              ? '请确认概念图'
                              : 'Review the concept image'}
                        </p>
                        <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
                          {isHistoricalTaskReference
                            ? locale === 'zh-CN'
                              ? '这是该任务当时使用的输入图，仅供回看，不会重新触发质量检查或计费。'
                              : 'This is the original input for the completed task. Viewing it does not rerun checks or incur cost.'
                            : locale === 'zh-CN'
                              ? '确认主体、轮廓、风格和关键细节后，再提交 3D。'
                              : 'Confirm the subject, silhouette, style, and key details before 3D.'}
                        </p>
                      </div>
                    </div>
                    {conceptImage && generationState !== 'concept_submitting' && (
                      <>
                        <div className={`mt-3 grid gap-2 ${conceptImage.views.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                          {(conceptImage.views.length
                            ? conceptImage.views
                            : [{ view: 'front' as const, reference_file: conceptImage.reference_file }]
                          ).map((item) => (
                            <div key={item.reference_file.id}>
                              <button
                                type="button"
                                onClick={() => setLightboxImage(item.reference_file)}
                                className="relative block aspect-square w-full overflow-hidden rounded-lg border border-border bg-[#111] focus:outline-none focus:ring-2 focus:ring-primary"
                                aria-label={locale === 'zh-CN' ? '查看参考图大图' : 'Open full-size reference'}
                              >
                                <Image
                                  src={item.reference_file.preview_url}
                                  alt={`${locale === 'zh-CN' ? '人物视图' : 'Character view'} ${item.view}`}
                                  fill
                                  unoptimized
                                  className="object-contain"
                                />
                                <span className="absolute bottom-1.5 right-1.5 rounded bg-black/70 px-1.5 py-1 text-[9px] text-white">
                                  {locale === 'zh-CN' ? '点击查看' : 'Open'}
                                </span>
                              </button>
                              <p className="mt-1 text-center text-[9px] font-semibold text-muted-foreground">
                                {{
                                  front: locale === 'zh-CN' ? '正面' : 'Front',
                                  left: locale === 'zh-CN' ? '左侧' : 'Left',
                                  back: locale === 'zh-CN' ? '背面' : 'Back',
                                  right: locale === 'zh-CN' ? '右侧' : 'Right',
                                }[item.view]}
                              </p>
                            </div>
                          ))}
                        </div>
                        {conceptImage.accessories.length > 0 && (
                          <div className="mt-3 rounded-lg border border-border bg-background/70 p-2">
                            <p className="mb-2 text-[10px] font-semibold">
                              {locale === 'zh-CN' ? '已拆分的独立配件资产' : 'Separate accessory assets'}
                            </p>
                            <div className="grid grid-cols-2 gap-2">
                              {conceptImage.accessories.map((accessory) => (
                                <div key={accessory.reference_file.id}>
                                  <button
                                    type="button"
                                    onClick={() => setLightboxImage(accessory.reference_file)}
                                    className="relative block aspect-square w-full overflow-hidden rounded-md bg-[#111] focus:outline-none focus:ring-2 focus:ring-primary"
                                  >
                                    <Image
                                      src={accessory.reference_file.preview_url}
                                      alt={accessory.name}
                                      fill
                                      unoptimized
                                      className="object-contain"
                                    />
                                  </button>
                                  <p className="mt-1 text-center text-[9px] font-medium">{accessory.name}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                          <span>{conceptImage.model}</span>
                          <span>
                            {conceptImage.views.length + conceptImage.accessories.length} {locale === 'zh-CN' ? '张' : 'images'} · ¥{conceptImage.estimated_cost_cny.toFixed(2)}
                          </span>
                        </div>
                        {!isHistoricalTaskReference && (
                          <p className="mt-2 text-[10px] leading-4 text-amber-300">
                            {locale === 'zh-CN'
                              ? assetType === 'character'
                                ? '下一步将把人物四视图作为 3D 输入；配件保留为独立参考资产。3D 会单独产生费用。'
                                : '下一步将把这张参考图作为 3D 输入，会单独产生 3D 费用。'
                              : 'The next step uses these references for 3D and incurs a separate 3D charge.'}
                          </p>
                        )}
                        {!isHistoricalTaskReference && conceptImage.quality_warnings.length > 0 && (
                          <div className="mt-2 rounded-lg border border-red-400/25 bg-red-400/8 p-2 text-[10px] leading-4 text-red-300">
                            <p className="font-semibold">{locale === 'zh-CN' ? '参考图未通过建模检查' : 'Reference check failed'}</p>
                            {conceptImage.quality_warnings.map((warning) => <p key={warning}>· {warning}</p>)}
                            <p className="mt-1">{locale === 'zh-CN' ? '请返回修改并重新生成参考图；系统不会自动扣费重试。' : 'Regenerate references before 3D; no automatic paid retry occurs.'}</p>
                          </div>
                        )}
                        {!isHistoricalTaskReference && conceptImage.ready_for_3d && (
                          <label className="mt-2 flex cursor-pointer items-start gap-2 rounded-lg border border-border bg-background/70 p-2 text-[10px] leading-4">
                            <input
                              type="checkbox"
                              checked={conceptReviewed}
                              onChange={(event) => setConceptReviewed(event.target.checked)}
                              className="mt-0.5"
                            />
                            <span>{locale === 'zh-CN' ? '我已逐张查看大图：四视图方向正确、人物无遮挡，人物图中不含已拆分配件。' : 'I checked every full-size view: angles are correct, character is unobstructed, and separated accessories are absent.'}</span>
                          </label>
                        )}
                        {!isHistoricalTaskReference && conceptImage.accessories.length > 0 && (
                          <p className="mt-2 text-[10px] font-medium text-amber-300">
                            {locale === 'zh-CN'
                              ? `确认后会提交 ${1 + conceptImage.accessories.length} 个独立 3D 资产（人物主体 + ${conceptImage.accessories.map((item) => item.name).join('、')}），每个资产单独计费。`
                              : `${1 + conceptImage.accessories.length} separate 3D assets will be billed individually.`}
                          </p>
                        )}
                        {!isHistoricalTaskReference && !generatedTask && <div className="mt-3 grid grid-cols-[0.8fr_1.2fr] gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            className="h-8"
                            onClick={() => {
                              setConceptImage(null);
                              setGenerationState('idle');
                            }}
                          >
                            {locale === 'zh-CN' ? '返回修改' : 'Edit request'}
                          </Button>
                          <Button
                            type="button"
                            className="h-8"
                            disabled={
                              !conceptImage.ready_for_3d ||
                              !conceptReviewed ||
                              generationState === 'submitting' ||
                              generationState === 'queued' ||
                              generationState === 'running' ||
                              generationState === 'streaming'
                            }
                            onClick={() =>
                              void submitGeneration(
                                prompt,
                                assetType,
                                conceptImage.reference_file.id,
                                conceptImage.views.map((item) => item.reference_file.id),
                              )
                            }
                          >
                            <WandSparkles />
                            {locale === 'zh-CN' ? '确认概念并生成 3D' : 'Approve and generate 3D'}
                          </Button>
                        </div>}
                      </>
                    )}
                  </div>
                </div>
              )}
            </section>

            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-xs font-semibold">{t.specs}</h2>
                <Button variant="ghost" size="icon-xs" aria-label={locale === 'zh-CN' ? '配置项目规格' : 'Configure project specifications'} onClick={() => setSettingsOpen(true)}>
                  <Settings2 />
                </Button>
              </div>
              <div className="mb-3 grid grid-cols-2 gap-2" role="radiogroup" aria-label={locale === 'zh-CN' ? '生成质量' : 'Generation quality'}>
                  {(['high', 'standard'] as const).map((tier) => (
                    <label
                      key={tier}
                      className={`cursor-pointer rounded-lg border px-2.5 py-2 text-left transition-colors ${
                        qualityTier === tier
                          ? 'border-primary bg-primary/8 text-primary'
                          : 'border-border bg-background/50 text-muted-foreground'
                      }`}
                    >
                      <input type="radio" name="workspace-quality" value={tier} checked={qualityTier === tier} onChange={() => setQualityTier(tier)} className="sr-only" />
                      <span className="block text-[10px] font-semibold">
                        {tier === 'high'
                          ? locale === 'zh-CN'
                            ? '高模源文件（默认）'
                            : 'High-poly source (default)'
                          : locale === 'zh-CN'
                            ? '游戏就绪'
                            : 'Game-ready'}
                      </span>
                      <span className="mt-0.5 block text-[9px] leading-3.5">
                        {tier === 'high'
                          ? `v3.1 Ultra · ${highFaceLimitLabel} faces · Extreme PBR`
                          : 'P1 · 20K faces · Detailed PBR'}
                      </span>
                    </label>
                  ))}
                </div>
              <dl className="divide-y divide-border rounded-lg border border-border bg-background/50 px-3">
                {[
                  [t.triangle, selectedFaceLimitLabel],
                  [t.texture, qualityTier === 'high' ? 'Extreme PBR · source' : 'Detailed PBR · runtime'],
                  [t.axis, 'Y Up · Z Forward'],
                  [t.candidates, String(candidateCount)],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between py-2.5 text-xs">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>

            <Button
              className="h-10 w-full bg-primary shadow-[0_0_0_1px_rgba(117,238,242,.18),0_12px_34px_rgba(39,205,214,.18)] hover:bg-primary/90"
              onClick={generate}
              disabled={
                Boolean(generatedTask) ||
                generationState === 'submitting' ||
                generationState === 'queued' ||
                generationState === 'running' ||
                generationState === 'streaming' ||
                generationState === 'analyzing' ||
                generationState === 'reviewing' ||
                generationState === 'concept_submitting' ||
                generationState === 'concept_ready' ||
                uploadState === 'uploading'
              }
            >
              {generationState === 'submitting' ||
              generationState === 'queued' ||
              generationState === 'running' ||
              generationState === 'streaming' ||
              generationState === 'analyzing' ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <WandSparkles />
              )}
              {generationState === 'analyzing'
                ? locale === 'zh-CN'
                  ? '正在检查需求…'
                  : 'Checking requirements…'
                : generationState === 'submitting'
                ? locale === 'zh-CN'
                  ? '正在提交任务…'
                  : 'Submitting task…'
                : generationState === 'queued'
                  ? locale === 'zh-CN'
                    ? '任务已进入队列'
                    : 'Task queued'
                : generationState === 'running'
                  ? generatedTask
                    ? taskStateLabel(generatedTask.state, locale)
                    : locale === 'zh-CN'
                      ? '正在生成…'
                      : 'Generating…'
                : generationState === 'streaming'
                  ? locale === 'zh-CN'
                    ? '候选正在返回…'
                    : 'Candidates are arriving…'
                : generationState === 'reviewing'
                  ? locale === 'zh-CN'
                    ? '请在上方确认'
                    : 'Review above'
                : generationState === 'concept_submitting'
                  ? locale === 'zh-CN'
                    ? '正在生成概念图…'
                    : 'Generating concept…'
                : generationState === 'concept_ready'
                  ? locale === 'zh-CN'
                    ? '请在上方确认概念图'
                    : 'Review concept above'
                : generatedTask
                  ? locale === 'zh-CN'
                    ? '任务已结束，请点击“新建”后再生成'
                    : 'Task complete. Choose New before generating again.'
                : provider === 'mock'
                  ? t.generateMock
                  : t.generateReal}
            </Button>
            {generatedTask && !isTerminalTaskState(generatedTask.state) && (
              <TaskStatusCard
                task={generatedTask}
                locale={locale}
                connection={taskConnection}
                cancelling={isCancelling}
                onCancel={() => void cancelActiveTask()}
              />
            )}
            {generationState === 'ready' && provider === 'mock' && (
              <div className="rounded-lg border border-amber-400/25 bg-amber-400/8 p-3 text-[11px] leading-5 text-amber-200">
                <p className="font-semibold">
                  {locale === 'zh-CN' ? '模拟任务已完成' : 'Mock task completed'}
                </p>
                <p>
                  {locale === 'zh-CN'
                    ? '当前尚未接入真实 3D 模型 API，所以画面不会随输入变化。'
                    : 'No real 3D model API is connected yet, so the mesh will not change with your prompt.'}
                </p>
                <p className="mt-1 text-[10px] text-amber-300/70">{diagnosticId}</p>
              </div>
            )}
            {generationState === 'error' && (
              <div className="rounded-md bg-destructive/8 px-3 py-2 text-center text-[11px] text-destructive">
                <p>{errorMessage}</p>
                {diagnosticId && <p className="mt-1 font-mono text-[9px] opacity-70">{diagnosticId}</p>}
              </div>
            )}
            {generationState === 'cancelled' && (
              <div className="rounded-md border border-border bg-secondary/45 px-3 py-2 text-center text-[11px] text-muted-foreground">
                {locale === 'zh-CN'
                  ? '任务已取消。已生成的信息会保留，你可以修改需求后重新开始。'
                  : 'Task cancelled. Existing information is preserved; edit the request to start again.'}
              </div>
            )}
            {generationState === 'partial' && (
              <div className="rounded-md border border-amber-400/25 bg-amber-400/8 px-3 py-2 text-[11px] leading-5 text-amber-200">
                {locale === 'zh-CN'
                  ? '任务已完成，但技术 QA 发现需要修复的项目。成功候选已保留。'
                  : 'Task completed with technical QA issues. Successful candidates are preserved.'}
              </div>
            )}
            {generationState === 'disconnected' && (
              <div className="rounded-md border border-cyan-400/25 bg-cyan-400/8 px-3 py-2 text-[11px] leading-5 text-cyan-200">
                {locale === 'zh-CN'
                  ? '连接暂时中断，任务未必停止。系统正在根据任务 ID 恢复真实状态。'
                  : 'Connection interrupted; the task may still be running. Recovering by task ID.'}
              </div>
            )}
          </div>
          ) : workspaceView === 'tasks' ? (
            <TaskCenterPanel
              tasks={taskHistory}
              locale={locale}
              loading={taskHistoryLoading}
              error={taskHistoryError}
              cancellingTaskId={cancellingTaskId}
              onRefresh={() => void refreshTaskHistory()}
              onOpenTask={openTask}
              onCancelTask={(task) => void cancelTaskFromCenter(task)}
              onStart={() => setWorkspaceView('generator')}
            />
          ) : (
            <AssetLibraryPanel
              tasks={taskHistory}
              locale={locale}
              onOpenAsset={openTask}
              onStart={() => setWorkspaceView('generator')}
            />
          )}
        </aside>

        {visualStageActive ? (
        <section className="visual-generation-stage relative min-h-[680px] overflow-hidden text-white" data-testid="visual-generation-stage">
          <div className="asset-grid absolute inset-0 opacity-45" />
          <div className="preview-aurora" aria-hidden="true" />
          <div className="preview-scan" aria-hidden="true" />
          <div className="absolute inset-x-0 top-0 z-10 flex min-h-16 items-center justify-between border-b border-white/8 bg-[#070b14]/45 px-5 py-3 backdrop-blur-md">
            <div>
              <p className="flex items-center gap-2 text-xs font-semibold"><span className="signal-dot" aria-hidden="true" />{locale === 'zh-CN' ? '视觉生成区' : 'Visual generation'}</p>
              <p className="mt-1 text-[10px] text-white/42">{locale === 'zh-CN' ? '参考图与概念图会先在这里生成，再进入 3D 建模' : 'References and concept images appear here before 3D modeling'}</p>
            </div>
            <Badge variant="outline" className="border-cyan-300/15 bg-cyan-300/5 font-mono text-[9px] tracking-[0.12em] text-cyan-100/65">
              IMAGE → 3D
            </Badge>
          </div>

          <div className="absolute inset-0 z-[2] flex items-center justify-center px-5 pb-36 pt-24 sm:px-8">
            {conceptImage ? (
              <div className={`grid h-full w-full max-w-5xl gap-3 ${conceptImage.views.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {(conceptImage.views.length ? conceptImage.views : [{ view: 'front' as const, reference_file: conceptImage.reference_file }]).map((item) => (
                  <button key={item.reference_file.id} type="button" onClick={() => setLightboxImage(item.reference_file)} className="group relative min-h-0 overflow-hidden rounded-2xl border border-white/10 bg-black/20 shadow-2xl transition-colors hover:border-cyan-200/35" aria-label={locale === 'zh-CN' ? '查看生成图片' : 'Open generated image'}>
                    <Image src={item.reference_file.preview_url} alt={`${item.view} concept`} fill unoptimized className="object-contain transition-transform duration-500 group-hover:scale-[1.015]" />
                    <span className="absolute bottom-3 left-3 rounded-full border border-white/10 bg-black/60 px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.12em] backdrop-blur-md">{item.view}</span>
                  </button>
                ))}
              </div>
            ) : referenceFile ? (
              <button type="button" onClick={() => setLightboxImage(referenceFile)} className="group relative h-full w-full max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-black/20 shadow-2xl transition-colors hover:border-cyan-200/35" aria-label={locale === 'zh-CN' ? '查看参考图' : 'Open reference image'}>
                <Image src={referenceFile.preview_url} alt={referenceFile.original_name} fill unoptimized className="object-contain transition-transform duration-500 group-hover:scale-[1.015]" />
                <span className="absolute bottom-4 left-4 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 text-[10px] backdrop-blur-md">{locale === 'zh-CN' ? '用户参考图' : 'User reference'}</span>
              </button>
            ) : (
              <div className="relative grid max-w-xl place-items-center text-center">
                <div className="visual-core mb-8 grid size-32 place-items-center rounded-[34px] border border-cyan-200/20 bg-cyan-200/6 shadow-[0_0_80px_rgba(57,213,224,.16)]">
                  {generationState === 'analyzing' || generationState === 'concept_submitting' ? <LoaderCircle className="size-10 animate-spin text-cyan-200" /> : <WandSparkles className="size-10 text-cyan-200" />}
                </div>
                <h2 className="text-2xl font-semibold tracking-[-0.035em]">
                  {generationState === 'analyzing'
                    ? locale === 'zh-CN' ? '正在理解你的创作意图' : 'Understanding your creative intent'
                    : generationState === 'reviewing'
                      ? locale === 'zh-CN' ? '生成路线已规划' : 'Generation route planned'
                      : generationState === 'concept_submitting'
                        ? locale === 'zh-CN' ? '正在绘制视觉参考' : 'Creating visual references'
                        : generationState === 'error'
                          ? locale === 'zh-CN' ? '生成服务暂时未连接' : 'Generation service is not connected'
                        : locale === 'zh-CN' ? '等待视觉输入' : 'Waiting for visual input'}
                </h2>
                <p className="mt-3 max-w-md text-xs leading-6 text-white/42">
                  {locale === 'zh-CN' ? '左侧会持续展示 Agent 的判断、澄清问题与确认动作；生成结果会在这里实时接替占位画面。' : 'The left panel keeps the conversation and approvals visible while generated visuals replace this canvas.'}
                </p>
              </div>
            )}
          </div>

          <div className="absolute inset-x-4 bottom-4 z-10 grid gap-2 rounded-2xl border border-white/10 bg-[#07101e]/78 p-3 shadow-2xl backdrop-blur-xl sm:grid-cols-3">
            {[
              { label: locale === 'zh-CN' ? '当前选择' : 'Selected output', value: selectedFaceLimit.toLocaleString(), detail: qualityTier === 'high' ? locale === 'zh-CN' ? '高模源文件 · 不自动减面' : 'High-poly source · no reduction' : locale === 'zh-CN' ? '游戏就绪版本' : 'Game-ready version', active: true },
              { label: locale === 'zh-CN' ? '高模源文件' : 'High-poly source', value: highFaceLimit.toLocaleString(), detail: locale === 'zh-CN' ? 'v3.1 Ultra · 默认' : 'v3.1 Ultra · default', active: qualityTier === 'high' },
              { label: locale === 'zh-CN' ? '游戏就绪' : 'Game-ready', value: '20,000', detail: locale === 'zh-CN' ? '可选低面版本' : 'Optional low-poly version', active: qualityTier === 'standard' },
            ].map(({ label, value, detail, active }) => (
              <div key={label} className={`rounded-xl border px-3 py-2.5 ${active ? 'border-cyan-200/24 bg-cyan-200/[0.065]' : 'border-white/7 bg-white/[0.035]'}`}>
                <p className="text-[9px] uppercase tracking-[0.12em] text-white/35">{label}</p>
                <p className="mt-1 font-mono text-lg font-semibold tracking-[-0.04em] text-white/88">{value}</p>
                <p className="mt-0.5 text-[9px] text-white/35">{detail}</p>
              </div>
            ))}
          </div>
        </section>
        ) : (
        <section
          className="preview-stage relative min-h-[680px] overflow-hidden text-white"
          onPointerMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            event.currentTarget.style.setProperty('--pointer-x', `${((event.clientX - bounds.left) / bounds.width) * 100}%`);
            event.currentTarget.style.setProperty('--pointer-y', `${((event.clientY - bounds.top) / bounds.height) * 100}%`);
          }}
          onPointerLeave={(event) => {
            event.currentTarget.style.setProperty('--pointer-x', '50%');
            event.currentTarget.style.setProperty('--pointer-y', '42%');
          }}
        >
          <div className="asset-grid absolute inset-0 opacity-50" />
          <div className="preview-aurora" aria-hidden="true" />
          <div className="preview-scan" aria-hidden="true" />
          <div className="absolute inset-x-0 top-0 z-10 flex h-14 items-center justify-between border-b border-white/8 bg-[#070b14]/40 px-5 backdrop-blur-md">
            <div>
              <p className="flex items-center gap-2 text-xs font-semibold">
                <span className="signal-dot" aria-hidden="true" />
                {t.preview}
              </p>
              <p className="mt-0.5 text-[10px] text-white/45">{t.previewHint}</p>
            </div>
            <div className="flex items-center gap-1">
              {canExportSelectedCandidate && generatedTask && selectedCandidate && (
                <Button
                  size="sm"
                  className="bg-cyan-300 text-[#071018] hover:bg-cyan-200"
                  render={
                    <a
                      href={getCandidateDownloadUrl(generatedTask.id, selectedCandidate.position)}
                      aria-label={locale === 'zh-CN' ? '导出 GLB' : 'Export GLB'}
                    />
                  }
                >
                  <Download />
                  {t.export}
                </Button>
              )}
              <span className="mr-2 hidden font-mono text-[9px] tracking-[0.14em] text-cyan-200/50 md:inline">
                LIVE SCENE · 81 NODES
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setWireframe((value) => !value)}
                aria-pressed={wireframe}
                className={
                  wireframe
                    ? 'bg-white/12 text-white hover:bg-white/16'
                    : 'text-white/60 hover:bg-white/8 hover:text-white'
                }
              >
                <Grid3X3 />
                {t.wireframe}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMaterialMode((value) => value === 'pbr' ? 'clay' : 'pbr')}
                aria-pressed={materialMode === 'clay'}
                className={materialMode === 'clay' ? 'bg-white/12 text-white hover:bg-white/16' : 'text-white/60 hover:bg-white/8 hover:text-white'}
              >
                <Layers3 />
                {materialMode === 'pbr' ? 'PBR' : locale === 'zh-CN' ? '黏土' : 'Clay'}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-white/60 hover:bg-white/8 hover:text-white"
                aria-label={locale === 'zh-CN' ? '重置相机' : 'Reset camera'}
                onClick={() => {
                  setCameraResetKey((value) => value + 1);
                  setNotice(locale === 'zh-CN' ? '相机视角已复位' : 'Camera view reset');
                }}
              >
                <RotateCcw />
              </Button>
            </div>
          </div>

          <div className="absolute inset-0 z-[2] flex items-center justify-center pt-4">
            <div className="relative size-full pt-12 pb-28">
              <AssetPreview
                key={cameraResetKey}
                wireframe={wireframe}
                materialMode={materialMode}
                modelUrl={provider === 'mock' ? undefined : selectedCandidate?.model_url}
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-28 z-10 text-center">
                <p className="text-sm font-medium">
                  {selectedCandidate
                    ? provider === 'mock'
                      ? `mock_candidate_A${selected}.glb`
                      : `generated_candidate_${selected}.glb`
                    : locale === 'zh-CN'
                      ? '示例资产 · 尚未生成'
                      : 'Sample asset · Not generated'}
                </p>
                <p className="mt-1 text-xs text-white/40">
                  {selectedCandidate ? metricValues[3] : locale === 'zh-CN' ? '用于预览交互' : 'Interaction preview'}
                </p>
              </div>
            </div>
          </div>

          <div className="absolute inset-x-4 bottom-4">
            <div className="preview-readout relative rounded-xl border border-white/10 p-2">
              {displayedCandidates.length > 0 ? (
                <div
                  className={`grid gap-2 ${
                    displayedCandidates.length === 1
                      ? 'grid-cols-1'
                      : displayedCandidates.length === 2
                        ? 'grid-cols-2'
                        : 'grid-cols-4'
                  }`}
                >
                  {displayedCandidates.map((candidate) => {
                    const visual = candidateVisuals[(candidate.position - 1) % candidateVisuals.length];
                    const candidateTriangles = candidate.metrics.triangle_count;
                    return (
                      <button
                        key={candidate.id}
                        onClick={() => setSelected(candidate.position)}
                        className={
                          'group relative overflow-hidden rounded-lg border p-2 text-left transition-all ' +
                          (selected === candidate.position
                            ? 'border-cyan-300/80 bg-cyan-300/10 shadow-[0_0_24px_rgba(68,220,231,.12)]'
                            : 'border-white/8 bg-white/4 hover:-translate-y-0.5 hover:border-cyan-200/30')
                        }
                      >
                        <div className={'mb-2 h-14 rounded-md bg-gradient-to-br opacity-70 ' + visual.tone}>
                          <div className="candidate-grid h-full w-full opacity-30" />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="max-w-[90px] truncate text-[11px] font-medium">
                            {candidate.asset_role === 'accessory'
                              ? candidate.asset_name
                              : locale === 'zh-CN' ? '人物主体' : 'Main asset'}
                          </span>
                          <span className="text-[10px] text-white/40">
                            {typeof candidateTriangles === 'number'
                              ? `${(candidateTriangles / 1000).toFixed(1)}K`
                              : candidate.state}
                          </span>
                        </div>
                        {selected === candidate.position && (
                          <span className="absolute right-2 top-2 grid size-5 place-items-center rounded-full bg-cyan-300 text-[#071018] shadow-[0_0_16px_rgba(103,232,238,.5)]">
                            <Check className="size-3" />
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="grid h-[94px] place-items-center rounded-lg border border-dashed border-white/10 text-center text-xs text-white/40">
                  {locale === 'zh-CN' ? '完成生成后，候选会显示在这里' : 'Generated candidates will appear here'}
                </div>
              )}
            </div>
          </div>
        </section>
        )}

        <aside className={`control-panel border-t border-border xl:border-l xl:border-t-0 ${workspaceView === 'generator' ? 'hidden' : ''}`}>
          <div className="flex h-12 items-center justify-between border-b border-border px-5">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              <span className="text-xs font-semibold">
                {selectedCandidate
                  ? `${t.selected} · A${selected}`
                  : locale === 'zh-CN'
                    ? '等待生成'
                    : 'Waiting for generation'}
              </span>
            </div>
            <Badge variant="secondary">
              {selectedCandidate ? t.version : locale === 'zh-CN' ? '未生成' : 'Not generated'}
            </Badge>
          </div>

          <div className="space-y-6 p-5">
            <section>
              <h2 className="mb-3 text-xs font-semibold">{t.metrics}</h2>
              <div className="grid grid-cols-2 gap-2">
                {metricValues.map((metric, index) => (
                  <div key={`${index}-${metric}`} className="rounded-lg border border-border bg-background/55 p-3">
                    <p className="text-xs font-semibold">{metric}</p>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <div className="mb-3 flex items-end justify-between">
                <div>
                  <h2 className="text-xs font-semibold">{t.qa}</h2>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {hasInspectedModel
                      ? generatedTask?.state === 'NEEDS_FIX'
                        ? locale === 'zh-CN' ? '检测完成：存在需要修复的指标' : 'Complete: fixes required'
                        : locale === 'zh-CN' ? '确定性检测已完成' : 'Deterministic QA complete'
                      : locale === 'zh-CN' ? '等待确定性 QA 检测结果' : 'Waiting for deterministic QA results'}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-semibold tracking-[-0.06em]">{qaScore ?? '--'}</span>
                  <span className="text-xs text-muted-foreground"> / 100</span>
                </div>
              </div>
              <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${qaScore ?? 0}%` }} />
              </div>
              <div className="space-y-1">
                {qaResults.map(([label, passed]) => (
                  <div key={label} className="flex items-center justify-between rounded-md px-1 py-2 text-xs">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      {hasInspectedModel
                        ? passed
                          ? <Check className="size-3.5 text-emerald-600" />
                          : <X className="size-3.5 text-red-600" />
                        : <LoaderCircle className="size-3.5 text-muted-foreground" />}
                      {label}
                    </span>
                    <span className={hasInspectedModel ? passed ? 'text-emerald-600' : 'text-red-600' : 'text-muted-foreground'}>
                      {hasInspectedModel ? passed ? 'PASS' : 'FAIL' : 'PENDING'}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {canExportSelectedCandidate && generatedTask && selectedCandidate ? (
              <Button
                className="h-10 w-full"
                render={
                  <a
                    href={getCandidateDownloadUrl(generatedTask.id, selectedCandidate.position)}
                    aria-label={locale === 'zh-CN' ? '导出 GLB' : 'Export GLB'}
                    aria-describedby="delivery-status"
                  />
                }
              >
                <Download />
                {t.export}
              </Button>
            ) : (
              <Button className="h-10 w-full" disabled aria-describedby="delivery-status">
                <Download />
                {t.export}
              </Button>
            )}
            <Button variant="outline" className="w-full" disabled aria-describedby="delivery-unavailable">
              <Play />
              Unity URP Mobile
            </Button>
            <p id="delivery-status" className="text-center text-[9px] leading-4 text-muted-foreground">
              {canExportSelectedCandidate
                ? locale === 'zh-CN'
                  ? 'GLB 已就绪，可直接下载；QA 警告不会隐藏已生成的原始文件。'
                  : 'The GLB is ready to download. QA warnings do not hide the generated source file.'
                : locale === 'zh-CN'
                  ? '完成一个有效候选后即可导出 GLB。'
                  : 'Export unlocks when a valid candidate is ready.'}
            </p>
            <p id="delivery-unavailable" className="text-center text-[9px] leading-4 text-muted-foreground">
              {locale === 'zh-CN'
                ? 'Unity 自动接入仍处于未开放状态。'
                : 'Automatic Unity handoff is not available yet.'}
            </p>
          </div>
        </aside>
      </div>
      )}
      <WorkspaceMenuSheet
        open={menuOpen}
        onOpenChange={setMenuOpen}
        locale={locale}
        activeView={workspaceView}
        onNavigate={navigateWorkspace}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenHelp={() => setHelpOpen(true)}
      />
      <HelpCenterDialog
        open={helpOpen}
        onOpenChange={setHelpOpen}
        locale={locale}
        onOpenTasks={() => navigateWorkspace('tasks')}
      />
      <ProjectSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        locale={locale}
        qualityTier={qualityTier}
        highFaceLimit={highFaceLimit}
        onQualityTierChange={setQualityTier}
        onSave={() => setNotice(locale === 'zh-CN' ? '项目规格已保存' : 'Project spec saved')}
      />
      {notice && (
        <output className="fixed bottom-5 left-1/2 z-[70] -translate-x-1/2 rounded-full border border-cyan-300/20 bg-[#0b1424]/95 px-4 py-2 text-xs text-cyan-100 shadow-[0_16px_50px_rgba(0,0,0,.45)] backdrop-blur-xl">
          {notice}
        </output>
      )}
      {lightboxImage && (
        <dialog
          open
          className="fixed inset-0 z-50 grid place-items-center bg-black/90 p-4"
          aria-modal="true"
          aria-label={locale === 'zh-CN' ? '参考图大图' : 'Full-size reference'}
        >
          <button
            type="button"
            onClick={() => setLightboxImage(null)}
            className="absolute right-5 top-5 grid size-10 place-items-center rounded-full bg-white/10 text-white hover:bg-white/20"
            aria-label={locale === 'zh-CN' ? '关闭' : 'Close'}
          >
            <X />
          </button>
          <div className="relative h-[82vh] w-[92vw]">
            <Image
              src={lightboxImage.preview_url}
              alt={lightboxImage.original_name}
              fill
              unoptimized
              priority
              className="object-contain"
            />
          </div>
          <a
            href={lightboxImage.preview_url}
            target="_blank"
            rel="noreferrer"
            className="absolute bottom-5 rounded-lg bg-white px-4 py-2 text-xs font-semibold text-black"
          >
            {locale === 'zh-CN' ? '在新窗口打开原图' : 'Open original'}
          </a>
        </dialog>
      )}
    </main>
  );
}
