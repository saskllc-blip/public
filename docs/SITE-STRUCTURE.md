# SASK public site structure

Static GitHub Pages site served from `/docs`.

## Pages

| Path | Role |
|---|---|
| `index.html` | Home — short products + services landing (dark) |
| `products/keepers.html` | Keepers product page (Coming soon) |
| `services.html` | Three services + contact (verbatim copy) |
| `how-we-work.html` | Process steps (verbatim) |
| `demos.html` | Demo projects incl. MediAssist (verbatim) |
| `open-source.html` | Public repo showroom (verbatim) |
| `founder.html` | Founder bio (verbatim) |
| `keepers-privacy.html` | Keepers privacy policy — **do not rename/move** |
| `google5dc10e1d3112c2c9.html` | Google site verification — **do not rename/move** |

## Shared assets

- `styles.css` — shared near-black theme (`#0a0a0c` family)
- `assets/` — compressed Keepers splash derivatives + K-mark crop

## Constraints

- No build step, no new dependencies
- Products nav is a CSS/`<details>` dropdown (no JS required for open)
- Protected privacy + Google verification files must remain byte-identical at their current URLs
