"""Files: 16-bit WAV in and out, and Ogg Opus out by way of macOS's afconvert.

afconvert encodes Opus but writes it into a CAF file; `encode` reads the packets out of the CAF and writes them
into an Ogg container with the OpusHead and OpusTags headers (RFC 7845), keeping afconvert's pre-skip and the
exact sample count in the last page's granule position, so a player trims the decoder's delay at the start and
the padding at the end and a 30 s bed decodes to exactly 30 s. Ported from TranceX's
tool/audio/make_content_sounds.py. `decode` turns an Ogg Opus file back into samples with afconvert, which reads
Ogg on macOS.

Opus bytes depend on afconvert's encoder, so the same samples can give different bytes on another macOS version;
the samples themselves are deterministic.
"""
import array, os, struct, subprocess, sys, wave

from .core import RATE

VENDOR = b"QRX.pack soundscapes"


def _to_int16(x):
    return array.array("h", (int(round(max(-1.0, min(1.0, v)) * 32767)) for v in x))


def write_wav(path, channels):
    """A 16-bit WAV of one or two channels (lists of floats in -1..1, of one length)."""
    if len(channels) == 1:
        data = _to_int16(channels[0])
    else:
        l, r = _to_int16(channels[0]), _to_int16(channels[1])
        data = array.array("h", bytes(4 * len(l)))
        data[0::2], data[1::2] = l, r
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(path, "wb") as w:
        w.setnchannels(len(channels))
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


def read_wav(path):
    """(rate, [channel, ...]) from a 16-bit PCM WAV (plain or WAVE_FORMAT_EXTENSIBLE, as afconvert writes for
    stereo), as floats in -1..1."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("%s is not a WAV file" % path)
    p, fmt, raw = 12, None, None
    while p + 8 <= len(data):
        kind, size = data[p:p + 4], struct.unpack("<I", data[p + 4:p + 8])[0]
        if kind == b"fmt ":
            fmt = struct.unpack("<HHIIHH", data[p + 8:p + 24])
        elif kind == b"data":
            raw = data[p + 8:p + 8 + size]
        p += 8 + size + (size & 1)
    if fmt is None or raw is None:
        raise ValueError("%s has no fmt or data chunk" % path)
    tag, ch, rate, _, _, bits = fmt
    if tag not in (1, 0xFFFE) or bits != 16:
        raise ValueError("%s: format %d, %d bits; only 16-bit PCM is read" % (path, tag, bits))
    samples = array.array("h", raw[:len(raw) - len(raw) % 2])
    if sys.byteorder != "little":
        samples.byteswap()
    k = 1 / 32768
    return rate, [[v * k for v in samples[c::ch]] for c in range(ch)]


def _ber(data, p):
    v = 0
    while True:
        b = data[p]
        p += 1
        v = (v << 7) | (b & 0x7F)
        if b < 0x80:
            return v, p


def read_caf_opus(path):
    """(channels, pre_skip, valid_frames, packets) from a CAF file afconvert wrote with `-d opus`."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"caff":
        raise ValueError("not a CAF file")
    p = 8
    channels = pre_skip = valid = None
    sizes, audio = None, None
    while p < len(data):
        kind = data[p:p + 4]
        size = struct.unpack(">q", data[p + 4:p + 12])[0]
        body = data[p + 12:] if size < 0 else data[p + 12:p + 12 + size]
        if kind == b"desc":
            _, fmt, _, _, fpp, channels, _ = struct.unpack(">d4sIIIII", body[:32])
            if fmt != b"opus" or fpp != 960:
                raise ValueError("unexpected CAF format %r, %d frames a packet" % (fmt, fpp))
        elif kind == b"pakt":
            count, valid, pre_skip, _ = struct.unpack(">qqii", body[:24])
            q, sizes = 24, []
            for _ in range(count):
                s, q = _ber(body, q)
                sizes.append(s)
        elif kind == b"data":
            audio = body[4:]
        if size < 0:
            break
        p += 12 + size
    if sizes is None or audio is None:
        raise ValueError("CAF file has no packet table or no data")
    packets, q = [], 0
    for s in sizes:
        packets.append(audio[q:q + s])
        q += s
    return channels, pre_skip, valid, packets


