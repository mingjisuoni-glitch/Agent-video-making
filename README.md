# 通用视频制作方法库

这里提炼视频制作的规则、方案模板、技能路由、风格与动效参考，以及可切换后端的配音接口。它不包含系列选题、脚本、成片、素材、试听、模型权重或 API 凭据。

## 目录

- [AGENTS.md](AGENTS.md)：制作前确认、文本与分镜、音画同步和交付规则。
- [VIDEO_DESCRIPTION_TEMPLATE.md](VIDEO_DESCRIPTION_TEMPLATE.md)：单条视频制作方案模板。
- [video-skill-library.md](video-skill-library.md)：按任务内容选择技能与创意检查。
- [visual-styles.md](visual-styles.md)、[motion-library.md](motion-library.md)：两个默认视觉方向、自定义风格规则和动效转译参考。
- [docs/voice-workflow.md](docs/voice-workflow.md)：配音制作顺序与接口边界。
- [LICENSE.md](LICENSE.md)、[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)：分范围授权和第三方工具、模型、服务说明。
- `voice/`：火山引擎与本地 Qwen3-TTS 的统一调用接口。

**制作视频前，先配置 HyperFrames 环境。**在将本方法库交给 Codex、Qwen Code、WorkBuddy 或其他可操作本地工程的 agent 时，先确保其工作环境能访问项目文件和终端，并已准备 Node.js、HyperFrames CLI 及对应的 HyperFrames Skill。再按 [下载后准备与演练](docs/getting-started.md) 完成本地预检和新工程初始化。本仓库是方法库，没有视频组合或渲染工程；下载它本身不会配置好 HyperFrames，也不能直接渲染视频。

下载者需按自己的内容重新确认每条视频的参数、素材许可、视觉风格和配音方式。默认风格是剧情解说风、极简产品风，也可自行添加。配音方式为无配音、火山语音 API 或本地 Qwen3-TTS；后两者需选择具体音色。Skill、HyperFrames、语音模型以及云服务账号由下载者自行安装或配置。

现有项目登记过 Kokoro 和 Qwen3-TTS 音色；这个接口先实现你指定的火山引擎与本地 Qwen3-TTS 两个后端。Kokoro 音色配方不属于这两个后端，不能通过改一个音色 ID 直接使用；后续可按同一契约增加 Kokoro 适配器。各文件的对外授权见 [LICENSE.md](LICENSE.md)。

## 配音接口

**使用范围：仅本项目提供的配音方案不可用于商业用途。**这项限制不适用于仓库内的视频制作规则、方案模板、风格和动效文档；这些通用文件按 [LICENSE.md](LICENSE.md) 中的 Apache-2.0 条款授权。配音代码、示例配置和使用说明分别按该文件列明的非商业许可授权。具体模型、音色及 API 的条件见 [第三方说明](THIRD_PARTY_NOTICES.md)。

### 统一流程

1. 先确认视频方案，锁定视频适配精修稿及自然停顿分句。
2. 在 `voices.example.json` 的副本中选定一个音色配置和后端。
3. 逐个停顿分句合成，保持全文音色与整体语速一致，并试听读音、停顿和情绪。
4. 合成最终音频后，再进行词级对齐并按真实停顿制作字幕；任何重新配音或剪辑都要重新对齐。

`VoiceSpec` 是共同输入，`SynthesisResult` 是共同输出。`VolcanoProvider` 使用火山引擎 HTTP V3；`Qwen3LocalProvider` 读取本机已下载的 Qwen3-TTS CustomVoice 模型。两者都由同一个 CLI 选择调用。火山输出 MP3，本地 Qwen 输出 WAV；后续混音和字幕流程须以最终音频文件为准。示例配置保留了项目里四个 Qwen 音色的名称、说话人和种子，但不包含试听音频或无法在 0.6B 中生效的语气指令。

### 使用

```powershell
# 火山引擎：从控制台取得新式 API Key，放入当前会话环境变量。
$env:VOLC_API_KEY = '<your-key>'
python -m voice.cli --voices voices.example.json --voice volcano-example --text-file approved-segment.txt --output outputs/segment.mp3

# 本地 Qwen3-TTS：先安装 qwen-tts 和 soundfile，并从 Qwen 官方仓库下载模型。
$env:QWEN3_TTS_MODEL_DIR = 'C:\path\to\Qwen3-TTS-12Hz-0.6B-CustomVoice'
python -m voice.cli --voices voices.example.json --voice qwen-accent --text-file approved-segment.txt --output outputs/segment.wav
```

在下载后的仓库根目录执行命令。不要把真实密钥写进 JSON、命令脚本、聊天记录或 Git 提交。旧控制台也可设置 `VOLC_APP_ID` 和 `VOLC_ACCESS_KEY`。`resource_id` 显式配置，因为它决定服务版本和计费方式。

真正合成前，可先运行不联网的本地配置检查：`python -m voice.cli --voices voices.example.json --voice volcano-example --check`，或将音色改为 `qwen-accent` 检查本地 Qwen 环境。检查通过不代表云端账号已开通资源，也不代表模型推理一定成功。

本地 Qwen3-TTS 的模型需要用户自行下载；程序不会在运行时联网下载。0.6B CustomVoice 不支持 `instruct` 风格指令，若要使用该能力，应选支持它的 1.7B CustomVoice 模型。两种后端的音色 ID 不能直接互换，切换后端须重新试听和校对。

该接口只负责生成音频，不生成词级时间戳或字幕。火山端需要账号、可用资源和网络；Qwen 端需要本机模型和足够的计算资源。未提供凭据，也未进行真实服务调用。

官方参考：[火山引擎 HTTP V3](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh) · [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)

