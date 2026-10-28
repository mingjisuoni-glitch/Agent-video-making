# 新机安装与验收

这是新电脑的唯一安装入口。先决定你要做到哪一级，避免一上来下载数 GB 的配音依赖。

| 目标 | 必需组件 | 典型下载量 |
| --- | --- | --- |
| 只读规则、填写制作方案 | 无 | 0 |
| 运行 Python 检查和配音试跑 | Python 3.10+ | 很小 |
| 渲染无配音样例 | Node.js 22+、npm、FFmpeg、HyperFrames/Chrome | 首次数百 MB |
| 火山配音 | 上述环境、火山账号与已开通资源 | 无本地模型 |
| 本地 Qwen3-TTS | 独立 Python 环境、`qwen-tts`、模型权重 | 约 5 GB 起 |

“离线渲染”指依赖、浏览器与 npm 包已在首次联网安装中进入本机缓存；一台没有任何软件和缓存的新电脑不可能在完全断网时安装这些依赖。

## 1. 安装系统工具

HyperFrames 0.8.210 要求 Node.js 22 或更高版本。安装后核对版本：

```text
node --version
npm --version
ffmpeg -version
python --version
```

常见安装方式（全新系统还要先装 Git，或者使用下面的 ZIP 方案）：

- Windows：`winget install --id Git.Git -e`、`winget install OpenJS.NodeJS.LTS`、`winget install Gyan.FFmpeg`，Python 从 python.org 或 Microsoft Store 安装。
- macOS：先安装 Homebrew，再运行 `brew install git node@22 ffmpeg python@3.12`；Apple Silicon 通常还要执行 `echo 'export PATH="/opt/homebrew/opt/node@22/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc`，Intel Mac 将 `/opt/homebrew` 换成 `/usr/local`。
- Ubuntu/Debian：先运行 `sudo apt update && sudo apt install -y git curl ffmpeg python3 python3-venv`，再按 NodeSource 当前指引执行 `curl -fsSL https://deb.nodesource.com/setup_22.x -o nodesource_setup.sh && sudo -E bash nodesource_setup.sh && sudo apt install -y nodejs`。

如果包管理器提供的 Node 仍低于 22，先升级 Node，不要继续排查 HyperFrames。

## 2. 取得仓库并安装核心工具

有 Git 时：

```bash
git clone https://github.com/mingjisuoni-glitch/Agent-video-making.git
cd Agent-video-making
python -m venv .venv
```

没有 Git 时，在仓库网页选择 **Code → Download ZIP**，解压后进入包含 `README.md` 和 `pyproject.toml` 的目录，再运行 `python -m venv .venv`。ZIP 可以使用项目，但没有版本更新和提交历史。

激活虚拟环境：

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

