# Agent Video Making：通用视频制作方法库

这是一个**不绑定题材**的视频制作方法与工具仓库。它把“先确认、再拆解、后制作、最后检查”做成可复用规则、模板和机器闸门，并提供火山语音 API 与用户自装 Qwen3-TTS 的统一接口。

[English summary](README.en.md)

## 能得到什么 / 得不到什么

| 下载后已有 | 下载后没有 |
| --- | --- |
| 制作规则、方案模板、风格与动效路由 | 任何系列的选题、脚本、素材或成片 |
| 新机环境体检与渲染前预检 | API Key、云服务账号或已开通资源 |
| 12 秒、三镜、无配音的 HyperFrames 样例 | Qwen 模型权重、试听音频或人物声音授权 |
| 火山与 Qwen3-TTS 的统一 CLI | 自动替用户决定音色、许可或商业可用性 |
| 最终音频到停顿字幕的工具 | 无需确认方案即可自动生成整条视频的承诺 |

## 开始之前

实际制作视频前必须先配置 HyperFrames 环境。当前钉住的 HyperFrames 0.8.210 要求 Node.js 22+，并需要 FFmpeg 和可用的 Chrome/Chromium。只阅读方法文档不需要安装这些工具。

新电脑请从 [新机安装与验收](docs/install.md) 开始，不要跳过 `avm-doctor`。

```bash
python -m venv .venv
python -m pip install -e .
avm-doctor
python -m unittest discover -s tests -q
```

样例工程：

```bash
cd examples/hello-video
npm install
npm run check
npm run make
```

首次安装依赖和浏览器需要联网；依赖缓存完成后，该样例不需要 API Key、配音模型或远程素材即可本地检查与渲染。

## 仓库结构

- [AGENTS.md](AGENTS.md)：制作前确认、文本与分镜、音画同步及交付规则。
- [VIDEO_DESCRIPTION_TEMPLATE.md](VIDEO_DESCRIPTION_TEMPLATE.md)：单条视频制作方案模板。
- [video-skill-library.md](video-skill-library.md)：按任务内容选择 Skill 与创意检查。
- [visual-styles.md](visual-styles.md)、[motion-library.md](motion-library.md)：默认视觉方向、自定义风格和动效转译参考。
- [docs/install.md](docs/install.md)：Windows、macOS、Linux 新机安装与分级验收。
- [examples/hello-video](examples/hello-video)：可检查、可渲染的最小 HyperFrames 工程。
- `tools/`：环境体检、Skill 清单检查和视频预检。
- `voice/`：火山语音、本地 Qwen3-TTS、批量合成规划与字幕分组。
- [LICENSE.md](LICENSE.md)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)：分范围授权与第三方条件。

## 标准制作顺序

1. 确认比例与分辨率、时长、视觉方向、配音方式与具体音色。
2. 对文案逐句拆解并做视频适配精修；锁定分镜、素材和声音计划。
3. 使用 [制作方案模板](VIDEO_DESCRIPTION_TEMPLATE.md)提交方案，等待明确批准。
4. 运行 `avm-preflight video-plan.json`；失败时不进入渲染。
5. 需要旁白时，以批准后的同一版文案生成最终音频，再做词级转写和停顿字幕。
6. 对 HyperFrames 工程运行完整 `check`、人工预览和音画审计；最终批准后再渲染。

## 配音接口

配音方式可选择：无配音、火山语音 API、本地 Qwen3-TTS。后两者都要具体选择音色；模型和账号由使用者自行取得。

```bash
# 查看配置中的全部音色
avm-voice --voices voices.example.json --list-voices

# 不调用模型或 API，只检查一个后端
avm-voice --voices voices.example.json --voice volcano-example --check

# 先验证批量任务，不实际合成
avm-voice --voices voices.example.json --batch examples/segments.example.jsonl --dry-run --duration-report

# 最终音频完成后生成停顿字幕
avm-captions --audio outputs/final.wav --model small --language zh
```

完整边界和批量/断点说明见 [配音工作流](docs/voice-workflow.md)。

## 许可边界

**仅本仓库提供的配音方案不可用于商业用途。**这里包括配音工作流、`voice/` 实现、相关测试和示例音色配置；视频制作规则、模板、风格与动效文档不受这项非商业限制，按 [LICENSE.md](LICENSE.md) 的 Apache-2.0 范围授权。

第三方模型、音色、API、素材和工具有自己的许可、服务协议与计费规则；本仓库不替它们授权。具体可参考所选配音模型和服务说明及 [第三方说明](THIRD_PARTY_NOTICES.md)。

