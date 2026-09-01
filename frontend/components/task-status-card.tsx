import { CircleStop, LoaderCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { GenerationTask } from '@/lib/api';
import { taskStateLabel } from '@/lib/task-state';

type TaskStatusCardProps = {
  task: GenerationTask;
  locale: 'zh-CN' | 'en';
  connection: 'idle' | 'live' | 'polling' | 'disconnected';
  cancelling: boolean;
  onCancel: () => void;
};

export function TaskStatusCard({
  task,
  locale,
  connection,
  cancelling,
  onCancel,
}: TaskStatusCardProps) {
  const stages = ['QUEUED', 'GEOMETRY', 'TEXTURING', 'QA'];
  const activeStage = task.state === 'QA'
    ? 3
    : task.state === 'TEXTURING' || task.state === 'POST_PROCESSING'
      ? 2
      : task.state === 'PREPROCESSING' || task.state === 'GEOMETRY'
        ? 1
        : 0;

  return (
    <div
      className="task-signal-card rounded-lg border border-cyan-400/20 bg-cyan-400/6 p-3"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-[11px] font-semibold text-cyan-200">
            <span className="signal-dot" aria-hidden="true" />
            {taskStateLabel(task.state, locale)}
          </p>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
            {connection === 'live'
              ? locale === 'zh-CN'
                ? '实时接收任务阶段和候选；离开页面不会停止后端任务。'
                : 'Receiving live stages and candidates. Leaving does not stop the backend task.'
              : locale === 'zh-CN'
                ? '实时连接不可用，正在通过状态查询恢复。'
                : 'Live connection is unavailable; recovering through status checks.'}
          </p>
          <p className="mt-1 truncate font-mono text-[9px] text-muted-foreground/70">
            {task.id}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={cancelling}
          onClick={onCancel}
        >
          {cancelling ? <LoaderCircle className="animate-spin" /> : <CircleStop />}
          {locale === 'zh-CN' ? '取消任务' : 'Cancel'}
        </Button>
      </div>
      <progress
        className="sr-only"
        aria-label={locale === 'zh-CN' ? '生成阶段进度' : 'Generation stage progress'}
        max={4}
        value={activeStage + 1}
      />
      <div
        className="mt-3 grid grid-cols-4 gap-1"
        aria-hidden="true"
      >
        {stages.map((stage, index) => (
          <span
            key={stage}
            aria-hidden="true"
            className={`h-0.5 rounded-full transition-colors duration-500 ${
              index <= activeStage ? 'bg-cyan-300' : 'bg-white/10'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
