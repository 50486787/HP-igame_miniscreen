# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project reverse-engineers the LCD5A mini screen on iGame (Colorful) graphics cards to upload and play custom GIF animations. The screen is a USB HID device (VID=0x048D, PID=0x5711, ITE Tech chip) normally controlled by iGameCenter software. Resolution is 1024x240, physically mounted rotated 180 degrees.

## Build & Run

There is no formal build system. C# files are standalone programs compiled with `csc`. Pre-built binaries exist in `bin/`.

```powershell
# Compile the main CLI tool
csc /out:bin\iGamePet.exe /r:bin\iGameAPI.Contracts.dll /r:bin\iGameAPI.LCD.dll /r:bin\iGameAPI.LCD.CSharp.dll IGamePet.cs

# Generate the cat GIF, convert to PAK, and upload (full pipeline)
.\run_cat.bat

# Interactive console menu (cat / text / default)
.\pet.bat
# or PowerShell version:
.\pet.ps1
```

Python scripts require `Pillow`:
```bash
pip install Pillow
python generate_pet.py --output output/pet.gif --frames 30
python gif_to_pak.py output/pet.gif output/pet.pak
python text_display.py "Hello\nWorld" output/hello.pak --size 52
```

## Architecture

**Two-layer design: content generation vs. hardware communication.**

### Content generation (Python)
- `generate_pet.py` — draws pixel-art cat animation frame by frame with PIL, exports GIF
- `gif_to_pak.py` — converts GIF to the LCD5A native PAK format
- `text_display.py` — renders text into PAK format (supports Chinese, custom fonts/sizes)
- `test_resolution.py` — generates test pattern PAKs at different resolutions

### Hardware communication (C#)
- **`IGamePet.cs`** — main CLI tool. Uses the official iGame API (`iGameAPI.LCD.CSharp.dll`) via `LCD.GetLCDGeneralCOM()` → `LCD5A` object. Commands: `detect`, `info`, `list`, `play`, `delete`, `upload`, `pet`.
- `ComTest.cs` — raw COM port protocol reverse engineering (SerialPort, 115200 baud)
- `LcdHidTest.cs` / `LcdHidProbe.cs` / `LcdHidSimple.cs` — three HID-level probes using Windows HID API (CreateFile on device path, HidD_GetFeature/HidD_SetFeature)
- `patch_upload.cs` — bypasses iGame API upload restrictions by calling private methods (`ModeUpload`, `UploadFile`, `UploadImage`) via reflection on `LCD5ACore`
- `raw_upload.cs` — direct USB access via LibUsbDotNet (VID 0x048D, PID 0x5711)
- `test_pipe.cs` — tests WCF named pipe endpoints for the iGameCenter background service
- `InspectDevice.cs` / `get_resolution.cs` — reflection-based device introspection

### PAK file format
```
Header:  "JP" (2 bytes, magic)
         frame_count (uint16 LE)
         unknown (uint32, always 0x0C)
         offset_table (uint32 LE × frame_count)
Frames:  jpeg_size (uint32 LE)
         jpeg_data
         padding (0-3 bytes to 4-byte alignment)
```

### LCD communication protocol
```
[Header 1B][CmdID 2B LE][BodyLen 1B][Body N bytes][XOR Checksum 1B]
```
Headers: Display = 0xA9 (169), MassStorage = 0xD0 (208).
Known commands: GetDevice=60690 (0xED12), GetFiles=58905, PlayFile=58650, GetSD=59925.

## Key constraints

- iGameCenter must be installed at `C:\Program Files\iGameCenter` for the official API DLLs
- The C# programs set up assembly resolution to load DLLs from iGameCenter's directories
- Screen is mounted rotated 180 degrees — all PAK content should be rotated before encoding
- The official API may reject uploads; `patch_upload.cs` works around this by calling private internal methods via reflection
- Running as administrator may be required for device access

<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（20 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令

## 可用 Skills

Skills 位于 `.claude/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文代码审查规范——在保持专业严谨的同时，用符合国内团队文化的方式给出有效反馈
- **chinese-commit-conventions**: 中文 Git 提交规范 — 适配国内团队的 commit message 规范和 changelog 自动化
- **chinese-documentation**: 中文技术文档写作规范——排版、术语、结构一步到位，告别机翻味
- **chinese-git-workflow**: 适配国内 Git 平台和团队习惯的工作流规范——Gitee、Coding、极狐 GitLab、CNB 全覆盖
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发或执行实现计划之前使用——创建具有智能目录选择和安全验证的隔离 git 工作树
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `Skill` 工具加载对应 skill 并严格遵循其流程。绝不要用 Read 工具读取 SKILL.md 文件。

如果你认为哪怕只有 1% 的可能性某个 skill 适用于你正在做的事情，你必须调用该 skill 检查。
<!-- superpowers-zh:end -->
