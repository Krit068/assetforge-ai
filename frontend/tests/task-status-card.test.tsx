import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TaskStatusCard } from '@/components/task-status-card';
import type { GenerationTask } from '@/lib/api';

const task: GenerationTask = {
  id: 'task-alpha-001',
  state: 'GEOMETRY',
  asset_type: 'prop',
  provider: 'mock',
  diagnostic_id: 'diag-001',
  error_code: null,
  error_message: null,
  concept_bundle_id: null,
  reference_files: [],
  accessory_reference_files: [],
  candidates: [],
};

describe('TaskStatusCard', () => {
  it('shows the real backend stage and exposes real cancellation', () => {
    const onCancel = vi.fn();
    render(
      <TaskStatusCard
        task={task}
        locale="zh-CN"
        connection="live"
        cancelling={false}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByText('正在生成几何')).toBeInTheDocument();
    expect(screen.getByText('task-alpha-001')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: '生成阶段进度' })).toHaveAttribute('value', '2');
    fireEvent.click(screen.getByRole('button', { name: '取消任务' }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('explains polling recovery instead of claiming the task failed', () => {
    render(
      <TaskStatusCard
        task={{ ...task, state: 'TEXTURING' }}
        locale="en"
        connection="polling"
        cancelling={false}
        onCancel={() => undefined}
      />,
    );

    expect(screen.getByText('Generating textures')).toBeInTheDocument();
    expect(screen.getByText(/recovering through status checks/i)).toBeInTheDocument();
  });
});
