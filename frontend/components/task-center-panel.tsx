import { CircleStop, Clock3, LoaderCircle, RefreshCw, RotateCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { GenerationTask } from '@/lib/api';
import { isTerminalTaskState, taskStateLabel } from '@/lib/task-state';

type TaskCenterPanelProps = {
  tasks: GenerationTask[];
  locale: 'zh-CN' | 'en';
  loading: boolean;
  error: string;
  cancellingTaskId: string | null;
  onRefresh: () => void;
  onOpenTask: (task: GenerationTask) => void;
  onCancelTask: (task: GenerationTask) => void;
  onStart: () => void;
};

export function TaskCenterPanel({
  tasks,
  locale,
  loading,
  error,
  cancellingTaskId,
  onRefresh,
  onOpenTask,
  onCancelTask,
  onStart,
}: TaskCenterPanelProps) {
  return (
    <div className="space-y-4 p-5" data-testid="task-center-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{locale === 'zh-CN' ? '任务中心' : 'Task center'}</h2>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
            {locale === 'zh-CN' ? '查看、恢复或取消最近 20 个真实任务。' : 'Inspect, recover, or cancel the latest 20 real tasks.'}
          </p>
        </div>
        <Button variant="outline" size="icon-sm" onClick={onRefresh} aria-label={locale === 'zh-CN' ? '刷新任务' : 'Refresh tasks'}>
          <RefreshCw className={loading ? 'animate-spin' : ''} />
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-400/20 bg-amber-400/7 px-3 py-2 text-[10px] leading-4 text-amber-200">
          {error}
        </div>
      )}

      {loading && tasks.length === 0 ? (
        <div className="grid min-h-48 place-items-center rounded-xl border border-border bg-background/40 text-xs text-muted-foreground">
          <LoaderCircle className="mb-2 size-5 animate-spin text-primary" />
          {locale === 'zh-CN' ? '正在同步任务…' : 'Syncing tasks…'}
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-background/35 p-5 text-center">
          <Clock3 className="mx-auto size-6 text-muted-foreground" />
          <p className="mt-3 text-xs font-semibold">{locale === 'zh-CN' ? '还没有生成任务' : 'No generation tasks yet'}</p>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
            {locale === 'zh-CN' ? '创建首个任务后，可以在这里恢复进度。' : 'Create your first task to recover it here later.'}
          </p>
          <Button className="mt-4 h-8" onClick={onStart}>{locale === 'zh-CN' ? '开始生成' : 'Start generating'}</Button>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((task, index) => (
            <article key={task.id} className="rounded-xl border border-border bg-background/45 p-3 transition-colors hover:border-primary/25">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold">
                    {task.original_prompt?.trim() || (task.asset_type === 'character' ? (locale === 'zh-CN' ? '角色资产' : 'Character asset') : (locale === 'zh-CN' ? '道具资产' : 'Prop asset'))}
                  </p>
                  <p className="mt-1 truncate font-mono text-[9px] text-muted-foreground">{task.id}</p>
                </div>
                <span className="shrink-0 rounded-full border border-cyan-300/15 bg-cyan-300/6 px-2 py-1 text-[9px] font-medium text-cyan-200">
                  {taskStateLabel(task.state, locale)}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground">
                <span>#{String(index + 1).padStart(2, '0')} · {task.candidates.length} {locale === 'zh-CN' ? '个候选' : 'candidates'}</span>
                <span>{task.provider}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" onClick={() => onOpenTask(task)}>
                  <RotateCcw />
                  {locale === 'zh-CN' ? '打开任务' : 'Open task'}
                </Button>
                {!isTerminalTaskState(task.state) ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={cancellingTaskId === task.id}
                    onClick={() => onCancelTask(task)}
                  >
                    {cancellingTaskId === task.id ? <LoaderCircle className="animate-spin" /> : <CircleStop />}
                    {locale === 'zh-CN' ? '取消' : 'Cancel'}
                  </Button>
                ) : (
                  <div className="grid place-items-center rounded-lg border border-border text-[10px] text-muted-foreground">
                    {locale === 'zh-CN' ? '任务已结束' : 'Task complete'}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
