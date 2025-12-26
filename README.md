# 迈睿传感器 Home Assistant 集成开发文档

> **作者**: 优诺智能  
> **版本**: 1.0.0  
> **日期**: 2025-12-26

---

## 目录

1. [项目概述](#项目概述)
2. [协议分析](#协议分析)
3. [集成开发](#集成开发)
4. [图标制作与上传](#图标制作与上传)
5. [安装使用](#安装使用)

---

## 项目概述

### 支持的传感器

| 型号 | 类型 | 技术 | 频率 |
|------|------|------|------|
| MSA203D | FMCW 雷达 | 毫米波 | 5.8GHz |
| MSA237D | FMCW 雷达 | 毫米波 | 5.8GHz |
| MSA236D | PIR | 被动红外 | - |
| MSA238D | PIR | 被动红外 | - |

### 功能特性

- ✅ 通过 TCP 转 RS485 网关连接
- ✅ 支持 Modbus RTU 协议
- ✅ 批量添加多个传感器（支持 `1,2,3` 或 `1-5` 格式）
- ✅ 实时存在检测状态推送
- ✅ 自动重连机制

---

## 协议分析

### 通信参数

| 参数 | 值 |
|------|-----|
| 接口 | RS485 半双工 |
| 协议 | Modbus RTU |
| 波特率 | 9600 bps |
| 数据格式 | 8N1 |
| 地址范围 | 1-247 |
| 校验 | CRC-16 |

### 寄存器地址

| 地址 | 功能 | 读写 |
|------|------|------|
| 0x0000 | 存在状态 (0=无人, 1=有人) | R |
| 0x0001 | 延时时间 | R/W |
| 0x0002 | 灵敏度 | R/W |
| 0x0003 | 光感阈值 | R/W |
| 0x0004 | 设备地址 | R/W |

### CRC-16 算法

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

## 集成开发

### 文件结构

```
merrytek_sensor/
├── manifest.json          # 集成元数据
├── const.py               # 常量定义
├── gateway.py             # TCP/Modbus 通信
├── __init__.py            # 初始化入口
├── config_flow.py         # UI 配置流程
├── binary_sensor.py       # 存在检测传感器
├── sensor.py              # 预留平台
├── strings.json           # 默认翻译
├── icon.png               # 256×256 图标
├── icon@2x.png            # 512×512 高清图标
└── translations/
    ├── zh-Hans.json       # 简体中文
    └── en.json            # 英文
```

### 核心模块说明

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

#### gateway.py 功能
- TCP 异步连接（asyncio）
- Modbus RTU 帧构建与解析
- CRC-16 校验
- 多设备轮询（Round-robin）
- 自动重连
- 状态回调通知

#### config_flow.py 功能
- UI 配置界面
- 地址格式解析（支持 `1,2,3` 和 `1-5`）
- 唯一 ID 检查

---

## 图标制作与上传

### 图标规格要求

| 文件 | 尺寸 | 必需 |
|------|------|------|
| `icon.png` | **256×256** | ✅ 是 |
| `icon@2x.png` | **512×512** | 推荐 |
| `logo.png` | 128-256 短边 | 可选 |
| `logo@2x.png` | 256-512 短边 | 可选 |

> ⚠️ **重要**: 尺寸必须精确匹配，否则验证会失败！

### 图标规范
- 格式：PNG
- 背景：透明优先
- 压缩：无损优化
- 深色版本：可加 `dark_` 前缀

### 调整图标尺寸

```python
from PIL import Image

# 打开原始图片
img = Image.open('original_icon.png')

# 生成 256×256 版本
img256 = img.resize((256, 256), Image.LANCZOS)
img256.save('icon.png', 'PNG')

# 生成 512×512 版本
img512 = img.resize((512, 512), Image.LANCZOS)
img512.save('icon@2x.png', 'PNG')
```

### 上传到 Home Assistant Brands

#### 第一步：Fork 官方仓库

1. 访问 https://github.com/home-assistant/brands
2. 点击右上角 **Fork**

#### 第二步：克隆并创建分支

```bash
git clone https://github.com/YOUR_USERNAME/brands.git
cd brands
git checkout -b add-merrytek-sensor
```

#### 第三步：添加图标文件

```bash
mkdir -p custom_integrations/merrytek_sensor
cp icon.png custom_integrations/merrytek_sensor/
cp icon@2x.png custom_integrations/merrytek_sensor/
```

#### 第四步：提交并推送

```bash
git add .
git commit -m "Add merrytek_sensor brand icons"
git push -u origin add-merrytek-sensor
```

#### 第五步：创建 Pull Request

1. 访问你的 fork 仓库
2. 点击 **Compare & pull request**
3. 填写 PR 描述：

```markdown
## Summary
Add brand assets for merrytek_sensor custom integration.

## Type of change
- [x] Add a new logo or icon for a custom integration
  - [x] I've added a link to my custom integration repository

## Additional information
- Link to custom integration repository: https://github.com/YOUR_USERNAME/merrytek_sensor

## Checklist
- [x] PNG format
- [x] icon.png is 256x256px
- [x] icon@2x.png is 512x512px
```

#### 第六步：等待审核

- 自动检查会验证图片格式和尺寸
- 如果失败，修复后重新推送
- 人工审核通过后自动合并

---

## 安装使用

### 安装步骤

1. 复制 `merrytek_sensor` 到 HA 配置目录：
   ```
   <HA配置>/custom_components/merrytek_sensor/
   ```

2. 重启 Home Assistant

3. 添加集成：设置 → 设备与服务 → 添加集成 → 搜索 "迈睿"

### 配置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| 名称 | 自定义名称 | 迈睿感应器 |
| 主机 | 网转串口设备 IP | 192.168.1.100 |
| 端口 | TCP 端口 | 8899 |
| 地址 | Modbus 地址 | `1,2,3` 或 `1-5` |
| 类型 | FMCW 或 IR | FMCW |
| 轮询间隔 | 秒 | 1.0 |

### 创建的实体

| 实体 | 类型 | 说明 |
|------|------|------|
| `binary_sensor.xxx_存在检测` | 占用 | 有人/无人状态 |
| `binary_sensor.xxx_在线状态` | 连接 | 网关连接状态 |

---

## 相关链接

- **集成仓库**: https://github.com/xyiqq/merrytek_sensor
- **Brands PR**: https://github.com/home-assistant/brands/pull/8834

---

*© 2025 优诺智能 - Home Assistant 集成开发*