```bash
# macOS / Linux
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

核心包会安装 JSON Schema 校验依赖，但不会自动安装 Qwen 模型或重型机器学习运行时。安装后运行：

```bash
avm-doctor
python -m tools.fetch_skills --check
python -m unittest discover -s tests -q
```

Skill 不是全部打包在仓库里的依赖。公开上游、安装命令、固定提交、许可证以及 `imagegen`/私有插件等例外，统一见 [Skill 来源、安装渠道与限制](skill-sources.md)。不要看到缺少可选 Skill 就从同名仓库盲装；先核对清单中的来源。

这些命令是仓库作用域工具：默认从当前仓库读取 `voices.example.json`、`tests/` 和示例方案。离开仓库目录运行时，应显式传 `avm-doctor --root <仓库路径>`、`avm-voice --voices <仓库路径/voices.example.json>`；PyPI 式的独立应用安装不在当前版本承诺范围内。

`avm-doctor` 的 `warn` 表示可选能力不可用，例如未配置 Qwen 模型或火山密钥；`fail` 才会令退出码非零。HyperFrames 自己的 `npx hyperframes doctor --json` 不同：它总是退出 0，自动化必须检查 JSON 的顶层 `ok`。

## 3. 第一次准备 HyperFrames 与浏览器

样例工程已钉住 HyperFrames 0.8.210。首次安装需要联网：

```bash
npx hyperframes@0.8.210 skills update hyperframes
cd examples/hello-video
npm install
npx hyperframes doctor
npx hyperframes browser ensure
npm run check
```

`npm install` 会安装本地 HyperFrames 和 GSAP；组合不依赖 CDN。之后运行 `npm run check` 或 `npm run make` 会使用本地锁定版本。`npm run make` 输出 `out/hello.mp4`。

## 4. 火山语音（可选）

在火山控制台开通对应资源并取得 API Key、speaker 和 `resource_id`。复制示例配置后修改，不要把密钥写入文件：

```powershell
Copy-Item voices.example.json voices.local.json
$env:VOLC_API_KEY = '<your-key>'
avm-voice --voices voices.local.json --voice volcano-example --check
```

真实调用会发送文本并可能计费。先用短句验证权限和音色。

## 5. Qwen3-TTS（可选，独立环境）

`qwen-tts==0.1.1` 会钉住一组较重的机器学习依赖，因此不要与其他 torch 项目共用环境：

```bash
python -m venv .venv-tts
# Windows: .\.venv-tts\Scripts\Activate.ps1
# macOS/Linux: source .venv-tts/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-tts.txt
```

国内网络可使用 ModelScope 获取模型：

```bash
python -m pip install -U modelscope
modelscope download --model Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice --local_dir ./models/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

然后设置 `QWEN3_TTS_MODEL_DIR` 并运行 `avm-voice ... --check`。下载后应看到声明 `custom_voice` 的 `config.json` 和完整 safetensors 权重；体检会解析权重头与分片索引，并核对所有声明分片和数据区。只有文件名、空文件或截断权重不算安装完成。

## 6. 字幕链路

先生成并锁定最终音频，再转写；中文必须显式使用多语言模型，不能使用会转成英文的 `.en` 模型：

```bash
avm-captions --audio outputs/final.wav --model small --language zh --json-output outputs/captions.json --srt-output outputs/captions.srt
```

工具仅在实际静音间隔达到 0.28 秒时分组。超过字符建议但没有真实停顿的字幕会被标记并以退出码 2 提醒，不会按固定字数强拆。

音频与字幕锁定后，用场景配置组装可检查工程：

```bash
avm-assemble scenes.json --out out/my-video
cd out/my-video
npm install
npm run check
```

`scenes.json` 的最小结构见 `examples/voiced-demo/scenes.json`。工程总时长来自 ffprobe 读取的真实音频，镜头切点只落在字幕组起点。完整的 20 秒本地语音演练需要额外安装 `espeak-ng`，运行 `bash examples/voiced-demo/scripts/build.sh`；该脚本只做严格检查，不渲染视频。

## 7. 渲染前机器闸门

复制 `examples/video-plan.example.json`，按 `video.schema.json` 记录四项确认、明确批准和八项带路径的证据对象：

```bash
avm-preflight path/to/video-plan.json
```

证据文件必须存在、可解析且计数/时长自洽。HyperFrames 严格检查后，把实际报告再次送入门禁：

```bash
avm-preflight path/to/video-plan.json --with-checks .hyperframes/artifacts/checks/<id>.json
```

放行要求为 `ok=true`、`strict=true`、`browserSkipped=false`。最终渲染后生成交付记录：

```bash
avm-manifest --plan path/to/video-plan.json --video out/video.mp4 \
  --audio outputs/final.wav --captions outputs/captions.json -o delivery.json
```

若未传 `--checks`，工具会寻找唯一的最新报告；有歧义时要求显式指定。任何输入、音频/字幕 provenance sidecar 缺失或哈希不一致都会非零退出。这个闸门不能代替人工试听、素材许可核对和最终预览。

