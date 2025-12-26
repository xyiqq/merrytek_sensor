# 迈睿传感器 Home Assistant 集成开发文档

## 项目概述

本文档记录了为迈睿（Merrytek）人体存在感应器创建 Home Assistant 自定义集成的完整过程。

### 支持的传感器型号

| 型号 | 类型 | 技术 |
|------|------|------|
| MSA203D | FMCW 毫米波雷达 | 5.8GHz |
| MSA237D | FMCW 毫米波雷达 | 5.8GHz |
| MSA236D | 红外 PIR | 被动红外 |
| MSA238D | 红外 PIR | 被动红外 |

---

## 第一部分：协议分析

### 通信规格

所有型号使用统一的 **Modbus RTU** 协议：

| 参数 | 值 |
|------|-----|
| 接口 | RS485 半双工 |
| 波特率 | 9600 bps |
| 数据格式 | 8N1 |
| 地址范围 | 1-247 |
| 校验 | CRC-16 |

### 核心寄存器

| 地址 | 功能 |
|------|------|
| 0x0000 | 存在状态 (0=无人, 1=有人) |
| 0x0001 | 延时设置 |
| 0x0002 | 灵敏度 |
| 0x0003 | 光感阈值 |
| 0x0004 | 设备地址 |

---

## 第二部分：集成文件结构

```
merrytek_sensor/
├── manifest.json          # 集成元数据
├── const.py               # 常量定义
├── gateway.py             # TCP/Modbus 通信核心
├── __init__.py            # 集成初始化
├── config_flow.py         # UI 配置流程
├── binary_sensor.py       # 存在检测传感器
├── sensor.py              # 预留平台
├── strings.json           # 默认翻译
├── icon.svg               # SVG 矢量图标
├── icon.png               # 256×256 图标
├── icon@2x.png            # 512×512 高清图标
└── translations/
    ├── zh-Hans.json       # 简体中文
    └── en.json            # 英文
```

### 关键文件说明

#### manifest.json
```json
{
  "domain": "merrytek_sensor",
  "name": "迈睿传感器",
  "codeowners": ["@优诺智能"],
  "config_flow": true,
  "iot_class": "local_polling",
  "version": "1.0.0"
}
```

#### gateway.py 核心功能
- TCP 异步连接管理
- Modbus RTU 帧构建 (CRC-16)
- 多设备轮询 (Round-robin)
- 自动重连机制
- 回调通知系统

---

## 第三部分：多设备批量添加

### 地址输入格式

| 格式 | 示例 | 结果 |
|------|------|------|
| 逗号分隔 | `1,2,3` | 地址 1、2、3 |
| 范围 | `1-5` | 地址 1 到 5 |
| 混合 | `1,3-5,7` | 地址 1、3、4、5、7 |

### 实现原理

1. `config_flow.py` 解析地址字符串
2. `gateway.py` 维护设备地址列表
3. 轮询循环依次查询每个地址
4. 每个地址创建独立的 `binary_sensor` 实体

---

## 第四部分：图标制作与上传

### 图标规格要求

| 文件 | 尺寸 | 用途 |
|------|------|------|
| icon.png | 256×256 | 标准图标 |
| icon@2x.png | 512×512 | 高清 Retina |
| logo.png | 128-256 短边 | 品牌横向标志 |
| logo@2x.png | 256-512 短边 | 高清品牌标志 |

### 图标规范
- 格式：PNG
- 背景：推荐透明
- 压缩：无损优化
- 深色版本：可加 `dark_` 前缀

### 上传到 Home Assistant Brands

#### 步骤 1: Fork 官方仓库
```
https://github.com/home-assistant/brands
```

#### 步骤 2: 创建目录结构
```
custom_integrations/
└── merrytek_sensor/
    ├── icon.png
    └── icon@2x.png
```

#### 步骤 3: Git 操作
```bash
git clone https://github.com/YOUR_USERNAME/brands.git
cd brands
git checkout -b add-merrytek-sensor
mkdir -p custom_integrations/merrytek_sensor
# 复制图标文件到目录
git add .
git commit -m "Add merrytek_sensor brand"
git push -u origin add-merrytek-sensor
```

#### 步骤 4: 创建 Pull Request
访问 GitHub 仓库，点击 "Compare & pull request"

**PR 描述模板：**
```markdown
## Summary
Add brand assets for the merrytek_sensor custom integration.

## Integration Details
- Domain: `merrytek_sensor`
- Type: Custom Integration
- Description: Merrytek presence sensors via TCP/Modbus RTU

## Files Added
- icon.png (256×256)
- icon@2x.png (512×512)
```

#### 步骤 5: 等待审核
- 自动检查通过后等待人工审核
- 审核周期：几天到几周
- 合并后图标自动生效

---

## 第五部分：安装与使用

### 安装步骤

1. 将 `merrytek_sensor` 文件夹复制到：
   ```
   <HA配置目录>/custom_components/
   ```

2. 重启 Home Assistant

3. 添加集成：
   - 设置 → 设备与服务 → 添加集成
   - 搜索 "迈睿" 或 "Merrytek"

### 配置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| 名称 | 自定义名称 | 迈睿感应器 |
| 主机 | 网络转串口设备 IP | 192.168.1.100 |
| 端口 | TCP 端口 | 8899 |
| 地址 | Modbus 地址 | 1,2,3 或 1-5 |
| 类型 | FMCW 或 IR | FMCW |
| 轮询间隔 | 秒 | 1.0 |

---

## 附录：CRC-16 计算

```python
def calculate_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc
```

---

*文档版本: 1.0 | 更新日期: 2025-12-26 | 作者: 优诺智能*