def _crc_table():
    table = []
    for i in range(256):
        r = i << 24
        for _ in range(8):
            r = ((r << 1) ^ 0x04C11DB7) if r & 0x80000000 else (r << 1)
        table.append(r & 0xFFFFFFFF)
    return table


_CRC = _crc_table()


def _ogg_crc(data):
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC[((crc >> 24) & 0xFF) ^ b]
    return crc


def _page(serial, seq, granule, packets, flags):
    lacing = bytearray()
    for pk in packets:
        lacing += bytes([255] * (len(pk) // 255) + [len(pk) % 255])
    assert len(lacing) <= 255
    header = struct.pack("<4sBBqIIIB", b"OggS", 0, flags, granule, serial, seq, 0, len(lacing))
    page = bytearray(header + lacing + b"".join(packets))
    struct.pack_into("<I", page, 22, _ogg_crc(page))
    return bytes(page)


def write_ogg_opus(path, channels, pre_skip, valid, packets, serial):
    head = struct.pack("<8sBBHIhB", b"OpusHead", 1, channels, pre_skip, RATE, 0, 0)
    tags = struct.pack("<8sI", b"OpusTags", len(VENDOR)) + VENDOR + struct.pack("<I", 0)
    out = [_page(serial, 0, 0, [head], 0x02), _page(serial, 1, 0, [tags], 0)]
    seq, granule, i = 2, 0, 0
    end = pre_skip + valid
    while i < len(packets):
        batch, lace = [], 0
        while i < len(packets) and len(batch) < 50:
            need = len(packets[i]) // 255 + 1
            if lace + need > 255:
                break
            batch.append(packets[i])
            lace += need
            i += 1
        granule += 960 * len(batch)
        last = i == len(packets)
        out.append(_page(serial, seq, min(granule, end) if last else granule, batch, 0x04 if last else 0))
        seq += 1
    with open(path, "wb") as f:
        f.write(b"".join(out))


def encode(channels, dest, bitrate, serial, tmp, context=0):
    """Writes `channels` (one or two lists of floats) to `dest` as Ogg Opus at about `bitrate` bits a second,
    working in the directory `tmp`, and returns its size in bytes. The file is written beside `dest` and moved
    over it, so a reader never sees half a file.

    `context` (samples, for a loop): the encoder is given the loop's last `context` samples before it and its
    first after it, and the extra is marked for the decoder to drop (a longer pre-skip, and the end granule at
    the loop's length). So the codec codes the seam as the middle of a sound rather than as a start and an end
    made separately, and a decoder that follows RFC 7845 returns exactly the loop."""
    n = len(channels[0])
    if context:
        channels = [c[n - context:] + c + c[:context] for c in channels]
    base = os.path.join(tmp, os.path.basename(dest))
    wav, caf = base + ".wav", base + ".caf"
    write_wav(wav, channels)
    subprocess.run(["/usr/bin/afconvert", "-f", "caff", "-d", "opus", "-b", str(int(bitrate)), wav, caf],
                   check=True, stdout=subprocess.DEVNULL)
    ch, pre_skip, valid, packets = read_caf_opus(caf)
    if valid != len(channels[0]):
        raise RuntimeError("%s: afconvert kept %s of %d frames" % (dest, valid, len(channels[0])))
    pre_skip += context
    if pre_skip > 0xFFFF:
        raise ValueError("context too long for Opus's 16-bit pre-skip")
    end = pre_skip + n
    packets = packets[:(end + 959) // 960]          # the packets wholly after the loop's end are not needed
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part%d" % os.getpid()
    write_ogg_opus(part, ch, pre_skip, n, packets, serial)
    os.replace(part, dest)
    for p in (wav, caf):
        os.remove(p)
    return os.path.getsize(dest)


def decode(path, tmp):
    """(rate, [channel, ...]) decoded from an Ogg Opus file by afconvert (16-bit), working in `tmp`."""
    wav = os.path.join(tmp, os.path.basename(path) + ".decoded.wav")
    subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", path, wav], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        return read_wav(wav)
    finally:
        os.remove(wav)
