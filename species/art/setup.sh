#!/usr/bin/env bash
# Installs what species/art/make.py runs on, in Linux (WSL2 Ubuntu 24.04 on the owner's Windows machine), with no
# root: everything goes under $ART_HOME (default ~/qrx-art), outside the repository. Each part is skipped when it is
# already there, so this can be run again after a failure. Versions and commits are the ones make.py pins (PINS).
#
#   bash species/art/setup.sh base        micromamba, uv, Blender, gltfpack, the "art" env (render, cutout, checks)
#   bash species/art/setup.sh hunyuan     Hunyuan3D 2.1 and its env "hy3d"
#   bash species/art/setup.sh trellis     TRELLIS and its env "trellis"
#   bash species/art/setup.sh unirig      UniRig and its env "unirig"
#
# Model weights are fetched on first use into $ART_HOME/hf (HF_HOME), each at the revision make.py names.
set -euo pipefail
ART_HOME=${ART_HOME:-$HOME/qrx-art}
BIN=$ART_HOME/bin
MM=$BIN/micromamba
export MAMBA_ROOT_PREFIX=$ART_HOME/mamba
mkdir -p "$BIN" "$ART_HOME/src" "$ART_HOME/hf" "$ART_HOME/tmp"
export TMPDIR=$ART_HOME/tmp

BLENDER=4.5.16
GLTFPACK=v1.3
BLENDER_MIRROR=https://mirrors.ocf.berkeley.edu/blender/release/Blender4.5

# Upstream sources, pinned (the commit each was first set up from; make.py checks them).
HUNYUAN_REPO=https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git
TRELLIS_REPO=https://github.com/microsoft/TRELLIS.git
UNIRIG_REPO=https://github.com/VAST-AI-Research/UniRig.git
HUNYUAN_COMMIT=${HUNYUAN_COMMIT:-82920d643c0dc2f7bfd7255f45f62d386edfe60c}   # 2025-10-17
TRELLIS_COMMIT=${TRELLIS_COMMIT:-193e0502b5cb3eb5997ec457d5340e95d09b158e}   # 2026-10-27
UNIRIG_COMMIT=${UNIRIG_COMMIT:-6793c6640ff01c8fb389f3993434124bb43d2933}    # 2026-06-04

say() { printf '\n== %s\n' "$*"; }

env_create() {  # name, then micromamba packages
    local name=$1; shift
    if [ ! -x "$MAMBA_ROOT_PREFIX/envs/$name/bin/python" ]; then
        "$MM" create -y -q -n "$name" -c conda-forge -c nvidia/label/cuda-12.4.1 "$@"
    fi
}
in_env() { local name=$1; shift; CUDA_HOME=$MAMBA_ROOT_PREFIX/envs/$name "$MM" run -n "$name" "$@"; }

clone() {  # url, dir, commit (empty: keep what is checked out, print it)
    local url=$1 dir=$2 commit=$3
    [ -d "$dir/.git" ] || git -c core.longpaths=true clone --recursive "$url" "$dir"
    if [ -n "$commit" ]; then git -C "$dir" fetch -q origin && git -C "$dir" checkout -q "$commit" && git -C "$dir" submodule update -q --init --recursive; fi
    echo "$(basename "$dir") at $(git -C "$dir" rev-parse HEAD)"
}

base() {
    if [ ! -x "$MM" ]; then
        say micromamba
        curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest -o "$TMPDIR/mm.tar.bz2"
        python3 -c "import tarfile,sys; tarfile.open(sys.argv[1]).extract('bin/micromamba', sys.argv[2])" "$TMPDIR/mm.tar.bz2" "$ART_HOME"
    fi
    "$MM" --version
    if [ ! -x "$BIN/uv" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$BIN" UV_NO_MODIFY_PATH=1 sh
    fi
    if [ ! -x "$BIN/gltfpack" ]; then
        say "gltfpack $GLTFPACK"
        curl -Ls "https://github.com/zeux/meshoptimizer/releases/download/$GLTFPACK/gltfpack-ubuntu.zip" -o "$TMPDIR/gp.zip"
        python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$TMPDIR/gp.zip" "$BIN"
        chmod +x "$BIN/gltfpack"
    fi
    case "$("$BIN/gltfpack" -h 2>&1 || true)" in *"-tc:"*) ;; *) echo "gltfpack has no texture compression"; exit 1;; esac
    if [ ! -x "$ART_HOME/blender/blender" ]; then
        say "Blender $BLENDER"
        local tarball=blender-$BLENDER-linux-x64.tar.xz
        curl -L --fail "$BLENDER_MIRROR/$tarball" -o "$TMPDIR/$tarball"
        curl -Ls --fail "$BLENDER_MIRROR/blender-$BLENDER.sha256" | grep linux-x64 > "$TMPDIR/blender.sha256"
        (cd "$TMPDIR" && sha256sum -c blender.sha256)
        tar -xJf "$TMPDIR/$tarball" -C "$ART_HOME"
        rm -rf "$ART_HOME/blender" && mv "$ART_HOME/blender-$BLENDER-linux-x64" "$ART_HOME/blender"
        rm -f "$TMPDIR/$tarball"
    fi
    # Blender's own build carries its libraries except a few X11 and GL ones a bare WSL lacks: take them from conda-forge.
    env_create blenderlibs xorg-libx11 xorg-libxi xorg-libxxf86vm xorg-libxfixes xorg-libxrender xorg-libxext xorg-libsm xorg-libice libxkbcommon libglvnd libegl libgl
    LD_LIBRARY_PATH=$MAMBA_ROOT_PREFIX/envs/blenderlibs/lib "$ART_HOME/blender/blender" -b --factory-startup --version | head -1
    say "env art"
    env_create art python=3.11 pip
    in_env art pip install -q --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1
    in_env art pip install -q diffusers==0.32.2 transformers==4.48.3 accelerate==1.3.0 sentencepiece protobuf \
        safetensors huggingface_hub==0.28.1 timm==1.0.14 kornia einops Pillow numpy==1.26.4 trimesh==4.6.1 pygltflib==1.16.3 scipy==1.15.1 bitsandbytes==0.45.2
    in_env art python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
}

