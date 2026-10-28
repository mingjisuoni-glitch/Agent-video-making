# 下载后准备与演练

本仓库是**方法和接口代码**。下载后即可阅读规则和模板、运行不联网的单元测试；它没有视频组合、示例素材、配音模型或可直接渲染的成片。

**前置顺序：先配置 HyperFrames 环境，再创建视频工程、制作组合或渲染。**只阅读方法文档或运行配音接口时，不需要 HyperFrames；但任何 agent 要实际制作视频，都必须先完成下列环境检查。模型名称本身不能代替本地文件、终端和工具权限。

## 1. 取得仓库并确认工具

从 GitHub 克隆本仓库或下载 ZIP；如果仓库仍为私有，需要先登录有访问权限的账号。以下命令在仓库根目录执行。若只使用文档，不必安装配音依赖；若运行配音接口，先安装 Python 3.10 或更新版本。Qwen3-TTS 官方建议使用独立的 Python 3.12 环境。下载本仓库不会自动安装 HyperFrames。

```powershell
python --version
python -m unittest discover -s tests -q
```

测试应通过，且不会调用火山 API 或加载 Qwen 模型。

## 2. 先配置 HyperFrames 环境

在准备用于制作视频的电脑或 agent 工作环境中，先完成以下准备：

1. 安装 Node.js 和 npm，确认 `node --version` 与 `npm --version` 可运行。
2. 按 [HyperFrames 官方文档索引](https://hyperframes.mintlify.app/llms.txt)安装或调用 HyperFrames CLI，并安装当前任务所需的 HyperFrames Skill。具体安装命令与版本以当前官方文档和所用 agent 的 Skill 机制为准。
3. 确认 agent 能读取、修改本地项目文件并执行终端命令；把本仓库的 `AGENTS.md`、方案模板和技能路由交给它阅读。不同 agent 对规则文件和 Skill 的自动加载方式可能不同，不能仅凭下载本仓库就假定它已加载这些规则。
4. 在**另建的 HyperFrames 视频工程**中完成初始化，并验证 CLI 能识别工程、预览和检查命令可运行。检查命令应在视频工程目录执行，不能在本方法库目录执行：本方法库没有 `package.json` 或 `index.html`。

如果上述环境尚未就绪，可以先阅读规则和编写制作方案；不得声称已经能够制作或渲染 HyperFrames 视频。

## 3. 开始一条新视频

阅读 [制作规则](../AGENTS.md)、[方案模板](../VIDEO_DESCRIPTION_TEMPLATE.md)和[风格库](../visual-styles.md)。按自己的题材确认比例、时长、风格、配音方式；两个默认风格是剧情解说风和极简产品风，也可新增。完成文本拆解、精修、分镜及素材计划后，把方案交给使用者明确确认。获批前不调用 TTS 或视频生成服务。

要实际制作 HyperFrames 视频，另建 HyperFrames 工程并在其中制作组合；本方法库不带 `package.json`、`index.html` 或成片。HyperFrames 的安装和初始化以其[机器可读文档索引](https://hyperframes.mintlify.app/llms.txt)及对应 Skill 为准。视频素材、字体及使用许可也由新项目准备。

## 4A. 选择“无配音”

无需配置火山账号或下载 Qwen 模型。制作方案仍需写清画面文字、BGM、音效及它们的时间线。

## 4B. 选择火山语音 API

在火山引擎控制台开通相应语音合成资源，取得 API Key、音色 ID 和匹配的 `resource_id`。这三者不能靠示例值推定。新控制台将 API Key 放在当前终端的 `VOLC_API_KEY` 环境变量；旧控制台可用 `VOLC_APP_ID` 与 `VOLC_ACCESS_KEY`。`.env.example` 只是变量清单，不会自动加载，也不要填入真实密钥后提交。

```powershell
Copy-Item voices.example.json voices.local.json
# 编辑 voices.local.json 中的 speaker 与 resource_id，再在当前终端设置密钥。
$env:VOLC_API_KEY = '<从控制台取得的密钥>'
python -m voice.cli --voices voices.local.json --voice volcano-example --check
```

`--check` 只核对本地配置，不联网、没有用量费用。通过后，在视频方案获批且 `approved-segment.txt` 已写入最终口播分句时，才运行真实合成：

```powershell
python -m voice.cli --voices voices.local.json --voice volcano-example --text-file approved-segment.txt --output outputs/segment.mp3
```

真实调用会发送文本到火山并可能计费。第一次先用短句验证账号权限、音色、资源和输出，再进行长文案制作；试听后再进行最终音频的词级字幕对齐。

## 4C. 选择本地 Qwen3-TTS

在独立 Python 环境安装 `qwen-tts` 与 `soundfile`，并从 [Qwen 官方仓库](https://github.com/QwenLM/Qwen3-TTS)获取完整的 CustomVoice 模型目录。`0.6B` 可使用预置说话人，但会忽略 `instruct` 风格指令；需要指令控制时选择 `1.7B` CustomVoice。模型权重需要数 GB 磁盘空间；首次加载和 CPU 合成可能较慢。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip qwen-tts soundfile
# 将完整模型下载到本机目录后，指向该目录。
$env:QWEN3_TTS_MODEL_DIR = 'C:\path\to\Qwen3-TTS-12Hz-0.6B-CustomVoice'
python -m voice.cli --voices voices.example.json --voice qwen-accent --check
```

本地预检通过、制作方案获批且文案锁定后，执行：

```powershell
python -m voice.cli --voices voices.example.json --voice qwen-accent --text-file approved-segment.txt --output outputs/segment.wav
```

`--check` 只检查必要文件与 Python 包，无法保证模型文件完整、显存足够或成品听感合适。首次实际合成同样先用短句验证。改变音色、后端、文案或最终音频后，重新审听并生成字幕时间戳。

