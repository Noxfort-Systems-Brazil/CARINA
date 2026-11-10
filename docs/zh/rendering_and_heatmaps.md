---
tags: [rendering, heatmaps, maps, sumo, visualization, graphics]
aliases: [渲染引擎, 空间热力图, 地图生成器, 画布可视化]
---

# 🗺️ 矢量地图渲染引擎与异步空间热力图

本文档详尽规范了 CARINA 位于 [`src/rendering/`](../../src/rendering) 的地图矢量渲染与交通流可视化子系统。深入阐述了从 SUMO 道路网络定义文件（`.net.xml`）生成静态矢量地图、地理空间坐标投影变换以及基于核密度估计（KDE）的异步实时空间热力图插值算法。

⬅️ 返回 [核心技术主文档中心 (MOC)](carina_moc.md) | 🖥️ 查阅 [桌面 UI 与仪表盘](ui_and_dashboard.md) | 📈 查阅 [宏观基础图 (MFD)](mfd_and_analytics.md)

---

## 1. 渲染子系统架构拓扑

CARINA 原生提供完全离线的高性能地理空间可视化能力，绝不依赖任何外部商业瓦片地图服务或第三方专有制图 API。整个渲染管线 100% 离线自主运行：

```text
 SUMO 道路网络定义 (`.net.xml`) / 实时时序遥测
                      │
                      ▼
        ┌───────────────────────────┐
        │  map_coordinate_generator │ (将 UTM 测地/笛卡尔坐标映射为画布像素)
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
┌────────────────────────┐  ┌────────────────────────┐
│   static_map_renderer  │  │ async_heatmap_renderer │
│ (车道线、节点、信号灯) │  │ (KDE 空间密度与延误插值)│
└───────────┬────────────┘  └───────────┬────────────┘
            │                           │
            └─────────────┬─────────────┘
                          ▼
             原生 Flet 自绘画布表面
             (`LiveCanvasMapWidget`)
```

---

## 2. `src/rendering/` 核心功能模块

### 2.1 空间坐标投影变换器 (`map_coordinate_generator.py`)
位于 [`src/rendering/map_coordinate_generator.py`](../../src/rendering/map_coordinate_generator.py)：
- 将 SUMO 2D 真实物理米制坐标 $(x, y)$ 转换为前端视口画布像素坐标 $(u, v)$。
- 全面支持平滑视口平移（Pan）、双指手势缩放（Pinch-to-zoom），并支持基于全部活动交叉口的包围盒（Bounding Box）一键自动居中。
- 在异构显示器分辨率和长宽比下，自动维持 1:1 的真实物理各向同性，杜绝地图畸变拉伸。

### 2.2 静态矢量路网渲染器 (`static_map_renderer.py`)
位于 [`src/rendering/static_map_renderer.py`](../../src/rendering/static_map_renderer.py)：
- 高效解析 SUMO `.net.xml` 车道几何形状（Polylines）、交叉口拓扑边界以及路口内部导向车道连通关系。
- 矢量绘制多车道干线道路、车道分道虚线、行车导向箭头以及信号灯灯头状态图标。
- 在内存中缓存光栅化矢量路径，在静态无几何变动场景下彻底消除 CPU 冗余重绘开销。

### 2.3 异步空间热力图插值渲染器 (`async_heatmap_renderer.py`)
位于 [`src/rendering/async_heatmap_renderer.py`](../../src/rendering/async_heatmap_renderer.py)：
- 运用 **核密度估计（Kernel Density Estimation, KDE）** 空间算法，将离散车道的点状与线状微观指标插值为全路网连续二维空间热力场：
  - **车流空间密度热力图：** 直观展现全城各片区每平方公里的车辆空间堆积度。
  - **排队等待时间延误热力图：** 精准高亮主干道通行瓶颈与常发性拥堵节点。
  - **溢流回堵风险热力图：** 动态可视化呈现 Guardian 智能体预测的拥堵冲击波扩散趋势。
- 将高耗时的二维高斯核模糊（Gaussian Blur）与矩阵卷积运算卸载至后台独立工作线程执行，确保前端 60 FPS 的流畅交互帧率。

---

## 3. 热力图参数配置与色彩阶梯方案

热力图融合权重与色彩映射配置于 [`config/settings.ini`](../../config/settings.ini)：

```ini
[HEATMAP_SCALING]
weight_occupancy = 1.0
weight_waiting_time = 1.5
weight_flow = 1.0
saturation_threshold = 0.85
lane_aggregation_strategy = max
heatmap_strategy = combined
heatmap_saturation = 1.0
```

---

<div align="center">
  <img src="../assets/noxfort-logo.png" alt="Noxfort Systems Logo" width="45" /><br/>
  <b>Noxfort Systems</b> — <i>A State Of Art Company</i><br/>
  <i>智能交通系统工程 • CARINA CORE v1.2.0</i><br/>
  <small>© 2026 Noxfort Systems. 基于 AGPLv3 或更高版本授权 (SPDX: <code>AGPL-3.0-or-later</code>)。</small>
</div>
