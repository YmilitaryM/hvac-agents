import { test, expect } from '@playwright/test';

const MOCK_EQUIPMENT = [
  { id: 'ch-1', name: '离心式冷水机组 A', type_code: 'centrifugal_chiller', plant_id: null, design_params: {} },
  { id: 'ch-2', name: '离心式冷水机组 B', type_code: 'centrifugal_chiller', plant_id: null, design_params: {} },
  { id: 'pu-1', name: '冷冻水泵 A', type_code: 'pump', plant_id: null, design_params: {} },
  { id: 'pu-2', name: '冷却水泵 B', type_code: 'pump', plant_id: null, design_params: {} },
  { id: 'ct-1', name: '冷却塔 A', type_code: 'cooling_tower', plant_id: null, design_params: {} },
  { id: 'cv-1', name: '电动调节阀 A', type_code: 'control_valve', plant_id: null, design_params: {} },
  { id: 'ts-1', name: '温度传感器 A', type_code: 'temperature_sensor', plant_id: null, design_params: {} },
];

test.describe('PlantBuilder — new plant', () => {
  test.beforeEach(async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/equipment',
      (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPMENT) }),
    );
    await page.route(
      (url) => url.pathname.startsWith('/api/plants'),
      (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ id: 'test-plant', name: '测试站', equipment: [], pipe_segments: [] }) }),
    );
  });

  test('page loads with toolbar and canvas', async ({ page }) => {
    await page.goto('/plant');
    await expect(page.locator('canvas')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('制冷站构建')).toBeVisible();
    await expect(page.getByText('0 设备')).toBeVisible();
  });

  test('toolbar buttons are visible', async ({ page }) => {
    await page.goto('/plant');
    await expect(page.getByRole('button', { name: '添加设备' })).toBeVisible();
    await expect(page.getByRole('button', { name: '校验拓扑' })).toBeVisible();
    await expect(page.getByRole('button', { name: '保存' })).toBeVisible();
  });

  test('clicking 添加设备 opens equipment panel', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    await expect(page.getByText('设备库')).toBeVisible();
    await expect(page.getByText('离心式冷水机组 A')).toBeVisible();
  });

  test('equipment panel groups by type with color dots', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    // Type labels have count in parens, e.g. "离心式冷水主机 (2)"
    await expect(page.getByText(/离心式冷水主机.*\(\d+\)/)).toBeVisible();
    await expect(page.getByText(/水泵.*\(\d+\)/)).toBeVisible();
    await expect(page.getByText(/冷却塔.*\(\d+\)/)).toBeVisible();
  });

  test('clicking equipment in panel adds it and updates toolbar count', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    await page.getByText('离心式冷水机组 A').click();
    await expect(page.getByText('1 设备')).toBeVisible({ timeout: 5_000 });
  });

  test('can add multiple equipment of different types', async ({ page }) => {
    await page.goto('/plant');
    // Open panel, add first item
    await page.getByRole('button', { name: '添加设备' }).click();
    await page.getByText('离心式冷水机组 A').click();
    // Panel stays open; first item is now filtered out. Close and reopen to add next.
    await page.getByRole('button', { name: '添加设备' }).click(); // close
    await page.getByRole('button', { name: '添加设备' }).click(); // re-open
    await page.getByText('冷冻水泵 A').click();

    await expect(page.getByText('2 设备')).toBeVisible({ timeout: 5_000 });
  });

  test('can open and close equipment panel', async ({ page }) => {
    await page.goto('/plant');
    // Open
    await page.getByRole('button', { name: '添加设备' }).click();
    await expect(page.getByText('设备库')).toBeVisible();
    // Close
    await page.getByRole('button', { name: '添加设备' }).click();
    await expect(page.getByText('设备库')).not.toBeVisible();
  });

  test('topology validation shows all-ok for empty plant', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '校验拓扑' }).click();
    await expect(page.getByText('全部正常')).toBeVisible();
  });

  test('topology validation flags orphan equipment', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    await page.getByText('离心式冷水机组 A').click();

    await page.getByRole('button', { name: '校验拓扑' }).click();
    await expect(page.getByText('孤立设备')).toBeVisible();
  });

  test('can close validation results', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '校验拓扑' }).click();
    await expect(page.getByText('全部正常')).toBeVisible();
    await page.getByText('关闭').click();
    await expect(page.getByText('全部正常')).not.toBeVisible();
  });

  test('save sends POST request with correct body', async ({ page }) => {
    let requestBody: unknown = null;
    await page.route(
      (url) => url.pathname.startsWith('/api/plants'),
      (route) => {
        if (route.request().method() === 'POST') {
          requestBody = route.request().postDataJSON();
          return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ id: 'new-plant', name: '新建制冷站' }) });
        }
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ id: 'test-plant', name: '测试站', equipment: [], pipe_segments: [] }) });
      },
    );

    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    await page.getByText('离心式冷水机组 A').click();

    await page.getByRole('button', { name: '保存' }).click();

    await page.waitForTimeout(500);
    expect(requestBody).toBeDefined();
    const body = requestBody as Record<string, unknown>;
    expect(body.name).toBe('新建制冷站');
    expect(Array.isArray(body.equipment)).toBe(true);
    expect(body.equipment).toHaveLength(1);
  });

  test('pipe table panel is visible', async ({ page }) => {
    await page.goto('/plant');
    await expect(page.getByText('管段列表')).toBeVisible();
  });
});

