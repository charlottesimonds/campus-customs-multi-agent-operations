// Original line-art motifs inspired by Yale and New Haven. These are drawn for this
// project. They are not official Yale marks, crests, or logos, and they depict no real person.

type Props = { className?: string; size?: number; title?: string }

const stroke = { fill: 'none', stroke: 'currentColor', strokeLinecap: 'round', strokeLinejoin: 'round' } as const

/** A friendly bulldog, sketched in a single weight of line. */
export function Bulldog({ className, size = 64, title }: Props) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 120 120" role={title ? 'img' : undefined} aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      <g {...stroke} strokeWidth={2.6}>
        {/* folded ears at the top corners */}
        <path d="M33 37 C25 25 14 26 11 35 C18 37 25 41 29 46" />
        <path d="M87 37 C95 25 106 26 109 35 C102 37 95 41 91 46" />
        {/* wide, flat-topped head with heavy cheeks */}
        <path d="M28 44 C30 28 44 21 60 21 C76 21 90 28 92 44 C103 50 107 65 103 79 C99 95 81 103 60 103 C39 103 21 95 17 79 C13 65 17 50 28 44 Z" />
        {/* forehead crease and heavy brows */}
        <path d="M51 34 Q60 30 69 34" />
        <path d="M60 36 V45" />
        <path d="M36 49 Q44 44 52 49" />
        <path d="M68 49 Q76 44 84 49" />
        {/* broad muzzle */}
        <path d="M37 75 C37 63 49 58 60 63 C71 58 83 63 83 75 C83 85 73 89 60 87 C47 89 37 85 37 75 Z" />
        <path d="M60 71 V78" />
        {/* jutting lower jaw with two teeth showing */}
        <path d="M41 89 Q60 101 79 89" />
        <path d="M49 92 L50.5 86.5" />
        <path d="M71 92 L69.5 86.5" />
        {/* droopy jowls */}
        <path d="M33 82 C31 92 39 99 47 96" />
        <path d="M87 82 C89 92 81 99 73 96" />
      </g>
      <g fill="currentColor">
        <circle cx="44" cy="56" r="3.6" />
        <circle cx="76" cy="56" r="3.6" />
        <path d="M50.5 64 Q60 57.5 69.5 64 Q65.5 71.5 60 71.5 Q54.5 71.5 50.5 64 Z" />
      </g>
    </svg>
  )
}

/** A collegiate Gothic tower: lancet windows, corner pinnacles, a spire. */
export function GothicTower({ className, size = 220 }: Props) {
  return (
    <svg className={className} height={size} width={size * 0.42} viewBox="0 0 120 286" aria-hidden>
      <g {...stroke} strokeWidth={1.6}>
        <path d="M60 4 V14" />
        <path d="M44 52 L60 14 L76 52" />
        <rect x="44" y="52" width="32" height="40" />
        <path d="M54 86 V66 Q57 59 60 66 V86 M60 66 Q63 59 66 66 V86" />
        <path d="M38 92 L41 77 L44 92 M76 92 L79 77 L82 92" />
        <rect x="38" y="92" width="44" height="60" />
        <path d="M47 144 V112 Q51 102 55 112 V144 M65 144 V112 Q69 102 73 112 V144" />
        <path d="M30 152 L34 132 L38 152 M82 152 L86 132 L90 152" />
        <rect x="30" y="152" width="60" height="130" />
        <path d="M48 282 V236 Q60 214 72 236 V282" />
        <path d="M40 206 V178 Q44 170 48 178 V206 M72 206 V178 Q76 170 80 178 V206" />
        <path d="M30 168 H90 M38 106 H82" strokeDasharray="2 4" />
      </g>
    </svg>
  )
}

