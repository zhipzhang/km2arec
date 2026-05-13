M2ARec 项目是对官方`KM2ARec_V3`重建程序的Python-native重写。相比于原来使用`c++`的OOP模式，在该项目中我们会使用data-driven的模式来重写。

## 环境介绍
- 激活Python环境：`conda activate km2arec`
- Python版本： 3.14
- 核心运行依赖：`uproot`, `awkward`, `numpy`（`scipy` 在 Phase 5 NKG拟合时添加）
- 开发依赖：`pytest`, `ruff`

## 数据路径以及原项目路径
### 输入文件介绍
该项目的输入数据为`G4KM2A`模拟的输出文件，该输出文件为root格式。一个示例的路径为`data/km2a_simulation.root`。

### 原项目路径
原项目是基于ROOT和C++的重建项目，路径为`/data/home/zzp/KM2A_Software/KM2AMCrec_V3`

## 开发工作流

### 提交前必须运行检查
**每次提交前必须运行 `make run-checks` 并确保全部通过。**

```bash
conda activate km2arec
make run-checks
```

`run-checks` 包含：
- `ruff format --check` — 格式检查（替代 black/isort）
- `ruff check` — lint 检查
- `pytest -v` — 单元测试

如果格式不通过，运行 `ruff format .` 自动修复，然后重新检查。

### 分支命名规范
- 功能分支：`phase<N>_<short_description>`，例如 `phase1_io`、`phase2_geometry`
- 每个 Phase 在独立分支开发，通过 PR 合并到 `main`


