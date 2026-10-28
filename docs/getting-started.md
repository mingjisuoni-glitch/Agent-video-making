# 下载后准备与第一次演练

完整安装步骤见 [新机安装与验收](install.md)。本页只描述第一次成功路径。

## 1. 先跑体检

```bash
python -m pip install -e .
avm-doctor
python -m tools.fetch_skills --check
python -m unittest discover -s tests -q
```

`warn` 可表示某个可选配音后端尚未配置；`fail` 表示核心链路不完整。不要因为单元测试通过就声称已能渲染，单元测试不会启动 HyperFrames、浏览器或模型。

## 2. 证明这台机器能渲染

```bash
cd examples/hello-video
npm install
npx hyperframes doctor
npx hyperframes browser ensure
npm run check
```

检查通过后，在明确同意生成样片时运行 `npm run make`。输出为 `out/hello.mp4`。样例固定为 9:16、1080×1920、12 秒、30 FPS、极简产品风、无旁白；它只证明环境和方法可运行，不是下载者今后视频的默认授权。

## 3. 开始自己的视频

阅读 [制作规则](../AGENTS.md)、[方案模板](../VIDEO_DESCRIPTION_TEMPLATE.md)和[风格库](../visual-styles.md)。为每条视频重新确认比例、时长、风格和配音，再完成文本拆解、精修、分镜和素材计划。

复制并填写 `examples/video-plan.example.json`：

```bash
avm-preflight my-video-plan.json
```

方案结构以 `video.schema.json` 为唯一真源；八项创意检查必须引用真实证据文件。通过只表示当前结构、语义与证据自洽；仍须人工核对事实、素材许可、旁白听感、字幕停顿和最终预览。

## 4. 配音和字幕

无配音不需要模型或 API。火山需要自己的账号、资源、speaker 和密钥；Qwen3-TTS 需要独立环境与完整模型。先运行 `avm-voice --list-voices`，再对选定配置运行 `--check`。

长文案可用 JSONL 批量任务：

```bash
avm-voice --voices voices.local.json --batch segments.jsonl --dry-run
avm-voice --voices voices.local.json --batch segments.jsonl --resume --duration-report outputs/durations.json
```

最终音频不再改动后，才运行：

```bash
avm-captions --audio outputs/final.wav --model small --language zh
```

字幕工具按真实停顿分组；它不会为了满足固定字数擅自拆开一个没有停顿的口播单位。

## 5. 组装、严格检查与交付清单

准备 `scenes.json`（可复制 `examples/voiced-demo/scenes.json`）后执行：

```bash
avm-assemble scenes.json --out out/my-video
cd out/my-video
npm install
npm run check -- --json
```

使用该命令保存的 `.hyperframes/artifacts/checks/<id>.json` 重新运行最终门禁：

```bash
avm-preflight ../../my-video-plan.json --with-checks .hyperframes/artifacts/checks/<id>.json
```

人工审看和最终渲染完成后，在仓库根目录生成交付清单：

```bash
avm-manifest --plan my-video-plan.json --video out/my-video/out/video.mp4 \
  --audio outputs/final.wav --captions outputs/captions.json \
  --checks out/my-video/.hyperframes/artifacts/checks/<id>.json -o delivery.json
```

音频和字幕命令会自动生成同名 `*.avm.json` 来源记录；不要在生成 sidecar 后替换对应产物，否则交付清单会因哈希不一致而拒绝。
