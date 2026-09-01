export type TaskUiState =
  | 'submitting'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'partially_succeeded'
  | 'failed'
  | 'cancelled'
  | 'stale';

const TERMINAL_STATES = new Set(['READY', 'NEEDS_FIX', 'FAILED', 'CANCELLED']);

export function isTerminalTaskState(state: string): boolean {
  return TERMINAL_STATES.has(state);
}

export function mapTaskState(state: string): TaskUiState {
  switch (state) {
    case 'DRAFT':
    case 'VALIDATING':
      return 'submitting';
    case 'QUEUED':
      return 'queued';
    case 'PREPROCESSING':
    case 'GEOMETRY':
    case 'TEXTURING':
    case 'POST_PROCESSING':
    case 'QA':
      return 'running';
    case 'READY':
      return 'succeeded';
    case 'NEEDS_FIX':
      return 'partially_succeeded';
    case 'FAILED':
      return 'failed';
    case 'CANCELLED':
      return 'cancelled';
    default:
      return 'stale';
  }
}

const labels = {
  'zh-CN': {
    DRAFT: '准备提交',
    VALIDATING: '正在校验',
    QUEUED: '已进入队列',
    PREPROCESSING: '正在预处理',
    GEOMETRY: '正在生成几何',
    TEXTURING: '正在生成材质',
    POST_PROCESSING: '正在优化模型',
    QA: '正在执行技术 QA',
    READY: '可以导出',
    NEEDS_FIX: '需要修复',
    FAILED: '生成失败',
    CANCELLED: '已取消',
    UNKNOWN: '正在同步状态',
  },
  en: {
    DRAFT: 'Preparing',
    VALIDATING: 'Validating',
    QUEUED: 'Queued',
    PREPROCESSING: 'Preprocessing',
    GEOMETRY: 'Generating geometry',
    TEXTURING: 'Generating textures',
    POST_PROCESSING: 'Optimizing model',
    QA: 'Running technical QA',
    READY: 'Ready to export',
    NEEDS_FIX: 'Fixes required',
    FAILED: 'Generation failed',
    CANCELLED: 'Cancelled',
    UNKNOWN: 'Syncing status',
  },
} as const;

export function taskStateLabel(state: string, locale: 'zh-CN' | 'en'): string {
  const dictionary = labels[locale] as Record<string, string>;
  return dictionary[state] ?? dictionary.UNKNOWN;
}

