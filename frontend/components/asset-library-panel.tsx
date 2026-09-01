import { Box, Cuboid, ExternalLink } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { GenerationTask } from '@/lib/api';

type AssetLibraryPanelProps = {
  tasks: GenerationTask[];
  locale: 'zh-CN' | 'en';
  onOpenAsset: (task: GenerationTask, position: number) => void;
  onStart: () => void;
};

export function AssetLibraryPanel({ tasks, locale, onOpenAsset, onStart }: AssetLibraryPanelProps) {
  const assets = tasks.flatMap((task) => task.candidates.map((candidate) => ({ task, candidate })));

  return (
    <div className="space-y-4 p-5" data-testid="asset-library-panel">
      <div>
        <h2 className="text-sm font-semibold">{locale === 'zh-CN' ? '资产库' : 'Asset library'}</h2>
        <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
          {locale === 'zh-CN' ? '来自已持久化任务的候选资产；打开后可继续预览和 QA。' : 'Candidates from persisted tasks, ready for preview and QA.'}
        </p>
      </div>

      {assets.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-background/35 p-5 text-center">
          <Cuboid className="mx-auto size-6 text-muted-foreground" />
          <p className="mt-3 text-xs font-semibold">{locale === 'zh-CN' ? '资产库还是空的' : 'Your asset library is empty'}</p>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">
            {locale === 'zh-CN' ? '完成一次生成后，候选会自动出现在这里。' : 'Candidates appear here after a generation finishes.'}
          </p>
          <Button className="mt-4 h-8" onClick={onStart}>{locale === 'zh-CN' ? '创建资产' : 'Create asset'}</Button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {assets.map(({ task, candidate }, index) => {
            const triangles = candidate.metrics.triangle_count;
            return (
              <article key={candidate.id} className="group overflow-hidden rounded-xl border border-border bg-background/45">
                <div className={`relative grid h-24 place-items-center bg-gradient-to-br ${index % 2 ? 'from-violet-950 via-blue-900 to-cyan-700' : 'from-slate-950 via-cyan-950 to-cyan-600'}`}>
                  <div className="candidate-grid absolute inset-0 opacity-20" />
                  <Box className="relative size-7 text-white/70 transition-transform group-hover:-translate-y-1 group-hover:rotate-6" />
                </div>
                <div className="p-2.5">
                  <p className="truncate text-[11px] font-semibold">
                    {candidate.asset_name || `${locale === 'zh-CN' ? '候选' : 'Candidate'} A${candidate.position}`}
                  </p>
                  <p className="mt-1 text-[9px] text-muted-foreground">
                    {typeof triangles === 'number' ? `${Number(triangles).toLocaleString()} tris` : candidate.state}
                  </p>
                  <Button variant="ghost" size="sm" className="mt-2 w-full" onClick={() => onOpenAsset(task, candidate.position)}>
                    <ExternalLink />
                    {locale === 'zh-CN' ? '打开' : 'Open'}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
