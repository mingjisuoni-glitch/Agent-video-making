# 第三方工具、模型与服务

本仓库提供制作方法和配音接口，**不附带** HyperFrames、Qwen3-TTS 模型权重、火山引擎账号或 API 凭据，也不附带音色试听、字体、视频素材和成片。下载者自行取得这些项目，并遵守其各自的许可、服务协议、音色授权和计费规则。本仓库的[配音非商业限制](LICENSE.md)是额外的项目授权边界，不能用第三方允许商用的条款覆盖。

| 项目 | 本仓库如何使用 | 官方资料与授权核对 |
| --- | --- | --- |
| HyperFrames | 作为另行安装的视频制作与渲染工具；本仓库不含其代码或可运行工程。 | [官方仓库](https://github.com/heygen-com/hyperframes)与[文档索引](https://hyperframes.mintlify.app/llms.txt)。官方仓库当前标注 Apache-2.0；使用者应核对所安装版本。 |
| Qwen3-TTS | `voice/` 可调用使用者本机安装的 `qwen-tts` 和自行下载的 CustomVoice 模型；本仓库不分发模型、预置音频或依赖包。 | [官方代码仓库](https://github.com/QwenLM/Qwen3-TTS)与[0.6B CustomVoice 模型页](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)。该模型页当前标注 Apache-2.0；改用其他模型时以对应模型页为准。 |
| 火山引擎语音 API | `voice/` 通过用户自己的账号和密钥请求语音合成；合成文本会发送给服务端，真实调用可能计费。 | [HTTP V3 接口文档](https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3?lang=zh)与[计费说明](https://docs.volcengine.com/docs/doubao-voice/billing-overview?lang=zh)。具体服务协议、音色权限与价格以用户实际开通的资源为准。 |

使用自行添加的声音、参考音频、字体或画面素材时，应确认有权使用并按原始许可保留署名或其他要求。配音服务与模型的授权范围不等于对任何人物声音或身份的使用许可。
