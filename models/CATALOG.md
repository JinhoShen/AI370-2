# 本機模型清單

模型集中於 `/home/shen/AI370-2/models/`；`GGUF -> .` 保留舊程式路徑。

大小以 GiB 計算；分類不代表已通過推論驗證。

## 語言模型

| 檔案 | GiB |
|---|---:|
| [Devstral-Small-2-24B-Instruct-2512-Q3_K_M.gguf](Devstral-Small-2-24B-Instruct-2512-Q3_K_M.gguf) | 10.69 |
| [Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf](Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf) | 7.52 |
| [Qwen3-0.6B-Q4_0.gguf](Qwen3-0.6B-Q4_0.gguf) | 0.36 |
| [Qwen3-14B-Q4_0.gguf](Qwen3-14B-Q4_0.gguf) | 7.96 |
| [Qwen3-14B-Q4_K_M.gguf](Qwen3-14B-Q4_K_M.gguf) | 8.38 |
| [Qwen3-4B-Q4_0.gguf](Qwen3-4B-Q4_0.gguf) | 2.21 |
| [Qwen3.5-9B-UD-Q4_K_XL.gguf](Qwen3.5-9B-UD-Q4_K_XL.gguf) | 5.56 |
| [Qwen3.6-35B-A3B-Q8_0.gguf](Qwen3.6-35B-A3B-Q8_0.gguf) | 34.37 |
| [Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf](Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf) | 10.86 |
| [Qwen3.8-27B-Fable-5-Coding-Distilled.i1-IQ3_M.gguf](Qwen3.8-27B-Fable-5-Coding-Distilled.i1-IQ3_M.gguf) | 11.89 |
| [Qwen3.8-27B-UD-IQ2_S.gguf](Qwen3.8-27B-UD-IQ2_S.gguf) | 7.80 |
| [Qwen3.8-27B-UD-IQ2_XXS.gguf](Qwen3.8-27B-UD-IQ2_XXS.gguf) | 6.77 |
| [Qwen3.8-27B-UD-IQ3_XXS.gguf](Qwen3.8-27B-UD-IQ3_XXS.gguf) | 10.18 |
| [Qwen3.8-27B-UD-Q2_K_XL.gguf](Qwen3.8-27B-UD-Q2_K_XL.gguf) | 9.15 |
| [Qwen3.8-27B-UD-Q3_K_XL.gguf](Qwen3.8-27B-UD-Q3_K_XL.gguf) | 12.24 |
| [Qwen3.8-27B-UD-Q4_K_M.gguf](Qwen3.8-27B-UD-Q4_K_M.gguf) | 15.33 |
| [Qwen3.8-27B-UD-Q4_K_XL.gguf](Qwen3.8-27B-UD-Q4_K_XL.gguf) | 16.35 |
| [Qwen3.8-27B-Uncensored-Q4_K_M.gguf](Qwen3.8-27B-Uncensored-Q4_K_M.gguf) | 15.66 |
| [Underdog-Saluki-27B-1.0-IQ2-mix.gguf](Underdog-Saluki-27B-1.0-IQ2-mix.gguf) | 7.36 |
| [gemma-4-26B_q4_0-it.gguf](gemma-4-26B_q4_0-it.gguf) | 13.45 |
| [gemma-4-31b-jang-crack-Q4_K_M.gguf](gemma-4-31b-jang-crack-Q4_K_M.gguf) | 17.40 |
| [gpt-oss-20b-UD-Q4_K_XL.gguf](gpt-oss-20b-UD-Q4_K_XL.gguf) | 11.06 |

## 文字嵌入

| 檔案 | GiB |
|---|---:|
| [Qwen3-Embedding-0.6B-Q8_0.gguf](Qwen3-Embedding-0.6B-Q8_0.gguf) | 0.60 |
| [Qwen3-Embedding-0.6B-f16.gguf](Qwen3-Embedding-0.6B-f16.gguf) | 1.12 |

## 語音與喚醒詞

| 檔案 | GiB |
|---|---:|
| [ggml-base.bin](ggml-base.bin) | 0.14 |
| [hey_hermes.tflite](hey_hermes.tflite) | 0.00 |
| [kokoro-v1.0.onnx](kokoro-v1.0.onnx) | 0.30 |
| [voices-v1.0.bin](voices-v1.0.bin) | 0.03 |

## 影像生成

| 檔案 | GiB |
|---|---:|
| [mm_sd_v15_v2.ckpt](mm_sd_v15_v2.ckpt) | 1.69 |
| [sd15-v1-5-pruned-Q4_0.gguf](sd15-v1-5-pruned-Q4_0.gguf) | 2.84 |
| [sd_turbo-f16-q8_0.gguf](sd_turbo-f16-q8_0.gguf) | 1.88 |

## 視覺投影器

| 檔案 | GiB |
|---|---:|
| [mmproj-F16.gguf](mmproj-F16.gguf) | 0.86 |
| [mmproj-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf](mmproj-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf) | 0.84 |

## 備份與快取

- `Legacy_Cache/`：保留舊快取結構；硬連結共用的模型不重複佔用完整空間。
- `Legacy_Cache/Qwen_Cache/SER9-Qwen-Models.tar`：約 16.94 GiB 的原始備份。
- `Ross_Offline_Resources/`：約 7.1 GiB 的離線資源壓縮包與相容連結。

## 已知檢查結果

本機 Qwen3.6 Q8 的 GGUF 張量範圍檢查通過，大小為 36,903,139,328 bytes；尚未與發行者雜湊比對。T7 同名檔案曾截斷，後續複製因容量不足失敗，不完整副本已刪除；目前 T7 沒有此模型的完整副本。