hunyuan() {
    say "Hunyuan3D 2.1"
    clone "$HUNYUAN_REPO" "$ART_HOME/src/Hunyuan3D-2.1" "$HUNYUAN_COMMIT"
    # Python 3.10 as Hunyuan3D 2.1 was made on. Its bpy==4.0 is left out (PyPI no longer serves it); bpy only turned the
    # painted OBJ into a GLB, which mesh_hunyuan.py does with trimesh.
    env_create hy3d python=3.10 pip cuda-toolkit=12.4.1 gxx_linux-64=12 gcc_linux-64=12 ninja         xorg-libx11 xorg-libxi xorg-libxxf86vm xorg-libxfixes xorg-libxrender xorg-libxext xorg-libsm libxkbcommon libglvnd libgl
    local src=$ART_HOME/src/Hunyuan3D-2.1
    in_env hy3d pip install -q --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1
    # Its requirements without the two mirrors in China and without deepspeed and the demo's web server (training and gradio only).
    grep -vE "^--extra-index-url|^deepspeed|^gradio|^fastapi|^uvicorn|^bpy" "$src/requirements.txt" > "$TMPDIR/hy3d-requirements.txt"
    in_env hy3d pip install -q -r "$TMPDIR/hy3d-requirements.txt" "setuptools<81"     # pytorch-lightning 1.9 needs pkg_resources
    export TORCH_CUDA_ARCH_LIST=8.6 MAX_JOBS=12
    (cd "$src/hy3dpaint/custom_rasterizer" && in_env hy3d pip install -q --no-build-isolation -e .)
    (cd "$src/hy3dpaint/DifferentiableRenderer" && in_env hy3d bash compile_mesh_painter.sh)
    mkdir -p "$src/hy3dpaint/ckpt"
    [ -f "$src/hy3dpaint/ckpt/RealESRGAN_x4plus.pth" ] || curl -L --fail \
        https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -o "$src/hy3dpaint/ckpt/RealESRGAN_x4plus.pth"
}

trellis() {
    say TRELLIS
    clone "$TRELLIS_REPO" "$ART_HOME/src/TRELLIS" "$TRELLIS_COMMIT"
    env_create trellis python=3.10 pip cuda-toolkit=12.4.1 gxx_linux-64=12 gcc_linux-64=12 ninja libusb xorg-libx11 xorg-libxext xorg-libsm libglvnd libgl   # libusb: open3d
    local src=$ART_HOME/src/TRELLIS
    in_env trellis pip install -q --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1
    export TORCH_CUDA_ARCH_LIST=8.6 MAX_JOBS=12
    # Its setup.sh for the plain packages only: it builds the CUDA extensions in isolated pip builds that cannot see
    # torch, so they are built here with --no-build-isolation.
    (cd "$src" && in_env trellis bash setup.sh --basic)
    in_env trellis pip install -q xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124
    in_env trellis pip install -q spconv-cu124 "numpy<2"
    in_env trellis pip install -q kaolin==0.17.0 -f https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.1_cu124.html
    local ext=$ART_HOME/src/trellis-ext
    mkdir -p "$ext"
    [ -d "$ext/nvdiffrast" ] || git clone -q https://github.com/NVlabs/nvdiffrast.git "$ext/nvdiffrast"
    git -C "$ext/nvdiffrast" checkout -q v0.3.3
    in_env trellis pip install -q --no-build-isolation "$ext/nvdiffrast"
    [ -d "$ext/mip-splatting" ] || git clone -q --recursive https://github.com/autonomousvision/mip-splatting.git "$ext/mip-splatting"
    in_env trellis pip install -q --no-build-isolation "$ext/mip-splatting/submodules/diff-gaussian-rasterization"
    in_env trellis python -c "import torch, xformers, spconv, nvdiffrast.torch, diff_gaussian_rasterization, kaolin; print('trellis env ok', torch.__version__)"
}

unirig() {
    say UniRig
    clone "$UNIRIG_REPO" "$ART_HOME/src/UniRig" "$UNIRIG_COMMIT"
    env_create unirig python=3.11 pip cuda-toolkit=12.4.1 gxx_linux-64=12 gcc_linux-64=12 ninja \
        xorg-libx11 xorg-libxi xorg-libxxf86vm xorg-libxfixes xorg-libxrender xorg-libxext xorg-libsm libxkbcommon libglvnd libgl
    local src=$ART_HOME/src/UniRig
    in_env unirig pip install -q --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1
    # flash_attn from its prebuilt wheel (building it takes hours), then the rest of its requirements.
    in_env unirig pip install -q "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.5cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"
    grep -vE "^flash_attn|^wandb" "$src/requirements.txt" > "$TMPDIR/unirig-requirements.txt"
    in_env unirig pip install -q -r "$TMPDIR/unirig-requirements.txt"
    in_env unirig pip install -q spconv-cu124 torch_scatter torch_cluster -f https://data.pyg.org/whl/torch-2.5.1+cu124.html
    in_env unirig pip install -q numpy==1.26.4
}

for part in "${@:-base}"; do "$part"; done
