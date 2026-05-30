# iGamePet

[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()

逆向工程七彩虹（Colorful）显卡 LCD5A 副屏，上传和播放自定义 GIF 动画、文字和图片。彻底摆脱官方 iGameCenter 软件的限制，让你的显卡小屏幕显示任何你想显示的内容。

## 特性

- **猫咪动画**：用像素艺术手绘的猫走路动画，可一键生成并上传到副屏
- **GIF → PAK 转换**：将任意 GIF 动图转换为 LCD5A 原生 PAK 格式
- **文字显示**：在屏幕上居中显示中文 / 英文文本，支持自定义字体大小和颜色
- **图片显示**：将静态图片上传到副屏，支持文字叠加标注
- **实时文字**：在终端输入文字，屏幕上即时刷新显示
- **交互式控制台**：CMD / PowerShell 双版本菜单，无需记命令
- **状态通知**：预制的 working / done / fail / info 状态画面
- **双通信路径**：正式路径走官方 iGame API，研究路径走纯 Python USB HID

## 硬件信息

| 项目 | 规格 |
|---|---|
| 设备型号 | LCD5A 副屏（ITE Tech 芯片） |
| 接口 | USB HID |
| VID/PID | `0x048D` / `0x5711` |
| 全分辨率 | 1024 × 240 |
| 可见区域 | 800 × 216（x=224, y=24，四周有边框遮挡） |
| 物理安装 | 旋转 180 度（输出内容需旋转后编码） |

## 环境要求

- **操作系统**：Windows 10 / 11
- **Python**：>= 3.8，需安装依赖包 `Pillow` 和 `pythonnet`（仅 `lcd_display.py` 需要）
- **.NET Framework**：>= 4.7.2（C# 程序需要）
- **iGameCenter**：必须安装在 `C:\Program Files\iGameCenter`（Python 和 C# 都需要加载其 DLL）
- **管理员权限**：部分设备访问操作可能需要

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install Pillow pythonnet
```

### 2. 一键运行猫咪动画

```batch
run_cat.bat
```

这会自动完成：生成猫咪动画 → 转为 PAK → 上传到设备 → 播放。

### 3. 使用交互式控制台

CMD 版本：

```batch
pet.bat
```

PowerShell 版本：

```powershell
.\pet.ps1
```

菜单提供 8 个选项：猫咪动画、文字显示、实时文字、默认动画、文件列表、上传 GIF、切换文件、删除文件。

## 项目结构

```
iGamePet/
├── Python（内容生成 + 设备控制）
│   ├── pak_utils.py        # 核心共享库：PAK 格式、JPEG 编码、字体、常量
│   ├── generate_pet.py     # 像素猫咪动画生成器
│   ├── gif_to_pak.py       # GIF 转 PAK 转换器
│   ├── text_display.py     # 文字/数字静态显示
│   ├── lcd_display.py      # 主显示控制器（pythonnet 桥接 iGame API）
│   └── lcd_control.py      # USB HID 直接控制（协议研究用）
│
├── C#（设备通信）
│   └── IGamePet.cs         # CLI 工具，使用官方 iGame API DLL
│
├── 启动脚本
│   ├── run_cat.bat         # 一键：生成 → 上传 → 播放猫咪
│   ├── pet.bat             # CMD 交互式菜单
│   └── pet.ps1             # PowerShell 交互式菜单
│
├── bin/                    # 预编译二进制及 DLL 依赖
│   ├── iGameAPI.LCD.CSharp.dll
│   ├── iGameAPI.Contracts.dll
│   ├── iGameAPI.LCD.dll
│   └── N15_25/             # 运行库（LibUsbDotNet、NAudio 等）
│
└── output/                 # 生成的文件输出目录
```

## 架构设计

项目采用**两层架构**：内容生成与硬件通信分离。

### 内容生成层（Python）

所有 Python 脚本围绕 `pak_utils.py` 构建。这个核心模块提供：

- **PAK 格式构建**：详见下方 PAK 格式说明
- **JPEG 编码**：自动将帧压缩为 JPEG，并执行 180 度旋转（适配屏幕物理安装方向）
- **亮度增强**：针对 LCD 面板自动调整暗色图像的亮度
- **画布常量**：`CANVAS_W=1024`, `CANVAS_H=240`, 可见区域 `VISIBLE_W=800`, `VISIBLE_H=216`
- **字体查找**：自动搜索 Windows 系统中文字体（微软雅黑 → 黑体 → 宋体 → Arial）

### 硬件通信层

提供两条通信路径：

| 路径 | 技术 | 文件 | 状态 |
|---|---|---|---|
| **正式路径** | iGame API (.NET DLL) → pythonnet 桥接 | `lcd_display.py` | 功能完整 |
| **正式路径** | iGame API (C# 直接调用) | `IGamePet.cs` | 功能完整 |
| **研究路径** | Python `hid` 库直接 USB HID | `lcd_control.py` | 上传功能待完成 |

研究路径绕过了 iGameCenter，直接与 USB HID 设备通信，但由于上传协议的命令 ID 尚未完全逆向，目前仅支持设备探测和信息读取。

## 命令行用法

### Python - lcd_display.py（推荐）

```bash
# 列表文件
python lcd_display.py list

# 播放已存储的文件
python lcd_display.py play mypet

# 删除文件（交互式）
python lcd_display.py delete

# 显示文字
python lcd_display.py text "Hello\nWorld" --size 60

# 显示图片
python lcd_display.py image cat.png

# 显示图片 + 文字标注
python lcd_display.py imagetext screenshot.png "部署完成" --bottom

# 上传 GIF / PAK 并播放
python lcd_display.py upload animation.gif mypet

# 实时文字模式（输入即显示）
python lcd_display.py live

# 切换文件（交互式）
python lcd_display.py switch

# 状态通知
python lcd_display.py done "编译成功"
python lcd_display.py fail "构建失败"

# 预上传状态图片（给钩子使用）
python lcd_display.py setup-status
```

### Python - 内容生成

```bash
# 生成猫咪动画
python generate_pet.py --frames 30 --output output/pet.pak

# 生成 GIF 预览
python generate_pet.py --frames 30 --output output/pet.gif --gif

# GIF 转 PAK
python gif_to_pak.py animation.gif animation.pak

# 文字转 PAK
python text_display.py "Hello\nWorld" output/hello.pak --size 52

# 自定义颜色
python text_display.py "警告" warn.pak --size 72 --color 255,0,0 --bg 30,30,30
```

### C# - IGamePet.cs

```powershell
# 编译
csc /out:bin\iGamePet.exe /r:bin\iGameAPI.Contracts.dll /r:bin\iGameAPI.LCD.CSharp.dll /r:bin\iGameAPI.LCD.dll IGamePet.cs

# 使用
iGamePet detect              # 扫描设备
iGamePet info                # 设备信息
iGamePet list                # 列出文件
iGamePet play mypet          # 播放文件
iGamePet delete mypet        # 删除文件
iGamePet upload C:\my.gif mypet   # 上传并播放
iGamePet pet                 # 一键猫咪
```

## PAK 文件格式

LCD5A 原生动画格式，本项目完全逆向并实现了编码器。

```
┌──────────────────────────────────────┐
│  Header (8 + N×4 字节)               │
│  ┌ "JP"                   2 bytes   │  魔术数
│  ├ frame_count            2 bytes   │  uint16 LE
│  ├ unknown                4 bytes   │  固定 0x0C
│  └ offset_table           N×4 bytes │  每帧偏移量 uint32 LE
├──────────────────────────────────────┤
│  Frame 0                            │
│  ├ jpeg_size              4 bytes   │  uint32 LE
│  ├ jpeg_data              变长      │  JPEG 图像数据
│  └ padding                0-3 bytes │  4 字节对齐
├──────────────────────────────────────┤
│  Frame 1 ...                        │
└──────────────────────────────────────┘
```

每个帧是独立完整的 JPEG 图像（1024×240），设备按顺序循环播放。

## LCD 通信协议

底层使用 USB HID 协议，命令格式如下：

```
┌──────┬──────────┬─────────┬──────────┬──────────┐
│Header│  CmdID   │ BodyLen │   Body   │ Checksum │
│ 1B   │  2B LE   │   1B    │  N bytes │   1B     │
└──────┴──────────┴─────────┴──────────┴──────────┘
```

- **Header**：`0xA9`（Display 显示命令）、`0xD0`（MassStorage 大容量存储）
- **Checksum**：对所有字节计算 XOR

已识别的命令：

| CmdID | 十进制 | 功能 |
|---|---|---|
| `0xED12` | 60690 | GetDevice - 获取设备信息 |
| `0xE619` | 58905 | GetFiles - 列出存储文件 |
| `0xE51A` | 58650 | PlayFile - 播放文件 |
| `0xEA15` | 59925 | GetSD - 获取 SD 卡信息 |

## 关键约束与已知问题

- **iGameCenter 必须安装**：Python 和 C# 程序都需要从 `C:\Program Files\iGameCenter` 加载 DLL。如果安装在非默认路径，需要修改源码中的 `IGAME_DIR` 常量。
- **屏幕旋转**：LCD5A 物理安装为 180 度倒置，所有 PAK 生成时默认自动旋转。如果需要关闭（例如其他型号屏幕），使用 `--no-rotate` 参数。
- **GIF 上传黑屏**：官方 API 的 GIF 直接上传在 LCD5A 上会产生黑屏。`lcd_display.py` 会自动将 GIF 转为 PAK 再上传以规避此问题。
- **管理员权限**：某些系统上访问 USB HID 设备可能需要以管理员身份运行。
- **研究路径限制**：`lcd_control.py` 的 HID 上传功能尚未完成——上传命令 ID 和协议细节仍在逆向中。

## 常见问题

### 提示 "No iGame LCD device found"

1. 确认 LCD5A 副屏已通过 USB 连接到电脑
2. 确认 iGameCenter 已安装在 `C:\Program Files\iGameCenter`
3. 尝试以管理员身份运行
4. 在设备管理器中检查是否有 "ITE" 或 "LCD5A" 设备

### 上传后屏幕黑屏

检查是否上传了 GIF 文件。请先转换为 PAK 再上传：

```bash
python gif_to_pak.py your.gif your.pak
python lcd_display.py upload your.pak
```

### 文字显示乱码

确认 `C:\Windows\Fonts\msyh.ttc`（微软雅黑）存在。可以在 `pak_utils.py` 的 `find_font()` 函数中添加其他字体路径。

## 致谢

- [iGameCenter](https://www.colorful.cn/) — 七彩虹官方显卡管理软件，本项目使用了其 API DLL
- [Pillow](https://python-pillow.org/) — Python 图像处理库
- [pythonnet](https://github.com/pythonnet/pythonnet) — Python 调用 .NET 的桥梁
- [LibUsbDotNet](https://github.com/LibUsbDotNet/LibUsbDotNet) — .NET USB 库
- [hidapi](https://github.com/trezor/cython-hidapi) — Python HID API 封装

## 许可证

[MIT](./LICENSE)
