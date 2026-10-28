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

接口不生成字幕、不估算词级时间戳，也不自动决定一个音色是否适合整篇文案。音频和字幕同步需要在最终音频产生后另做检查。

参考：[火山引擎 HTTP V3 文档](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh)；[Qwen3-TTS 官方仓库](https://github.com/QwenLM/Qwen3-TTS)。

