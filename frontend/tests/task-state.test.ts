import { describe, expect, it } from 'vitest';

import { isTerminalTaskState, mapTaskState, taskStateLabel } from '@/lib/task-state';

describe('task state mapping', () => {
  it.each([
    ['DRAFT', 'submitting'],
    ['VALIDATING', 'submitting'],
    ['QUEUED', 'queued'],
    ['GEOMETRY', 'running'],
    ['TEXTURING', 'running'],
    ['QA', 'running'],
    ['READY', 'succeeded'],
    ['NEEDS_FIX', 'partially_succeeded'],
    ['FAILED', 'failed'],
    ['CANCELLED', 'cancelled'],
    ['NEW_PROVIDER_STATE', 'stale'],
  ])('maps %s to %s', (backendState, expected) => {
    expect(mapTaskState(backendState)).toBe(expected);
  });

  it('only treats backend terminal states as terminal', () => {
    expect(isTerminalTaskState('READY')).toBe(true);
    expect(isTerminalTaskState('NEEDS_FIX')).toBe(true);
    expect(isTerminalTaskState('FAILED')).toBe(true);
    expect(isTerminalTaskState('CANCELLED')).toBe(true);
    expect(isTerminalTaskState('QA')).toBe(false);
  });

  it('uses a safe label for unknown states', () => {
    expect(taskStateLabel('UNKNOWN_PROVIDER_STATE', 'zh-CN')).toBe('正在同步状态');
    expect(taskStateLabel('UNKNOWN_PROVIDER_STATE', 'en')).toBe('Syncing status');
  });
});

