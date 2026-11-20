// Builds the AR/Collections long-tail social cards (SVG + PNG).
// Usage (from this folder):  node build_cards.mjs
// PNG rendering uses macOS QuickLook (qlmanage); run on a Mac.
// MILESTONES/CAP mirror the AR cadence in backend/app/services/ar_aging.py (30/60/90/120/180).
// If the cadence changes, edit them here and re-run so the cards match the product.
import { writeFileSync, mkdirSync, renameSync, readFileSync, unlinkSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const MILESTONES = [30, 60, 90, 120, 180]
const LONG_TAIL = 120
const CAP = 180
const TEAL = '#00C2A8'
const NAVY = '#0B1B2B'
const SLATE = '#5C7089'
const FONT = "Inter, -apple-system, 'Helvetica Neue', Arial, sans-serif"
const here = dirname(fileURLToPath(import.meta.url))
const outDir = join(here, 'out')
mkdirSync(outDir, { recursive: true })

const MARK = 'M 30 22 C 30 14 38 10 46 14 C 50 16 50 16 54 14 C 62 10 70 14 70 22 C 70 30 66 34 64 42 C 62 52 60 62 56 76 C 55 80 50 80 49 76 C 47 66 46 58 45 50 C 44 58 43 66 41 76 C 40 80 35 80 34 76 C 30 62 28 52 26 42 C 24 34 30 30 30 22 Z'

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
const text = (x, y, s, { size, weight = 700, fill = '#fff', anchor = 'start', spacing = 0 }) =>
  `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${spacing}">${esc(s)}</text>`

function logo(x, y, k) {
  return `<g transform="translate(${x},${y}) scale(${k})">
    <path d="${MARK}" transform="translate(-20,-6)" stroke="${TEAL}" stroke-width="6" stroke-linejoin="round" fill="none"/>
    <text x="52" y="40" font-family="${FONT}" font-size="38" font-weight="900" letter-spacing="-1" fill="#fff">Ortho<tspan fill="${TEAL}">Flow</tspan></text>
  </g>`
}

// ---- body renderers (all return svg for the area below the headline) ----
function timeline(W, y) {
  const x0 = 80, x1 = W - 80, w = x1 - x0
  const px = (d) => x0 + (w * d) / CAP
  const tail = px(LONG_TAIL)
  const ticks = MILESTONES.map((m) => `
    <circle cx="${px(m)}" cy="${y + 13}" r="15" fill="${m >= LONG_TAIL ? NAVY : TEAL}" stroke="${m >= LONG_TAIL ? '#fff' : NAVY}" stroke-width="3"/>
    ${text(px(m), y + 64, `${m}`, { size: 24, fill: m >= LONG_TAIL ? TEAL : '#fff', anchor: 'middle' })}`).join('')
  return `
    <rect x="${x0}" y="${y}" width="${tail - x0 - 4}" height="26" rx="13" fill="#1B3550"/>
    <rect x="${tail}" y="${y}" width="${x1 - tail}" height="26" rx="13" fill="${TEAL}" opacity="0.55"/>
    ${ticks}
    ${text(x0, y + 104, 'Days past due', { size: 20, weight: 500, fill: '#9FB3C8' })}
    ${text(x1, y + 104, 'The long tail many tools drop', { size: 20, weight: 700, fill: TEAL, anchor: 'end' })}`
}

function bullets(W, y, items, gap) {
  return items
    .map((t, i) => `
    <circle cx="${92}" cy="${y + i * gap - 8}" r="15" fill="${TEAL}"/>
    <path d="M 84 ${y + i * gap - 8} l 6 6 l 11 -12" stroke="${NAVY}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    ${text(124, y + i * gap, t, { size: 30, weight: 600 })}`)
    .join('')
}

function flow(W, y) {
  const steps = [
    ['Verify coverage', 'Stedi'],
    ['Send claims', 'Stedi'],
    ['Pay by bank', 'Plaid'],
    ['Follow up', '30 to 180 days'],
  ]
  const gap = 18
  const bw = (W - 160 - gap * 3) / 4
  return steps
    .map(([a, b], i) => {
      const x = 80 + i * (bw + gap)
      const hot = i === 3
      return `
      <rect x="${x}" y="${y}" width="${bw}" height="104" rx="18" fill="${hot ? TEAL : '#1B3550'}"/>
      ${text(x + bw / 2, y + 46, a, { size: 23, fill: hot ? NAVY : '#fff', anchor: 'middle' })}
      ${text(x + bw / 2, y + 78, b, { size: 23, weight: 500, fill: hot ? NAVY : '#9FB3C8', anchor: 'middle' })}`
    })
    .join('')
}

const cards = [
  {
    id: 'long-tail-1-cadence',
    eyebrow: 'AR & COLLECTIONS LONG TAIL',
    head: ['Many billing tools stop', 'at 90 to 120 days.'],
    accent: ['We follow up through 180.'],
    body: (W, y) => timeline(W, y),
    foot: 'Orthodontic balances only. Your team reviews every message.',
  },
  {
    id: 'long-tail-2-unfinished',
    eyebrow: 'AR & COLLECTIONS LONG TAIL',
    head: [`Past ${LONG_TAIL} days isn't`, 'lost revenue.'],
    accent: ["It's unfinished follow-up."],
    body: (W, y, land) =>
      bullets(W, y + 18, ['Reminders at 30, 60, 90, 120 and 180 days', 'A secure pay link by text to MyOrthoChart', 'Automatic or manual. You choose.'], land ? 52 : 62),
    foot: 'Automatic reminders are off until you turn them on.',
  },
  {
    id: 'long-tail-3-stedi-plaid',
    eyebrow: 'POWERED BY STEDI AND PLAID',
    head: ['Verify. Bill. Collect.', 'In one orthodontic platform.'],
    accent: ['Then keep following up.'],
    body: (W, y) => flow(W, y),
    foot: 'Insurance checks and claims by Stedi. Bank payments by Plaid.',
  },
]

function render(card, W, H) {
  const land = W > H
  const hs = land ? 46 : 74
  const lh = land ? 54 : 88
  const top = land ? 236 : 310
  let y = top
  const headSvg = card.head.map((l, i) => text(80, y + i * lh, l, { size: hs, weight: 800 })).join('')
  y += (card.head.length - 1) * lh + lh
  const accent = card.accent.map((l, i) => text(80, y + i * lh, l, { size: hs, weight: 800, fill: TEAL })).join('')
  y += (card.accent.length - 1) * lh
  const bodyY = y + (land ? 34 : 90)
  const body = card.body(W, bodyY, land)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs><radialGradient id="g" cx="85%" cy="10%" r="70%"><stop offset="0" stop-color="${TEAL}" stop-opacity="0.22"/><stop offset="1" stop-color="${TEAL}" stop-opacity="0"/></radialGradient></defs>
  <rect width="${W}" height="${H}" fill="${NAVY}"/>
  <rect width="${W}" height="${H}" fill="url(#g)"/>
  ${logo(land ? 80 : 70, land ? 34 : 52, land ? 0.7 : 1)}
  ${text(80, land ? 176 : 236, card.eyebrow, { size: 22, weight: 700, fill: TEAL, spacing: 3 })}
  ${headSvg}${accent}${body}
  <rect x="80" y="${H - 86}" width="${W - 160}" height="1" fill="#1B3550"/>
  ${text(80, H - 44, card.foot, { size: land ? 20 : 22, weight: 500, fill: '#9FB3C8' })}
  ${text(W - 80, H - 44, 'orthoflowsolutions.com', { size: land ? 20 : 22, weight: 700, fill: '#fff', anchor: 'end' })}
</svg>`
}

const sizes = [
  ['square', 1080, 1080],
  ['landscape', 1200, 627],
]
const files = []
for (const c of cards) {
  for (const [name, W, H] of sizes) {
    const base = `${c.id}-${name}`
    writeFileSync(join(outDir, `${base}.svg`), render(c, W, H))
    files.push([base, W, H])
  }
}

// Render PNGs with macOS QuickLook (qlmanage), which only outputs square thumbnails.
// Wide cards are rendered on a square canvas and cropped back with sips.
for (const [base, W, H] of files) {
  const svgPath = join(outDir, `${base}.svg`)
  const src = readFileSync(svgPath, 'utf8')
  const tmp = join(outDir, `_tmp_${base}.svg`)
  const side = Math.max(W, H)
  const dy = (side - H) / 2
  const wrapped = src
    .replace(`width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`, `width="${side}" height="${side}" viewBox="0 0 ${side} ${side}"><g transform="translate(0,${dy})">`)
    .replace('</svg>', '</g></svg>')
  writeFileSync(tmp, wrapped)
  execFileSync('qlmanage', ['-t', '-s', String(side), '-o', outDir, tmp], { stdio: 'ignore' })
  const png = join(outDir, `${base}.png`)
  renameSync(`${tmp}.png`, png)
  if (H !== side) execFileSync('sips', ['--cropToHeightWidth', String(H), String(W), png], { stdio: 'ignore' })
  unlinkSync(tmp)
}
console.log(`wrote ${files.length} cards to ${outDir}`)
