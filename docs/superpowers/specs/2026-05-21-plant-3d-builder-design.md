# 制冷站 3D 组态构建器 — 产品设计

## 概述

制冷站页面从空白页改造为 **3D 数字孪生组态构建器**，支持在 Three.js 画布上自由摆放设备、拖拽连线构建管路网络，完成后自动保存并可随时从数据恢复画布。

## 架构

```
 浏览器 (React + Three.js)
   ↕ REST
 API Gateway (:8007) → Asset Service (:8001)
   ↕
 PostgreSQL (plants, equipment, equipment_points, loops, pipe_segments)
```

- **前端**：新增 3D PlantBuilder 页面，Three.js 渲染引擎
- **网关**：`/api/plants` 直连路由（已实现），如 Asset Service 不可用则降级到内存存储
- **Asset Service**：已有完整的 Plant / Equipment / Point / PipeSegment CRUD + 拓扑校验 + 版本管理

## 页面布局

```
┌──────────────────────────────────────────────────────┐
│ 工具栏：[添加设备 ▾] [新建回路] [校验拓扑] [保存]      │
├──────────┬───────────────────┬───────────────────────┤
│ 设备面板  │                   │ 属性面板               │
│ (可收起)  │   3D 画布          │ (选中设备/管段时显示)   │
│          │   (Three.js)      │                       │
│ ▸ 冷水主机 │                   │ 设备/管段参数 + 点位列表 │
│ ▸ 水泵    │                   │                       │
│ ▸ 冷却塔  │                   │                       │
│ ▸ 阀门    │                   │                       │
│ ▸ 传感器  │                   │                       │
├──────────┴───────────────────┴───────────────────────┤
│ 管段表格（底部，可展开/收起）                           │
│ # │ 回路 │ 源→目标 │ 管径 │ 长度 │ 阀门 │              │
└──────────────────────────────────────────────────────┘
```

## 3D 设备模型（程序化生成）

所有设备用 Three.js 几何体组合搭建，无需外部 GLTF：

| 设备 | 构成 | 颜色 |
|------|------|------|
| 离心冷水主机 | 长方体机身 + 顶部圆柱电机 + 两侧 4 管嘴 | 蓝 |
| 水泵 | 圆柱泵体 + 法兰 + 顶部电机 + 进出管嘴 | 绿 |
| 冷却塔 | 方形塔体 + 顶部风筒 + 风扇网格 | 橙 |
| 电动调节阀 | 短管段 + 执行器方盒 + 手轮 | 黄 |
| 管道 | TubeGeometry 沿路径 | 灰 |
| 传感器 | 小球/小圆柱 | 白 |

## 点位标注

设备模型表面标注 3D 球体表示点位：
- **红色球** = 控制点位 (input)：设定值、启停指令等，可交互
- **青色球** = 显示点位 (output/calc)：传感器读数、计算值，只读
- 悬停显示点位名称、当前值；点击红色球可修改设定值

## 管道生成

- 从设备 A 的控制/显示点位球 → 拖拽到设备 B 的对应点位球
- 自动生成 L 型 / Z 型折线路径（水平出 → 转弯 → 水平入）
- 两端自动对齐设备管嘴位置
- 路径关键点保存为 waypoints，加载时重建

## 交互流程

1. **添加设备**：工具栏"添加设备"→ 设备库面板（从 `/api/equipment` 加载，按类型分组）→ 勾选 → 设备 3D 模型出现在画布
2. **摆放设备**：点击选中 → 拖拽平移（XZ 平面）；滚轮调整高度（Y）
3. **连线建网**：点击点位球 → 拖拽到另一设备点位 → 自动生成管道 → 管段同时写入底部表格
4. **管段编辑**：选中管道 → 属性面板显示参数（管径/长度/粗糙度/保温/阀门）；底部表格支持批量编辑
5. **点位管理**：选中设备 → 属性面板列出该类设备所有点位（来自 EquipmentType 模板），可勾选画布上显示/隐藏
6. **校验保存**："校验拓扑"→ 调用 `/api/plants/{id}/validate` → 显示错误/警告 → "保存"写入数据库

## 数据驱动恢复

- **加载**：`GET /api/plants/{id}` → equipment (含 position) + pipe_segments (含 waypoints) → Three.js 自动重建场景
- **保存**：设备 position(x,y,z)、管段 waypoints 写入 DB
- **新建**：首次添加设备时按默认布局算法排列（同类一排，按回路流向），后续可手动调整
- 画布始终是网络数据的可视化投影，数据与视图同步

## 设备打包管理

同一类型的设备在制冷站中共享点位模板：
- 从 EquipmentType → PointTemplate 读取该类型的所有点位定义
- 属性面板按"显示点位"和"控制点位"分组展示
- 同类型多台设备可批量选择，统一设置控制点位值

## 文件结构

```
frontend/src/
  pages/PlantBuilder.tsx          ← 3D 构建器主页面
  components/plant/
    PlantCanvas.tsx               ← Three.js 场景容器
    models/                       ← 设备 3D 模型工厂
      ChillerModel.ts
      PumpModel.ts
      CoolingTowerModel.ts
      ValveModel.ts
      PipeModel.ts
      SensorModel.ts
    EquipmentPanel.tsx            ← 左侧设备面板（拖入/勾选）
    PropertyPanel.tsx             ← 右侧属性面板（设备/管段/点位）
    PipeTable.tsx                 ← 底部管段表格
    PointBadge.tsx                ← 3D 点位标注球
    interaction/                  ← 交互逻辑
      DragDrop.ts                 ← 设备拖放
      PipeConnection.ts           ← 拖拽连线
    layout/                       ← 自动布局
      AutoLayout.ts
```

## 技术栈

- **Three.js** — 3D 渲染引擎（已有 @types/three 可用）
- **@react-three/fiber** — React 与 Three.js 的集成桥
- **@react-three/drei** — 常用 3D 控件（OrbitControls, TransformControls 等）
- **@tanstack/react-query** — 已有，数据获取
- **React Router** — 已有，路由

## 边界与不做的事

- 不做 VR/AR 体验（数字孪生暂不扩展到 XR）
- 不做实时数据推流到 3D 画布（点位值显示为静态数据，实时推送后续迭代）
- 不做管道流体动画（后续迭代）
- 不做多用户协同编辑（单用户）
