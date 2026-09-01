'use client';

import { useMemo, useState } from 'react';
import {
  Boxes,
  CircleHelp,
  Cpu,
  FolderClock,
  Grid3X3,
  Keyboard,
  LifeBuoy,
  Menu,
  Search,
  Settings2,
  Sparkles,
  WandSparkles,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

export type WorkspaceView = 'generator' | 'tasks' | 'assets';

type MenuSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  locale: 'zh-CN' | 'en';
  activeView: WorkspaceView;
  onNavigate: (view: WorkspaceView) => void;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
};

export function WorkspaceMenuSheet({
  open,
  onOpenChange,
  locale,
  activeView,
  onNavigate,
  onOpenSettings,
  onOpenHelp,
}: MenuSheetProps) {
  const entries: Array<{ id: WorkspaceView; label: string; icon: typeof WandSparkles }> = [
    { id: 'generator', label: locale === 'zh-CN' ? '生成器' : 'Generator', icon: WandSparkles },
    { id: 'tasks', label: locale === 'zh-CN' ? '任务中心' : 'Task center', icon: FolderClock },
    { id: 'assets', label: locale === 'zh-CN' ? '资产库' : 'Asset library', icon: Boxes },
  ];

  const navigate = (view: WorkspaceView) => {
    onNavigate(view);
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="border-cyan-300/10 bg-[#0a1020]/96 backdrop-blur-xl" data-testid="workspace-menu">
        <SheetHeader className="border-b border-border px-5 py-5">
          <SheetTitle className="flex items-center gap-2"><Menu className="size-4 text-primary" />AssetForge</SheetTitle>
          <SheetDescription>{locale === 'zh-CN' ? '第二阶段 AI 资产生产工作台' : 'Stage 02 AI asset production workbench'}</SheetDescription>
        </SheetHeader>
        <nav className="space-y-1 px-3" aria-label={locale === 'zh-CN' ? '主菜单' : 'Main menu'}>
          {entries.map((entry) => {
            const Icon = entry.icon;
            return (
              <button
                key={entry.id}
                type="button"
                onClick={() => navigate(entry.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition-colors ${activeView === entry.id ? 'bg-primary/12 text-primary' : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'}`}
              >
                <Icon className="size-4" />
                {entry.label}
              </button>
            );
          })}
        </nav>
        <div className="mt-4 border-t border-border px-3 pt-4">
          <button type="button" onClick={() => { onOpenSettings(); onOpenChange(false); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground">
            <Settings2 className="size-4" />
            {locale === 'zh-CN' ? '项目规格' : 'Project spec'}
          </button>
          <button type="button" onClick={() => { onOpenHelp(); onOpenChange(false); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground">
            <CircleHelp className="size-4" />
            {locale === 'zh-CN' ? '帮助中心' : 'Help center'}
          </button>
        </div>
        <div className="mx-4 mt-auto mb-5 rounded-xl border border-cyan-300/10 bg-cyan-300/5 p-3">
          <p className="font-mono text-[9px] tracking-[0.14em] text-cyan-200/70">SYSTEM ONLINE</p>
          <p className="mt-1 text-[10px] leading-4 text-muted-foreground">High-poly source · Game-ready option · Y Up</p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

type HelpCenterDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  locale: 'zh-CN' | 'en';
  onOpenTasks: () => void;
};

export function HelpCenterDialog({ open, onOpenChange, locale, onOpenTasks }: HelpCenterDialogProps) {
  const [query, setQuery] = useState('');
  const topics = useMemo(() => [
    {
      icon: WandSparkles,
      title: locale === 'zh-CN' ? '如何生成资产？' : 'How do I generate an asset?',
      body: locale === 'zh-CN' ? '输入清晰描述，确认概念图和费用，再提交 3D。任务进入后台后可以安全离开页面。' : 'Describe the asset, approve the concept and cost, then submit 3D. You can safely leave after the task starts.',
    },
    {
      icon: FolderClock,
      title: locale === 'zh-CN' ? '任务断线怎么办？' : 'What if the task disconnects?',
      body: locale === 'zh-CN' ? '打开任务中心并选择对应任务。系统会按任务 ID 查询真实状态，不会自动重复付费。' : 'Open Task center and select the task. Status is recovered by task ID without an automatic paid retry.',
    },
    {
      icon: Grid3X3,
      title: locale === 'zh-CN' ? '如何检查模型？' : 'How do I inspect a model?',
      body: locale === 'zh-CN' ? '拖动预览旋转，滚轮缩放；使用线框、材质模式和技术 QA 检查面数与结构。' : 'Drag to orbit, scroll to zoom, and use wireframe, material mode, and technical QA.',
    },
    {
      icon: Keyboard,
      title: locale === 'zh-CN' ? '快捷操作' : 'Keyboard shortcuts',
      body: locale === 'zh-CN' ? 'W 切换线框；Esc 关闭帮助、菜单和大图；刷新页面会从 URL 恢复当前任务。' : 'W toggles wireframe; Esc closes overlays; refresh restores the current task from its URL.',
    },
  ], [locale]);
  const normalized = query.trim().toLowerCase();
  const filtered = topics.filter((topic) => !normalized || `${topic.title} ${topic.body}`.toLowerCase().includes(normalized));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[86vh] overflow-y-auto border border-cyan-300/10 bg-[#0b1222] sm:max-w-xl" data-testid="help-center">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><LifeBuoy className="size-4 text-primary" />{locale === 'zh-CN' ? '帮助中心' : 'Help center'}</DialogTitle>
          <DialogDescription>{locale === 'zh-CN' ? '搜索当前 Alpha 工作流、任务恢复和模型检查说明。' : 'Search the Alpha workflow, task recovery, and model inspection guide.'}</DialogDescription>
        </DialogHeader>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === 'zh-CN' ? '搜索帮助…' : 'Search help…'} className="pl-9" />
        </div>
        <div className="space-y-2">
          {filtered.length ? filtered.map((topic) => {
            const Icon = topic.icon;
            return (
              <article key={topic.title} className="rounded-xl border border-border bg-background/45 p-3">
                <h3 className="flex items-center gap-2 text-xs font-semibold"><Icon className="size-3.5 text-primary" />{topic.title}</h3>
                <p className="mt-2 text-[11px] leading-5 text-muted-foreground">{topic.body}</p>
              </article>
            );
          }) : (
            <div className="rounded-xl border border-dashed border-border p-5 text-center text-xs text-muted-foreground">{locale === 'zh-CN' ? '没有匹配的帮助内容' : 'No matching help topics'}</div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { onOpenTasks(); onOpenChange(false); }}><FolderClock />{locale === 'zh-CN' ? '查看任务中心' : 'Open task center'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

type ProjectSettingsDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  locale: 'zh-CN' | 'en';
  qualityTier: 'standard' | 'high';
  highFaceLimit: number;
  onQualityTierChange: (tier: 'standard' | 'high') => void;
  onSave: () => void;
};

export function ProjectSettingsDialog({ open, onOpenChange, locale, qualityTier, highFaceLimit, onQualityTierChange, onSave }: ProjectSettingsDialogProps) {
  const faceLimit = qualityTier === 'high' ? highFaceLimit : 20_000;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border border-cyan-300/10 bg-[#0b1222] sm:max-w-lg" data-testid="project-settings">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Cpu className="size-4 text-primary" />{locale === 'zh-CN' ? '项目规格' : 'Project spec'}</DialogTitle>
          <DialogDescription>Unity URP Mobile</DialogDescription>
        </DialogHeader>
        <dl className="divide-y divide-border rounded-xl border border-border bg-background/45 px-3 text-xs">
          {[
            [locale === 'zh-CN' ? '几何面数上限' : 'Face limit', faceLimit.toLocaleString()],
            [locale === 'zh-CN' ? '坐标轴' : 'Axis', 'Y Up · Z Forward'],
            [locale === 'zh-CN' ? '纹理工作流' : 'Texture workflow', qualityTier === 'high' ? 'Extreme PBR' : 'Detailed PBR'],
            [locale === 'zh-CN' ? '交付用途' : 'Delivery use', qualityTier === 'high' ? (locale === 'zh-CN' ? '高模源文件 / 烘焙' : 'Source / baking') : 'Unity Mobile'],
          ].map(([label, value]) => <div key={label} className="flex items-center justify-between py-3"><dt className="text-muted-foreground">{label}</dt><dd className="font-medium">{value}</dd></div>)}
        </dl>
        <div>
          <p className="mb-2 text-xs font-semibold">{locale === 'zh-CN' ? '生成质量' : 'Generation quality'}</p>
          <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={locale === 'zh-CN' ? '生成质量' : 'Generation quality'}>
            {(['high', 'standard'] as const).map((tier) => (
              <label key={tier} className={`cursor-pointer rounded-xl border p-3 text-left transition-colors ${qualityTier === tier ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-background/35 text-muted-foreground hover:border-primary/30'}`}>
                <input type="radio" name="settings-quality" value={tier} checked={qualityTier === tier} onChange={() => onQualityTierChange(tier)} className="sr-only" />
                <Sparkles className="mb-2 size-4" />
                <span className="block text-xs font-semibold">{tier === 'high' ? (locale === 'zh-CN' ? '高模源文件（默认）' : 'High-poly source (default)') : (locale === 'zh-CN' ? '游戏就绪' : 'Game-ready')}</span>
                <span className="mt-1 block text-[9px]">{tier === 'high' ? `v3.1 Ultra · ${highFaceLimit.toLocaleString()} faces · no reduction` : 'P1 · 20,000 faces'}</span>
              </label>
            ))}
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => { onSave(); onOpenChange(false); }}><Settings2 />{locale === 'zh-CN' ? '保存规格' : 'Save spec'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
