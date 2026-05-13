M2ARec 项目是对官方`KM2ARec_V3`重建程序的Python-native重写。相比于原来使用`c++`的OOP模式，在该项目中我们会使用data-driven的模式来重写。

## 环境介绍
- 激活Python环境：`conda activate km2arec`
- Python版本： 3.14
- 核心的依赖：`awkward-array`, `uproot`, `numpy`, `pandas`, `pytest`

## 数据路径以及原项目路径
### 输入文件介绍
该项目的输入数据为`G4KM2A`模拟的输出文件，该输出文件为root格式。一个示例的路径为`data/km2a_simulation.root`。

### 原项目路径
原项目是基于ROOT和C++的重建项目，路径为`/data/home/zzp/KM2A_Software/KM2AMCrec_V3`


