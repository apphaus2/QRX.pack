"""The soundscape toolkit. A recipe starts with `from lib import *` and gets everything below; README.md lists
the signatures. The build calls the recipe inside the right loop mode (lib.core), so nothing here needs to be
told whether it is making a bed or a cue.
"""
from .core import (BED_SECONDS, CONTROL_RATE, RATE, cue, db, samples, undb)
from .noise import NOISE_RMS, blue, brown, pink, rms, set_rms, white
from .filters import (allpass, band, bandpass, highpass, highshelf, lowpass, moving_lowpass, onepole_highpass,
                      onepole_lowpass, peak)
from .control import apply, constant, drift, gusts, points, scale, smooth, stretch, swell
from .scatter import chorus, scatter
from .mix import add, decorrelate, gain, mix, pan, pan_gains, place, remove_dc, soft_limit, stereo, widen
from .voices import (bell, caw, chirp, churr, creak, croak, decay, distant, envelope, hoot, knock, noise_burst,
                     overlay, phrase, roll, seq, silence, snap, space, tone, trill, trim)

import types as _types

__all__ = [_name for _name, _value in list(globals().items())
           if not _name.startswith("_") and not isinstance(_value, _types.ModuleType)]
