// QModem: data between two screens and two cameras, one small QR code at a time. The reference implementation;
// Swift (Sources/QModem) and Kotlin (kotlin/qmodem) do the same and check vectors/qmodem.json, which this file writes
// (scripts/vectors.mjs). The protocol is spec/QMODEM.md. A session has no camera, no screen and no clock: the app
// shows `frame()`, hands every decoded code to `read`, calls `tick` on a timer, and passes the time in milliseconds.
(function (root) {
  "use strict";

  var B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  var C = {
    MIN_PIECE: 32, MAX_PIECE: 256, MAX_WINDOW: 8, CLEAN_TO_GROW: 2, MAX_CLEAN: 16,
    STALL_MS: 2000, CONFIRM_MS: 20000, LIMIT_MS: 120000, MAX_BYTES: 32768
  };
  var FRAME = /^app:t\.([a-z0-9]{4})\.([0-9a-z]{1,3})\.([0-9a-z]{1,3})\.([0-9a-z]{1,3})\.([A-Za-z0-9_-]*)$/;
  var DONE = /^app:d\.([a-z0-9]{4})$/;
  var ID = /^[a-z0-9]{4}$/;

  function encode(bytes) {
    var s = "", i = 0, n = bytes.length;
    for (; i + 2 < n; i += 3) {
      var v = (bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2];
      s += B64[v >> 18 & 63] + B64[v >> 12 & 63] + B64[v >> 6 & 63] + B64[v & 63];
    }
    if (n - i === 1) { var a = bytes[i] << 16; s += B64[a >> 18 & 63] + B64[a >> 12 & 63]; }
    else if (n - i === 2) { var b = (bytes[i] << 16) | (bytes[i + 1] << 8); s += B64[b >> 18 & 63] + B64[b >> 12 & 63] + B64[b >> 6 & 63]; }
    return s;
  }
  function decode(text) {
    if (text.length % 4 === 1) return null;
    var out = new Uint8Array(Math.floor(text.length * 3 / 4)), o = 0, acc = 0, bits = 0;
    for (var i = 0; i < text.length; i++) {
      var c = B64.indexOf(text[i]);
      if (c < 0) return null;
      acc = (acc << 6) | c; bits += 6;
      if (bits >= 8) { bits -= 8; out[o++] = (acc >> bits) & 255; }
    }
    return out;
  }
  function b36(n) { return n.toString(36); }

  // FNV-1a, 32 bits, of a string's UTF-16 units (the vectors only use ASCII).
  function fnv(text) {
    var h = 2166136261;
    for (var i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
    return h >>> 0;
  }
  // Made-up bytes from an id (mulberry32 seeded by FNV-1a), so the other side of a test can check what it got.
  function testBytes(id, n) {
    var a = fnv(id), out = new Uint8Array(n);
    for (var i = 0; i < n; i++) {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), a | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      out[i] = ((t ^ (t >>> 14)) >>> 0) & 255;
    }
    return out;
  }
  function newId() { var a = "abcdefghjkmnpqrstuvwxyz23456789", s = ""; for (var i = 0; i < 4; i++) s += a[Math.floor(Math.random() * a.length)]; return s; }

  // o: { data: bytes, id?: 4 of [a-z0-9], size: "grow" | 32 | 64 | 128 | 256, window: "grow" | 1 | 2 | 4 | 8, dwell: ms }
  function Session(o, now) {
    var id = o.id || newId(), size = o.size == null ? "grow" : o.size, win = o.window == null ? "grow" : o.window;
    if (!ID.test(id)) throw new Error("id must be 4 of a-z and 0-9");
    if (o.data.length > C.MAX_BYTES) throw new Error("at most " + C.MAX_BYTES + " bytes");
    if (size !== "grow" && [32, 64, 128, 256].indexOf(size) < 0) throw new Error("size: grow, 32, 64, 128 or 256");
    if (win !== "grow" && [1, 2, 4, 8].indexOf(win) < 0) throw new Error("window: grow, 1, 2, 4 or 8");
    this.id = id; this.text = encode(o.data); this.total = this.text.length;
    this.sizeMode = size; this.windowMode = win; this.dwell = o.dwell == null ? 250 : o.dwell;
    this.pieceSize = size === "grow" ? C.MIN_PIECE : size; this.window = win === "grow" ? 1 : win;
    this.need = C.CLEAN_TO_GROW; this.clean = 0; this.acked = 0;
    this.peer = null; this.peerTotal = null; this.got = null; this.have = null; this.held = 0;
    this.done = false; this.peerDone = false; this.ended = null; this.endedAt = null;
    this.t0 = now; this.firstRead = null; this.lastAdvance = now; this.doneAt = null; this.peerDoneAt = null; this.sentAt = null; this.heldAt = null;
    this.stalls = 0; this.advances = 0; this.reads = 0; this.foreign = 0;
    this.log = []; this.sizes = [this.pieceSize]; this.windows = [this.window];
    this.rebuild(now);
  }
  var S = Session.prototype;

  S.note = function (t, what) { this.log.push((t - this.t0) + " " + what); };
  S.rebuild = function (t) {
    this.pieces = [];
    for (var off = this.acked; off < this.total && this.pieces.length < this.window; off += this.pieceSize) this.pieces.push([off, Math.min(this.pieceSize, this.total - off)]);
    this.idx = 0; this.shownAt = t;
  };
  // The piece showing now, [offset, length]; [total, 0] when the other holds everything.
  S.current = function () { return this.pieces.length ? this.pieces[this.idx] : [this.total, 0]; };
  S.frame = function () {
    if (this.done) return "app:d." + this.id;
    var p = this.current();
    return "app:t." + this.id + "." + b36(this.total) + "." + b36(p[0]) + "." + b36(this.held) + "." + this.text.substr(p[0], p[1]);
  };
  // What the other sent, once all of it is held.
  S.received = function () { return this.peerTotal !== null && this.held === this.peerTotal ? decode(this.got.join("")) : null; };

  S.end = function (t, how, ev) { if (this.ended) return; this.ended = how; this.endedAt = t; this.note(t, "ended " + how); ev.push("end"); };
  S.stop = function (t) { var ev = []; this.end(t, "stopped", ev); return ev; };
  S.becomeDone = function (t, ev) { if (this.done) return; this.done = true; this.doneAt = t; this.note(t, "done"); ev.push("done"); };
  S.grow = function (t) {
    if (this.sizeMode === "grow" && this.pieceSize < C.MAX_PIECE) { this.pieceSize *= 2; this.sizes.push(this.pieceSize); this.note(t, "size " + this.pieceSize); return true; }
    if (this.windowMode === "grow" && this.window < C.MAX_WINDOW) { this.window *= 2; this.windows.push(this.window); this.note(t, "window " + this.window); return true; }
    return false;
  };
  S.shrink = function (t) {
    if (this.windowMode === "grow" && this.window > 1) { this.window /= 2; this.windows.push(this.window); }
    if (this.sizeMode === "grow" && this.pieceSize > C.MIN_PIECE) { this.pieceSize /= 2; this.sizes.push(this.pieceSize); }
    this.need = Math.min(this.need * 2, C.MAX_CLEAN); this.clean = 0;
    this.note(t, "stall " + this.acked + " size " + this.pieceSize + " window " + this.window);
  };

  // The clock: the time limits, stalls, the window turning over. Returns what happened.
  S.tick = function (t) {
    var ev = [];
    if (this.ended) return ev;
    if (this.done) { if (!this.peerDone && t - this.doneAt > C.CONFIRM_MS) this.end(t, "unconfirmed", ev); return ev; }
    if (t - this.t0 > C.LIMIT_MS) { this.end(t, "timeout", ev); return ev; }
    if (this.peer && this.acked < this.total && t - this.lastAdvance > C.STALL_MS) {
      this.stalls++; this.shrink(t); this.lastAdvance = t; this.rebuild(t); ev.push("stall");
    } else if (this.pieces.length > 1 && t - this.shownAt >= this.dwell) {
      this.idx = (this.idx + 1) % this.pieces.length; this.shownAt = t; ev.push("show");
    }
    return ev;
  };

  // One code the camera decoded. The same code arrives many times a second, so every branch is idempotent.
  S.read = function (text, t) {
    var ev = [], m = null, d = DONE.exec(text);
    if (this.ended) return ev;
    this.reads++;
    if (!d && !(m = FRAME.exec(text))) { this.foreign++; return ev; }
    var id = d ? d[1] : m[1];
    if (id === this.id) return ev;                      // our own code, in a mirror or glare
    if (!this.peer) { this.peer = id; this.firstRead = t - this.t0; this.lastAdvance = t; this.note(t, "found " + id); ev.push("found"); }
    if (id !== this.peer) { this.foreign++; return ev; }

    if (d) {
      // The other holds all of ours and saw that we hold all of theirs.
      if (!this.peerDone) { this.peerDone = true; this.peerDoneAt = t; this.note(t, "peer done"); }
      if (this.peerTotal === null) { this.peerTotal = 0; this.got = []; this.have = new Uint8Array(0); this.heldAt = t; }
      if (this.acked < this.total) { this.acked = this.total; }
      if (this.sentAt === null) this.sentAt = t;
      this.becomeDone(t, ev);
      this.end(t, "complete", ev);
      return ev;
    }
    if (this.done) return ev;

    var total = parseInt(m[2], 36), off = parseInt(m[3], 36), ack = parseInt(m[4], 36), data = m[5];
    if (this.peerTotal !== null && total !== this.peerTotal) { this.foreign++; return ev; }
    // Their acknowledgement of ours.
    if (ack > this.acked && ack <= this.total) {
      this.acked = ack; this.advances++; this.lastAdvance = t; ev.push("advance");
      if (this.acked === this.total) { this.sentAt = t; this.note(t, "sent all"); }
      else if (++this.clean >= this.need) { this.clean = 0; if (this.grow(t)) ev.push("grow"); }
      this.rebuild(t);
    }
    // Their data.
    if (this.peerTotal === null) {
      this.peerTotal = total; this.got = new Array(total); this.have = new Uint8Array(total);
      if (total === 0) this.heldAt = t;
    }
    if (data.length && off + data.length <= this.peerTotal) {
      for (var i = 0; i < data.length; i++) { this.got[off + i] = data[i]; this.have[off + i] = 1; }
      var before = this.held;
      while (this.held < this.peerTotal && this.have[this.held]) this.held++;
      if (this.held !== before) { ev.push("held"); if (this.held === this.peerTotal) { this.heldAt = t; this.note(t, "held all"); } }
    }
    if (this.held === this.peerTotal && this.acked === this.total) this.becomeDone(t, ev);
    return ev;
  };

  // Two sessions and a lossy pair of cameras, every step fixed, so all three implementations can be compared
  // (spec/QMODEM.md, "Vectors"). Each side reads the other's code every 120 ms, 80 ms apart, and misses a read when
  // the generator says so.
  function simulate(c) {
    var s = c.seed;
    var rnd = function () { s = (s * 48271) % 2147483647; return s / 2147483647; };   // MINSTD: exact in a double
    var mk = function (id, other) { return new Session({ data: testBytes(id, c.bytes), id: id, size: c.size, window: c.window, dwell: c.dwell }, 0); };
    var a = mk("aaaa"), b = mk("bbbb"), t = 0, ta = [a.frame()], tb = [b.frame()];
    while (t < 200000 && !(a.ended && b.ended)) {
      t += 40;
      a.tick(t); b.tick(t);
      if (t % 120 === 0 && rnd() > c.loss) a.read(b.frame(), t);
      if (t % 120 === 80 && rnd() > c.loss) b.read(a.frame(), t);
      var fa = a.frame(), fb = b.frame();
      if (fa !== ta[ta.length - 1]) ta.push(fa);
      if (fb !== tb[tb.length - 1]) tb.push(fb);
    }
    var same = function (x, y) { if (!x || x.length !== y.length) return false; for (var i = 0; i < x.length; i++) if (x[i] !== y[i]) return false; return true; };
    var side = function (p, trace, other) {
      return { ended: p.ended, endedAt: p.endedAt, sizes: p.sizes, windows: p.windows, stalls: p.stalls, advances: p.advances,
               received: same(p.received(), testBytes(other, c.bytes)), frames: trace.length, trace: fnv(trace.join("\n")), log: p.log };
    };
    return { t: t, a: side(a, ta, "bbbb"), b: side(b, tb, "aaaa"), traceA: ta };
  }

  var QModem = { Session: Session, encode: encode, decode: decode, testBytes: testBytes, fnv: fnv, newId: newId, simulate: simulate, constants: C };
  if (typeof module === "object" && module.exports) module.exports = QModem; else root.QModem = QModem;
})(typeof self !== "undefined" ? self : this);