test.describe('PlantBuilder — existing plant', () => {
  test.beforeEach(async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/equipment',
      (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPMENT) }),
    );
  });

  test('loads existing plant data and shows name', async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/plants/plant-1',
      (route) =>
        route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'plant-1',
            name: '一号制冷站',
            equipment: [
              { id: 'ch-1', name: '冷水机组', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
              { id: 'pu-1', name: '水泵', type_code: 'pump', position: { x: 6, y: 0, z: 0 }, design_params: {} },
            ],
            pipe_segments: [],
          }),
        }),
    );

    await page.goto('/plant/plant-1');
    await expect(page.getByText('一号制冷站')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('2 设备')).toBeVisible();
  });

  test('shows error message when plant fetch fails', async ({ page }) => {
    // Abort the request to simulate a network error, which causes fetch() to reject
    await page.route(
      (url) => url.pathname === '/api/plants/plant-404',
      (route) => route.abort('failed'),
    );

    await page.goto('/plant/plant-404');
    await expect(page.getByText('加载失败')).toBeVisible({ timeout: 10_000 });
  });

  test('shows loading state while fetching plant', async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/plants/plant-slow',
      async (route) => {
        await new Promise((r) => setTimeout(r, 500));
        return route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({ id: 'plant-slow', name: '慢', equipment: [], pipe_segments: [] }),
        });
      },
    );

    await page.goto('/plant/plant-slow');
    await expect(page.getByText('加载制冷站...')).toBeVisible();
  });

  test('save sends PUT when plantId exists', async ({ page }) => {
    let requestMethod = '';
    await page.route(
      (url) => url.pathname === '/api/plants/plant-edit',
      (route) => {
        requestMethod = route.request().method();
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ id: 'plant-edit', name: '已保存' }) });
      },
    );

    await page.goto('/plant/plant-edit');
    await page.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(500);
    expect(requestMethod).toBe('PUT');
  });
});

test.describe('PlantBuilder — pipe connection', () => {
  test.beforeEach(async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/equipment',
      (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPMENT) }),
    );
  });

  test('canvas loads with equipment for connection tests', async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/plants/conn-test',
      (route) =>
        route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'conn-test',
            name: '连接测试',
            equipment: [
              { id: 'ch-1', name: '冷机', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
              { id: 'pu-1', name: '水泵', type_code: 'pump', position: { x: 5, y: 0, z: 0 }, design_params: {} },
            ],
            pipe_segments: [],
          }),
        }),
    );

    await page.goto('/plant/conn-test');
    await page.waitForSelector('canvas', { timeout: 10_000 });
    await expect(page.getByText('0 管段')).toBeVisible();
  });

  test('pipe table reflects pipe count and id from loaded data', async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/plants/pipe-data',
      (route) =>
        route.fulfill({
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'pipe-data',
            name: '含管道站',
            equipment: [
              { id: 'ch-1', name: '冷机', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
              { id: 'pu-1', name: '水泵', type_code: 'pump', position: { x: 5, y: 0, z: 0 }, design_params: {} },
            ],
            pipe_segments: [
              {
                id: 'pipe-1',
                from_equipment_id: 'pu-1',
                from_point_code: 'outlet_pressure',
                to_equipment_id: 'ch-1',
                to_point_code: 'chw_supply_temp',
                diameter_mm: 200,
                length_m: 5.0,
                waypoints: [],
              },
            ],
          }),
        }),
    );

    await page.goto('/plant/pipe-data');
    await expect(page.getByText('1 管段')).toBeVisible({ timeout: 10_000 });
    // PipeTable displays point codes, diameter, and length alongside other components
    await expect(page.getByText('outlet_pressure').first()).toBeVisible();
    await expect(page.getByText('DN200').first()).toBeVisible();
    await expect(page.getByText('5m').first()).toBeVisible();
  });
});

test.describe('PlantBuilder — equipment interaction', () => {
  test.beforeEach(async ({ page }) => {
    await page.route(
      (url) => url.pathname === '/api/equipment',
      (route) => route.fulfill({ contentType: 'application/json', body: JSON.stringify(MOCK_EQUIPMENT) }),
    );
  });

  test('property panel shows default prompt when no selection', async ({ page }) => {
    await page.goto('/plant');
    await expect(page.getByText('选择设备或管段查看属性')).toBeVisible();
  });

  test('added equipment disappears from equipment library list', async ({ page }) => {
    await page.goto('/plant');
    await page.getByRole('button', { name: '添加设备' }).click();
    await expect(page.getByText('离心式冷水机组 A')).toBeVisible();
    await page.getByText('离心式冷水机组 A').click();
    // Item is now in the store — filtered out of available list
    await expect(page.getByText('离心式冷水机组 A')).not.toBeVisible();
    // Panel stays open with remaining items
    await expect(page.getByText('冷冻水泵 A')).toBeVisible();
  });

  test('all available equipment can be added without crash', async ({ page }) => {
    await page.goto('/plant');
    // Open panel once, add all items
    await page.getByRole('button', { name: '添加设备' }).click();

    const items = ['离心式冷水机组 A', '离心式冷水机组 B', '冷冻水泵 A', '冷却塔 A', '电动调节阀 A', '温度传感器 A'];
    for (const name of items) {
      await page.getByText(name).click();
    }

    await expect(page.getByText('6 设备')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('canvas')).toBeVisible();
  });
});
