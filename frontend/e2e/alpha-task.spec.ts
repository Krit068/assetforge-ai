import { expect, type Page, test } from '@playwright/test';

async function mockAlphaApi(page: Page) {
  let createdTask: Record<string, unknown> | null = null;
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const json = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (pathname.endsWith('/capabilities')) {
      await json({
        data: {
          provider: 'mock',
          candidate_counts: [1, 2, 4],
          quality_profiles: [
            { id: 'high', label: 'high_poly_source', face_limit: 2_000_000, default: true },
            { id: 'standard', label: 'game_ready', face_limit: 20_000, default: false },
          ],
        },
      });
      return;
    }
    if (pathname.endsWith('/concept-images/latest')) {
      await json({ error: { code: 'CONCEPT_NOT_FOUND', message: 'Not found' } }, 404);
      return;
    }
    if (pathname.endsWith('/generation-tasks/latest')) {
      await json({ error: { code: 'TASK_NOT_FOUND', message: 'Not found' } }, 404);
      return;
    }
    if (pathname.endsWith('/generation-tasks') && request.method() === 'GET') {
      await json({ data: createdTask ? [createdTask] : [] });
      return;
    }
    if (pathname.endsWith('/prompts/analyze')) {
      await json({
        data: {
          ready_to_generate: true,
          clarity_score: 100,
          detected_asset_type: 'prop',
          clarifying_questions: [],
          detected_accessories: [],
          concept_image_count: 1,
        },
      });
      return;
    }
    if (pathname.endsWith('/projects') && request.method() === 'GET') {
      await json({ data: [] });
      return;
    }
    if (pathname.endsWith('/projects') && request.method() === 'POST') {
      await json({
        data: {
          id: 'project-alpha',
          name: 'Unity URP Mobile',
          engine: 'unity',
          platform: 'mobile',
          locale: 'zh-CN',
          spec_profile: { template: 'unity_urp_mobile' },
        },
      }, 201);
      return;
    }
    if (pathname.endsWith('/generation-tasks') && request.method() === 'POST') {
      createdTask = {
        id: 'task-alpha-e2e',
        state: 'READY',
        asset_type: 'prop',
        provider: 'mock',
        diagnostic_id: 'diag-alpha-e2e',
        error_code: null,
        error_message: null,
        concept_bundle_id: null,
        reference_files: [],
        accessory_reference_files: [],
        candidates: [1, 2, 3, 4].map((position) => ({
          id: `candidate-${position}`,
          position,
          asset_role: 'main',
          asset_name: null,
          state: 'ready',
          model_url: `http://localhost:8010/assets/generated/task-alpha-e2e/candidate-${position}.glb`,
          preview_url: null,
          metrics: { triangle_count: 7600 + position * 400 },
          error_code: null,
        })),
      };
      await json({ data: createdTask }, 202);
      return;
    }
    if (pathname.endsWith('/generation-tasks/task-alpha-e2e/candidates/1/download')) {
      await route.fulfill({
        status: 200,
        contentType: 'model/gltf-binary',
        headers: {
          'Content-Disposition': 'attachment; filename="assetforge-task-alp-candidate-1.glb"',
        },
        body: Buffer.from('glTF-browser-export-test'),
      });
      return;
    }
    if (pathname.endsWith('/generation-tasks/task-alpha-e2e') && createdTask) {
      await json({ data: createdTask });
      return;
    }

    await json({ error: { code: 'NOT_FOUND', message: 'Not found' } }, 404);
  });
}

test('language preference survives refresh without losing the workbench', async ({ page }) => {
  await mockAlphaApi(page);
  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');
  await expect(page.getByText('AssetForge', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Forge your idea into a game-ready asset' })).toBeVisible();

  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');
  await expect(page.getByRole('heading', { name: 'Forge your idea into a game-ready asset' })).toBeVisible();
});

test('root opens the redesigned generator instead of restoring the latest historical task', async ({ page }) => {
  await mockAlphaApi(page);
  await page.route('**/api/v1/generation-tasks/latest', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 'historical-task',
          state: 'READY',
          asset_type: 'prop',
          provider: 'mock',
          diagnostic_id: 'historical-diagnostic',
          error_code: null,
          error_message: null,
          concept_bundle_id: null,
          reference_files: [],
          accessory_reference_files: [],
          candidates: [],
        },
      }),
    });
  });

  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');

  await expect(page).not.toHaveURL(/\?task=/);
  await expect(page.getByRole('heading', { name: '把你的想法，锻造成游戏资产' })).toBeVisible();
});

test('historical task references are informational instead of failed quality checks', async ({ page }) => {
  await mockAlphaApi(page);
  await page.route('**/api/v1/generation-tasks/historical-task', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: 'historical-task',
          state: 'READY',
          asset_type: 'prop',
          provider: 'mock',
          diagnostic_id: 'historical-diagnostic',
          error_code: null,
          error_message: null,
          concept_bundle_id: null,
          reference_files: [{
            id: 'historical-reference',
            original_name: 'historical.png',
            mime_type: 'image/png',
            size_bytes: 68,
            width: 256,
            height: 256,
            preview_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
          }],
          accessory_reference_files: [],
          candidates: [],
        },
      }),
    });
  });

  await page.goto('/?task=historical-task');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');

  await expect(page.getByText('历史任务参考图')).toBeVisible();
  await expect(page.getByText('参考图未通过建模检查')).toHaveCount(0);
  await expect(page.getByRole('button', { name: '确认概念并生成 3D' })).toHaveCount(0);
});

