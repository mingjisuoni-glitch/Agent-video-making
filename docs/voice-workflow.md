# 配音方案与双后端接口

## 使用范围

**仅本项目提供的配音方案不可用于商业用途。**这里的配音方案包括本文件的配音工作流、`voice/` 接口实现和 `voices.example.json` 示例音色配置；本限制不适用于仓库中的其他视频制作规则、模板、风格或动效文档。具体配音模型、音色和 API 的使用条件，请参考所选模型及服务的官方说明，例如 [Qwen3-TTS CustomVoice 模型页](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)和[火山引擎语音服务文档](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh)。本项目的非商业限制是对本配音方案的单独要求，不代表第三方模型或服务也一律禁止商用；商业使用本方案需另行取得项目作者授权。

## 制作顺序

1. 文案按语义拆成自然停顿分句，标明重音、情绪和必要的口播停顿。
2. 视频方案获明确批准后，锁定精修稿、音色、分镜和素材规划。
3. 使用 `voice.cli` 按已锁定的文本合成。每段记录后端、音色 ID、模型或资源 ID、语速设置和输出文件。
4. 试听每段的读音、语速、情绪与尾音；拼接后复听全文。段落级变速只有用户明确要求时才使用，并记录在制作日志。
5. 对**最终音频**做词级对齐，结合听感确定字幕的起声和停顿边界。一次自然停顿一条字幕；换行不算新条。
6. 按停顿分句逐项审计：旁白结束、字幕结束、对应主动作完成三者是否同步。音频改动后旧时间戳全部作废。

## 接口契约

`VoiceSpec` 用于描述后端、发音人和该后端支持的参数；`synthesize(text, voice, output)` 返回 `SynthesisResult`，其中含文件路径、后端、音频格式和采样率。火山适配器和本地 Qwen 适配器都遵守这个契约。两种音色 ID 不能互换；改用另一后端时需要重新选音色、试听和对齐。

火山引擎适配器通过 HTTP V3 合成 MP3。新控制台使用 `VOLC_API_KEY`，旧控制台使用 `VOLC_APP_ID` 加 `VOLC_ACCESS_KEY`。`resource_id` 必须由用户明确配置，它关联服务版本和计费。实际请求会把待合成文本发送到火山服务。

本地 Qwen 适配器直接读取用户自行下载的 CustomVoice 模型，输出 WAV。0.6B 的 `instruct` 会被官方实现忽略，因此接口会在这种配置下报错；如需指令控制语气，改用支持该功能的 1.7B CustomVoice。Qwen 不提供火山接口的数值语速参数，接口也不会假装已应用它。

选择预置 speaker 时优先匹配口播语言和母语能力。中文示例使用 `Dylan`、`Uncle_Fu`、`Serena`、`Vivian`；换成其他 speaker 前先用完整中文短段试听专名、数字、儿化和句尾，不凭英文音色名推断中文表现。

接口不会从文案估算时间戳，也不会自动决定一个音色是否适合整篇文案。`voice.captions` 会在**最终音频**上调用 HyperFrames 转写，取得真实词级时间戳后按自然停顿分组；它不重新实现强制对齐，也不会在没有停顿时按固定字数硬拆。

## CLI 能力

```bash
# 列出所有音色
avm-voice --voices voices.example.json --list-voices

# 单段试跑，不调用 API 或模型
avm-voice --voices voices.example.json --voice qwen-accent --text-file approved.txt --output outputs/test.wav --dry-run

# JSONL 批量任务；只有音频和任务指纹都匹配才会断点跳过
avm-voice --voices voices.local.json --batch segments.jsonl --resume --duration-report outputs/durations.json

# 最终音频转词级时间戳，再按停顿生成 JSON 与 SRT
avm-captions --audio outputs/final.wav --model small --language zh --json-output outputs/captions.json --srt-output outputs/captions.srt
```

批量 JSONL 的每行至少包含 `id`、`text`、`output`，可以单独指定 `voice`；未单独指定时使用命令行的 `--voice`。每次成功合成会在音频旁写入 `.avm.json` 指纹文件，包含文本和完整音色配置的摘要。`--resume` 只跳过“音频可读、指纹仍匹配”的段落；修改文本、speaker、后端参数或删除指纹后会重新合成。时长报告同时列出新完成和已验证后跳过的段落。MP3 时长报告需要 FFprobe。

中文转写必须显式选择不带 `.en` 的多语言模型并设置 `--language zh`；HyperFrames 默认的英语模型会把非英语音频转成英文。任何重新配音、拼接、变速或剪辑都会使旧字幕时间失效，必须重新运行。

参考：[火山引擎 HTTP V3 文档](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh)；[Qwen3-TTS 官方仓库](https://github.com/QwenLM/Qwen3-TTS)。

