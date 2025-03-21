## 作用

识别给定语句的语言种类

## 配置文件需要改动的部分

huggingface版本：

```json
"resources": {
        "common":{
            "cache_path": "~/.llm_web_kit_cache"
        },
        "lang-id-218": {
            "download_path": "https://huggingface.co/facebook/fasttext-language-identification/resolve/main/model.bin?download=true",
            "sha256": "8ded5749a2ad79ae9ab7c9190c7c8b97ff20d54ad8b9527ffa50107238fc7f6a"
        }
    },
```

s3版本：

```json
"resources": {
        "common":{
            "cache_path": "~/.llm_web_kit_cache"
        },
        "lang-id-218": {
            "download_path": "s3://web-parse-huawei/shared_resource/language/lid218e.bin",
            "sha256": "8ded5749a2ad79ae9ab7c9190c7c8b97ff20d54ad8b9527ffa50107238fc7f6a"
        }
    },
```

## 调用方法

```python
from llm_web_kit.model.lang_id import *
text = 'hello world, this is a test. the language is english'
print(update_language_by_str(text))
#{'language': 'en','language_details': 'eng_Latn'}
```

## 运行时间

使用单cpu进行推理

共有 2099 条数据

总 token 数: 379375

平均 token 数: 180.74

载入数据时间: 0.0214 秒

语言识别时间: 2.4313 秒

总时间: 2.4527 秒

处理速度: 863.33 条/秒