test('tech preview reacts to the pointer and stays within a mobile viewport', async ({ page }) => {
  await mockAlphaApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');

  await page.getByRole('textbox', { name: '描述你想生成的资产' }).fill('移动端科幻补给箱');
  await page.getByRole('button', { name: '发送并开始生成' }).click();
  await page.getByRole('button', { name: '确认并开始生成' }).click();

  const preview = page.locator('.preview-stage');
  await preview.scrollIntoViewIfNeeded();
  await preview.hover({ position: { x: 300, y: 180 } });
  await expect(preview).toHaveCSS('--pointer-y', /\d+(\.\d+)?%/);

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test('navigation, help, settings, material, and camera controls are interactive', async ({ page }) => {
  await mockAlphaApi(page);
  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');

  await expect(page.getByText('青铜遗迹')).toHaveCount(0);
  await page.getByRole('button', { name: '打开菜单' }).click();
  await expect(page.getByTestId('workspace-menu')).toBeVisible();
  await page.getByTestId('workspace-menu').getByRole('button', { name: '任务中心' }).click();
  await expect(page.getByTestId('task-center-panel')).toBeVisible();

  await page.getByRole('main').getByRole('button', { name: '资产库', exact: true }).click();
  await expect(page.getByTestId('asset-library-panel')).toBeVisible();

  await page.getByRole('button', { name: '打开帮助中心' }).click();
  await expect(page.getByTestId('help-center')).toBeVisible();
  await page.getByPlaceholder('搜索帮助…').fill('断线');
  await expect(page.getByText('任务断线怎么办？')).toBeVisible();
  await page.keyboard.press('Escape');

  await page.getByRole('button', { name: '打开项目规格' }).click();
  await expect(page.getByTestId('project-settings')).toBeVisible();
  await expect(page.getByRole('radio', { name: /高模源文件.*默认/ })).toBeChecked();
  await page.getByText('游戏就绪', { exact: true }).click();
  await expect(page.getByRole('radio', { name: '游戏就绪' })).toBeChecked();
  await page.getByRole('button', { name: '保存规格' }).click();
  await expect(page.getByRole('status')).toHaveText('项目规格已保存');

  await page.getByRole('main').getByRole('button', { name: '生成器', exact: true }).click();
  await page.getByRole('textbox', { name: '描述你想生成的资产' }).fill('移动端科幻无人机');
  await page.getByRole('button', { name: '发送并开始生成' }).click();
  await page.getByRole('button', { name: '确认并开始生成' }).click();

  await page.getByRole('button', { name: 'PBR' }).click();
  await expect(page.getByRole('button', { name: '黏土' })).toBeVisible();
  await page.getByRole('button', { name: '重置相机' }).click();
  await expect(page.getByRole('status')).toHaveText('相机视角已复位');
});

test('mock generation creates a recoverable task URL and candidates', async ({ page }) => {
  await mockAlphaApi(page);
  await page.goto('/');
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');
  const chineseToggle = page.getByRole('button', { name: /中文/ });
  if (await chineseToggle.isVisible()) await chineseToggle.click();

  await page.getByRole('textbox', { name: '描述你想生成的资产' }).fill('低多边形古代机关宝箱');
  await page.getByRole('button', { name: '发送并开始生成' }).click();
  await page.getByRole('button', { name: '确认并开始生成' }).click();

  await expect(page).toHaveURL(/\?task=[^&]+/);
  await expect(page.getByText('模拟任务已完成')).toBeVisible();
  await expect(page.getByRole('button', { name: /人物主体/ })).toHaveCount(4);
  await expect(page.getByRole('button', { name: /任务已结束，请点击“新建”后再生成/ })).toBeDisabled();

  const exportButton = page.getByRole('link', { name: '导出 GLB' });
  await expect(exportButton).toBeVisible();
  const downloadStarted = page.waitForEvent('download');
  await exportButton.click();
  const download = await downloadStarted;
  expect(download.suggestedFilename()).toBe('assetforge-task-alp-candidate-1.glb');

  await page.getByRole('main').getByRole('button', { name: '任务中心', exact: true }).click();
  await expect(page.getByTestId('task-center-panel').getByText('task-alpha-e2e')).toBeVisible();
  await page.getByTestId('task-center-panel').getByRole('button', { name: '打开任务' }).click();

  await page.getByRole('main').getByRole('button', { name: '资产库', exact: true }).click();
  await expect(page.getByTestId('asset-library-panel').getByRole('button', { name: '打开' })).toHaveCount(4);
  await page.getByTestId('asset-library-panel').getByRole('button', { name: '打开' }).first().click();
  await expect(page.getByText('继续补充或修改需求')).toBeVisible();

  const taskUrl = page.url();
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.appReady === 'true');
  await expect(page).toHaveURL(taskUrl);
  await expect(page.getByText('模拟任务已完成')).toBeVisible();
});
