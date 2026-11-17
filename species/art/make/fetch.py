"""Downloads every model make.py pins, at its pinned revision, into HF_HOME, so the first run of a step does not wait.

    python fetch.py [hunyuan] [trellis] [unirig] [render] [cutout]      (the art env; nothing given: all of them)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from huggingface_hub import snapshot_download
import make                                       # the pins

EXTRA = {"hunyuan": [("facebook/dinov2-giant", "611a9d42f2335e0f921f1e313ad3c1b7178d206d", None)]}
PATTERNS = {"hunyuan": ["hunyuan3d-dit-v2-1/*", "hunyuan3d-paintpbr-v2-1/*", "*.json"]}
for name in sys.argv[1:] or ["hunyuan", "trellis", "unirig", "cutout", "render"]:
    pin = make.PINS[name]
    for repo, revision, patterns in [(pin["model"], pin["revision"], PATTERNS.get(name))] + EXTRA.get(name, []):
        try:
            path = snapshot_download(repo, revision=revision, allow_patterns=patterns)
            print("fetched %s@%s -> %s" % (repo, revision[:8], path), flush=True)
        except Exception as error:
            print("NOT fetched %s: %s %s" % (repo, type(error).__name__, str(error)[:200]), flush=True)
