// Lamp.jsx — THE CUTE TABLE LAMP (our logo). Click it (or its pull cord) to turn it on/off.
//
// How to use it:
//   <Lamp on={lampOn} onToggle={() => setLampOn(!lampOn)} />
//
// It is drawn with SVG (shapes described in code). Both looks are drawn on top of
// each other, and we fade between them:
//   OFF → dark shade, sleeping face  (-‿-)
//   ON  → sage-green shade, happy face (^▽^), and a cone of light shining down
//
// Drawing area: 240 wide x 400 tall.

export default function Lamp({ on, onToggle }) {
  // Shows a layer only when "show" is true, with a smooth fade.
  const fade = (show) => "transition-opacity duration-500 " + (show ? "opacity-100" : "opacity-0");

  // The shade shape: narrow at the top, wide at the bottom, slightly rounded corners.
  const shade = "M70 62 L170 62 Q177 62 179 69 L208 163 Q211 172 202 172 L38 172 Q29 172 32 163 L61 69 Q63 62 70 62 Z";

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={on} // tells screen readers whether the lamp is on
      aria-label={on ? "Turn the lamp off" : "Turn the lamp on to sign in"}
      className="group cursor-pointer rounded-3xl focus-visible:outline-2 focus-visible:outline-offset-8 focus-visible:outline-sage"
    >
      <svg viewBox="0 0 240 400" className="h-auto w-44 overflow-visible md:w-60" aria-hidden="true">
        <defs>
          {/* Light cone: bright under the shade, fading out toward the floor. */}
          <linearGradient id="lamp-beam" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f5f1d2" stopOpacity="0.38" />
            <stop offset="100%" stopColor="#f5f1d2" stopOpacity="0" />
          </linearGradient>
          {/* Shade colors: a lighter left side makes it look round. */}
          <linearGradient id="shade-on" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#b3d3ae" />
            <stop offset="55%" stopColor="#93b98f" />
            <stop offset="100%" stopColor="#7aa377" />
          </linearGradient>
          <linearGradient id="shade-off" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#353a40" />
            <stop offset="100%" stopColor="#202428" />
          </linearGradient>
          {/* Metal of the stem and base. */}
          <linearGradient id="metal-on" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#f0f1f3" />
            <stop offset="100%" stopColor="#b9bdc4" />
          </linearGradient>
          <linearGradient id="metal-off" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#5a5f67" />
            <stop offset="100%" stopColor="#3a3e44" />
          </linearGradient>
          {/* A soft blur, used for the glows. */}
          <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="8" />
          </filter>
        </defs>

        {/* ---------- Light (only when on) ---------- */}
        <g className={fade(on)}>
          {/* The cone of light falling from the shade to the floor. */}
          <path d="M38 174 L202 174 L270 392 L-30 392 Z" fill="url(#lamp-beam)" />
          {/* A pool of light on the floor around the base. */}
          <ellipse cx="120" cy="372" rx="110" ry="16" fill="#f5f1d2" opacity="0.18" filter="url(#soft)" />
        </g>

        {/* ---------- Stem and base ---------- */}
        <rect x="114" y="170" width="12" height="178" rx="3" fill="url(#metal-off)" />
        <rect x="114" y="170" width="12" height="178" rx="3" fill="url(#metal-on)" className={fade(on)} />
        {/* Base: a flat disc (side + top). */}
        <path d="M58 352 L58 362 Q120 384 182 362 L182 352 Z" fill={on ? "#a7abb3" : "#2f3338"} className="transition-colors duration-500" />
        <ellipse cx="120" cy="352" rx="62" ry="13" fill={on ? "url(#metal-on)" : "url(#metal-off)"} />

        {/* ---------- Pull cord (dips down while you click) ---------- */}
        <g className="transition-transform duration-150 group-active:translate-y-2">
          <line x1="72" y1="172" x2="72" y2="252" stroke={on ? "#e8e9ec" : "#6b7078"} strokeWidth="2.5" strokeLinecap="round" className="transition-colors duration-500" />
          <rect x="68" y="250" width="8" height="18" rx="4" fill={on ? "#e8e9ec" : "#8a9099"} className={"transition-colors duration-500 " + (on ? "" : "lamp-hint")} />
        </g>

        {/* ---------- Shade ---------- */}
        <path d={shade} fill="url(#shade-off)" />
        <path d={shade} fill="url(#shade-on)" className={fade(on)} />
        {/* Glowing rim under the shade (where the bulb is). */}
        <ellipse cx="120" cy="171" rx="86" ry="6" fill={on ? "#f5f1d2" : "#15181b"} className="transition-colors duration-500" />
        <ellipse cx="120" cy="171" rx="86" ry="9" fill="#f5f1d2" filter="url(#soft)" className={fade(on)} />

        {/* ---------- Face: asleep (off) ---------- */}
        <g className={fade(!on)} stroke="#0c0e10" strokeWidth="3" strokeLinecap="round" fill="none">
          <path d="M88 116 Q97 124 106 116" />
          <path d="M134 116 Q143 124 152 116" />
        </g>

        {/* ---------- Face: happy (on) ---------- */}
        <g className={fade(on)}>
          {/* Happy closed eyes ^ ^ */}
          <g stroke="#1d2a1d" strokeWidth="3.5" strokeLinecap="round" fill="none">
            <path d="M88 118 Q97 106 106 118" />
            <path d="M134 118 Q143 106 152 118" />
          </g>
          {/* Rosy cheeks */}
          <ellipse cx="84" cy="131" rx="8" ry="5" fill="#f19aa0" opacity="0.55" />
          <ellipse cx="156" cy="131" rx="8" ry="5" fill="#f19aa0" opacity="0.55" />
          {/* Open smile with a little tongue */}
          <path d="M106 126 Q120 148 134 126 Z" fill="#2a1b1d" />
          <path d="M115 137 Q121 147 129 138 Q123 134 115 137 Z" fill="#ec7b86" />
        </g>
      </svg>
    </button>
  );
}
