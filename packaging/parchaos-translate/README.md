# Translate Selection (parchaos-translate)

Select text in any app and press **Ctrl+Alt+T**. English text is shown in Spanish and
Spanish text in English, translated on this computer. Nothing is sent anywhere.

## What gets downloaded on first use

| What | From | Licence |
|---|---|---|
| python3-onnxruntime, python3-numpy, python3-sentencepiece | Fedora (dnf, one password prompt) | MIT / Apache-2.0 / BSD |
| Opus-MT English→Spanish | `Xenova/opus-mt-en-es` @ `4b002a4c7edd54a7ced58877258b87f7efd3f892` | Apache-2.0 |
| Opus-MT Spanish→English | `Xenova/opus-mt-es-en` @ `eadfd7c658a9d8929ac3b8e996b68a68e2c7d480` | Apache-2.0 |

The models are by Helsinki-NLP (Language Technology Research Group, University of Helsinki),
published as `Helsinki-NLP/opus-mt-en-es` and `Helsinki-NLP/opus-mt-es-en` with the Apache-2.0
licence on their model cards. The OPUS-MT project also publishes its models under CC-BY 4.0;
either way, this is the attribution. They were trained on the OPUS parallel corpora
(J. Tiedemann and S. Thottingal, "OPUS-MT — Building open translation services for the
World", EAMT 2020). Xenova's repositories hold ONNX conversions of the same weights; ours use
the 8-bit quantized encoder and decoder. Every file has its size and SHA-256 written in
`parchaos-translate`; a file that doesn't match is thrown away.

Files go to `~/.local/share/parchaos/translate/` (about 230 MB). `parchaos-translate remove`
deletes them.
