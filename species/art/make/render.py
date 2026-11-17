"""make.py's render step: candidates for full.jpg from prompt.txt, word for word, with FLUX.1-schnell.

    python render.py <prompt.txt> <out dir> <seeds> <first seed> <model> <revision>

Writes seed-<n>.jpg (1536 x 1024, 3:2) for each seed and render.json (the prompt, the model, each seed, steps,
size, and how many of the prompt's words the text encoder kept). The transformer is loaded in 4 bits (NF4) so it fits
a 24 GB card beside the text encoders. FLUX.1-schnell is gated on Hugging Face: log in once in this shell
(huggingface-cli login), never with a token written in the repo."""
import json, os, sys, time
prompt_path, out, seeds, first, model, revision = sys.argv[1:7]
import torch                                                   # noqa: E402
from diffusers import BitsAndBytesConfig, FluxPipeline, FluxTransformer2DModel   # noqa: E402

prompt = open(prompt_path, encoding="utf-8").read().strip()
os.makedirs(out, exist_ok=True)
t = time.time()
transformer = FluxTransformer2DModel.from_pretrained(model, revision=revision, subfolder="transformer", torch_dtype=torch.bfloat16,
                                                     quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16))
pipe = FluxPipeline.from_pretrained(model, revision=revision, transformer=transformer, torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload()
tokens = len(pipe.tokenizer_2(prompt).input_ids)
print("make: loaded in %.0f s; the prompt is %d T5 tokens (schnell keeps 256)" % (time.time() - t, tokens))
record = {"prompt": prompt, "model": model, "revision": revision, "steps": 4, "guidance": 0.0, "size": [1536, 1024],
          "t5_tokens": tokens, "truncated": tokens > 256, "seeds": []}
for seed in range(int(first), int(first) + int(seeds)):
    t = time.time()
    image = pipe(prompt, width=1536, height=1024, num_inference_steps=4, guidance_scale=0.0, max_sequence_length=256,
                 generator=torch.Generator("cpu").manual_seed(seed)).images[0]
    path = os.path.join(out, "seed-%d.jpg" % seed)
    image.save(path, quality=95)
    record["seeds"].append({"seed": seed, "file": os.path.basename(path), "seconds": round(time.time() - t, 1)})
    print("make: seed %d in %.0f s, peak %.1f GB" % (seed, time.time() - t, torch.cuda.max_memory_allocated() / 2**30))
with open(os.path.join(out, "render.json"), "w", encoding="utf-8") as f: json.dump(record, f, indent=2)
