# Export AutoCite to GGUF

After the LoRA adapter is reviewed, merge it with `Qwen/Qwen3.5-0.8B` and export the merged model with a current `llama.cpp` conversion tool that supports Qwen3.5.

```python
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

base = "Qwen/Qwen3.5-0.8B"
adapter = "sonomos/AutoCite-0.8B"
output = "outputs/autocite-0.8b-merged"

model = AutoModelForImageTextToText.from_pretrained(base, device_map="cpu")
model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
model.save_pretrained(output, safe_serialization=True)
AutoProcessor.from_pretrained(base).save_pretrained(output)
```

Then convert and quantize the merged checkpoint:

```bash

python /path/to/llama.cpp/convert_hf_to_gguf.py \
  outputs/autocite-0.8b-merged \
  --outfile outputs/autocite-0.8b-f16.gguf \
  --outtype f16

llama-quantize \
  outputs/autocite-0.8b-f16.gguf \
  outputs/autocite-0.8b-q4_k_m.gguf \
  Q4_K_M
```

Run the SLM safety evaluation against the quantized build before publishing it. Conversion support changes quickly, so pin the tested `llama.cpp` commit in the model release notes.