/** An elm leaf, for the Elm City. */
export function ElmLeaf({ className, size = 90 }: Props) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 60 80" aria-hidden>
      <g {...stroke} strokeWidth={1.5}>
        <path d="M30 6 C46 16 52 36 40 56 C36 63 32 68 30 74 C27 66 22 62 18 55 C8 36 14 16 30 6 Z" />
        <path d="M30 6 C30 30 30 52 30 78" />
        <path d="M30 22 L40 16 M30 32 L44 25 M30 42 L46 36 M30 52 L42 48 M30 27 L19 20 M30 37 L16 31 M30 47 L15 42 M30 57 L19 54" />
      </g>
    </svg>
  )
}

/** A Gothic quatrefoil, the four-lobed ornament found in tracery. */
export function Quatrefoil({ className, size = 18 }: Props) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 40 40" aria-hidden>
      <g {...stroke} strokeWidth={2.2}>
        <path d="M20 4 a8 8 0 0 1 8 8 a8 8 0 0 1 0 16 a8 8 0 0 1 -16 0 a8 8 0 0 1 0 -16 a8 8 0 0 1 8 -8 Z" />
        <rect x="16" y="16" width="8" height="8" transform="rotate(45 20 20)" />
      </g>
    </svg>
  )
}

/** A campus pennant for the shop (no university wordmark). */
export function Pennant({ className, size = 120 }: Props) {
  return (
    <svg className={className} width={size} height={size * 0.3} viewBox="0 0 170 50" aria-hidden>
      <path d="M6 4 L164 25 L6 46 Z" fill="currentColor" />
      <path d="M3 2 V48" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <text x="14" y="29" fontFamily="var(--serif)" fontSize="9" fontWeight="700" letterSpacing="0.9" fill="var(--paper)">
        CAMPUS CUSTOMS
      </text>
    </svg>
  )
}

/** A New Haven skyline in line art: elms, cloister arches, and a Gothic tower. */
export function Skyline({ className }: Props) {
  const elm = (x: number, s = 1) => (
    <g transform={`translate(${x} 0) scale(${s})`} key={x}>
      <path d="M0 108 V78 M0 90 L-9 80 M0 86 L10 74" />
      <path d="M-22 76 C-34 72 -32 54 -18 54 C-20 38 2 32 8 46 C22 40 32 56 22 66 C30 76 16 86 6 80 C0 88 -16 86 -22 76 Z" />
    </g>
  )
  const arches = (x0: number, n: number) =>
    Array.from({ length: n }, (_, i) => {
      const x = x0 + i * 34
      return <path key={x} d={`M${x} 108 V82 Q${x + 14} 62 ${x + 28} 82 V108`} />
    })
  return (
    <svg className={className} viewBox="0 0 1200 112" preserveAspectRatio="xMidYMax meet" aria-hidden>
      <g {...stroke} strokeWidth={1.4}>
        <path d="M0 108 H1200" />
        {elm(90, 1.1)}
        {elm(170, 0.85)}
        {arches(230, 7)}
        <path d="M222 108 V70 H476 V108 M222 70 L230 60 L238 70 M460 70 L468 60 L476 70" />
        {elm(540, 1.25)}
        <g transform="translate(560 -2) scale(0.385)">
          <path d="M60 4 V14 M44 52 L60 14 L76 52 M38 92 L41 77 L44 92 M76 92 L79 77 L82 92 M30 152 L34 132 L38 152 M82 152 L86 132 L90 152" />
          <rect x="44" y="52" width="32" height="40" />
          <rect x="38" y="92" width="44" height="60" />
          <rect x="30" y="152" width="60" height="130" />
          <path d="M48 282 V236 Q60 214 72 236 V282 M47 144 V112 Q51 102 55 112 V144 M65 144 V112 Q69 102 73 112 V144" />
        </g>
        {elm(660, 1.05)}
        {arches(720, 8)}
        <path d="M712 108 V70 H1000 V108 M712 70 L720 60 L728 70 M984 70 L992 60 L1000 70" />
        {elm(1060, 1.15)}
        {elm(1135, 0.8)}
      </g>
    </svg>
  )
}
