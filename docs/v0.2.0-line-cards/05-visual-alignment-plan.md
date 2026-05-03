# Visual Alignment Plan: LINE Flex Cards vs Mock

เอกสารนี้เป็นแผนทำให้ card ที่ส่งจริงใน LINE มี visual language ใกล้กับ mock reference มากขึ้น โดยยังไม่แก้ code ในรอบเอกสารนี้

เป้าหมายไม่ใช่ pixel-perfect 100% เพราะ LINE Flex มีข้อจำกัดเรื่อง shadow, gradient, font rendering และปุ่มบางแบบ แต่ควรทำให้ผู้ใช้รู้สึกว่า card จริงกับ mock มาจาก design system เดียวกัน

## Current Gap

| Area | LINE card ปัจจุบัน | Mock reference | Desired direction |
| --- | --- | --- | --- |
| Overall shape | data/status card ที่ยาว | illustrated compact card | ใช้ compact card shell ที่ซ้ำได้ |
| Hero | solid green text hero | white hero with title + mascot | ใช้ header แบบ title + short subtitle + optional image |
| Visual cue | ไม่มี mascot/image | mascot/solar illustration | ใช้ image asset ใน hero/thumbnail |
| Step marker | ไม่มี | วงกลมเลข step | เพิ่ม optional `step_badge` |
| Copy | paragraph ยาว | copy สั้น 1-2 บรรทัด | ลด body text ให้ scan ได้ |
| Secondary button | gray filled | white outline | ใช้ outline/light button style |
| Empty/complete state | แสดง `เครื่องถัดไป -` | ซ่อน field ที่ไม่เกี่ยว | ซ่อน row ที่ไม่มี value จริง |
| Card family | แต่ละ card เริ่มต่างกัน | pattern เดียวกัน | สร้าง shared card shell |

## Target Fidelity

เลือกเป้าหมายเป็น **near-match within LINE Flex**:

- layout, hierarchy, copy, color และ asset placement ต้องใกล้ mock
- shadow/rounded corner ใช้เท่าที่ LINE Flex รองรับ
- image/mascot ใช้เป็น raster asset เพื่อให้ mood ใกล้ mock
- ถ้า Flex ทำไม่ได้ ให้ใช้ visual approximation ที่ stable บน LINE mobile

## Shared Card Shell

สร้าง design spec สำหรับ card shell กลางก่อน implement:

| Slot | Required | Description |
| --- | --- | --- |
| `step_badge` | optional | วงกลมเลขลำดับ เช่น `1`, ใช้ใน help/tutorial หรือ first-step card |
| `title` | required | หัวข้อหลัก เช่น `เริ่มบันทึกมิเตอร์` |
| `subtitle` | optional | context สั้น เช่น `รอบสัปดาห์นี้ M1-M8` |
| `hero_image_url` | optional | mascot/solar/report thumbnail |
| `body_items` | optional | bullet/metric rows สั้น ๆ |
| `status_badge` | optional | progress/role/warning badge |
| `primary_action` | required for actionable cards | green filled button |
| `secondary_actions` | optional | outline/light buttons, max 2 visible |
| `quick_replies` | optional | ใช้กับ M1-M8 หรือ fallback actions |

Rules:

- primary action มีได้ 1 ปุ่ม
- body text ไม่เกิน 2 บรรทัดต่อ section
- ซ่อน row ที่ value เป็น `None`, `-`, หรือไม่เกี่ยวกับ state
- card shell ต้องใช้กับ Start, Meter Request, OCR Confirmation และ Status ได้โดยไม่แตก layout

## Start Collection Card Target

Start Collection เป็น card แรกที่ควรปรับ เพราะต่างจาก mock ชัดที่สุดและเป็น entry point หลัก

Target content:

| Slot | Value |
| --- | --- |
| `step_badge` | `1` |
| `title` | `เริ่มบันทึกมิเตอร์` |
| `subtitle` | `รอบสัปดาห์นี้ M1-M8` หรือ `รอบสัปดาห์นี้ M1-M6` ตาม `expected_meter_count` |
| `hero_image_url` | mascot solar meter image |
| body | `เริ่มต้นบันทึกค่ามิเตอร์ เพื่อสร้างรายงานประจำสัปดาห์` |
| primary | `เริ่มบันทึก` -> `start_collection` |
| secondary | `ดูสถานะ` -> `show_status` |

Do not show:

- `เครื่องถัดไป -` when there is no next meter
- long OCR explanation in Start card
- cancel as a large button in the first visual pass; keep cancel in Quick Reply or secondary only when state is active

## Status Card Target

Status Card does not need to copy Start Card exactly, but must share the same shell and button styling

Target content:

| Slot | Value |
| --- | --- |
| `title` | `สถานะรอบบันทึก` |
| `status_badge` | `8/8 เครื่อง` |
| body | week, progress line, optional pending line |
| visual cue | M1-M8 grid with same green chip style |
| primary | `บันทึกต่อ` only when there is a next meter |
| secondary | `รายงานล่าสุด`, `Help` |

Complete state:

- if `confirmed_count == total_count`, primary should become `ดูรายงานล่าสุด` or be omitted until report is ready
- do not show `บันทึกต่อ` if there is no next meter

## Asset Plan with imagegen

Use `imagegen` built-in tool for visual assets unless a later task explicitly requests CLI/API fallback

### Asset 1: Solar Meter Mascot Hero

Purpose:

- used in Start Collection and Help-style cards
- should match existing eco-tech visual language

Target workspace path after generation:

```text
docs/v0.2.0-line-cards/assets/solar-meter-mascot-hero-v0.2.0.png
```

Prompt draft:

```text
Use case: ui-mockup
Asset type: LINE Flex Message hero illustration
Primary request: friendly solar meter robot mascot with a small solar panel, clean energy theme
Style/medium: soft 3D flat-modern illustration
Composition/framing: compact right-side hero illustration, generous padding, readable at mobile card size
Color palette: primary green #4CAF50, dark green #2E7D32, light green #E8F5E9, accent yellow #FFC107, accent blue #64B5F6
Constraints: no text, no logo, no watermark, no dark background, no clutter
```

### Asset 2: Card Visual Reference Board

Purpose:

- compare production card shell against mock before coding
- useful in docs and review

Target workspace path after generation:

```text
docs/v0.2.0-line-cards/assets/card-shell-reference-v0.2.0.png
```

Prompt draft:

```text
Use case: ui-mockup
Asset type: LINE Flex Message UI reference board
Primary request: show 4 card states using one shared LINE card shell: Start Collection, Meter Request, OCR Confirmation, Status Complete
Style/medium: high-fidelity mobile UI mockup
Composition/framing: 2x2 grid of LINE card mockups on light #F5F7F5 background
Color palette: green-centered eco-tech palette with #4CAF50, #2E7D32, #E8F5E9, #FFC107, #64B5F6, #9E9E9E
Text: use short Thai labels only: "เริ่มบันทึกมิเตอร์", "ถ่ายรูป M2", "ตรวจพบค่า", "สถานะรอบบันทึก"
Constraints: no browser chrome, no marketing hero, no extra explanatory paragraphs, no watermark
```

## graphify Plan

Use `graphify` for scoped understanding and verification, not the whole repo by default

Reason:

- full repo detection is too large because generated outputs, reports, images, and `tmp/` inflate the corpus
- card alignment needs only LINE code, tests, and v0.2.0 docs

Recommended scopes:

| Goal | Scope |
| --- | --- |
| Understand card implementation | `app/line` |
| Verify tests and behavior | `tests/test_line_messages.py`, `tests/test_line_webhook_postback.py` |
| Understand design docs | `docs/v0.2.0-line-cards` |
| Compare help-flow visuals | `docs/help-flows/preview` |

Recommended first command:

```bash
/graphify docs/v0.2.0-line-cards
```

Recommended implementation-review command after code changes:

```bash
/graphify app/line --mode deep
```

Expected use:

- identify which builders share styles and actions
- confirm `start_collection`, `show_status`, `confirm_reading`, and `select_meter` stay connected to expected tests
- use `GRAPH_REPORT.md` to inspect surprising cross-links before review
- do not commit large regenerated `graphify-out` files unless they are intentionally part of the task

## Implementation Phases

### Phase 1: Documentation and Assets

- add this visual alignment plan
- generate or choose mascot/hero assets with `imagegen`
- store project-bound assets under `docs/v0.2.0-line-cards/assets/`
- if production LINE cards need hosted images, later copy selected assets into an app asset path and expose HTTPS URLs

Done when:

- docs show exact visual target for Start and Status cards
- assets have stable names and are referenced from docs

### Phase 2: Card Shell Spec

- define card shell fields and defaults in docs first
- decide which Flex limitations require approximation
- add test cases for omitted rows and complete state actions

Done when:

- implementer can build the shell without deciding layout policy

### Phase 3: Start Collection Card

- change only Start card first
- use compact title/subtitle/body
- add optional hero image URL support
- hide next meter row when no next meter
- keep postbacks unchanged

Done when:

- Start card visually matches mock direction
- existing start collection behavior still passes tests

### Phase 4: Status Card

- reuse shell styling
- keep meter grid but align chip style with mock
- use configured `expected_meter_count`
- omit `บันทึกต่อ` when there is no next meter

Done when:

- complete state no longer looks like a pending-recording card
- Status card feels visually related to Start card

### Phase 5: Extend to Collection Set

Apply the same shell to:

- Meter Request
- OCR Confirmation
- Warning Recovery

Do not expand to all 12 cards until the collection set feels consistent in real LINE screenshots

## Acceptance Criteria

- Start card screenshot in LINE and mock reference have the same hierarchy: title, subtitle, visual cue, one primary action, one secondary action
- Status card uses the same button and badge language as Start card
- No card shows placeholder rows like `เครื่องถัดไป -`
- Card copy is short enough to scan on mobile
- Card actions still map to existing postback names
- Text fallback commands still work
- `graphify-out` changes are only kept when intentionally requested

## Open Decisions for Implementation

These should be locked before coding:

1. Asset hosting: use existing public raw GitHub URLs, backend static endpoint, or Cloudflare R2
2. Image placement: Flex `hero` image vs body-side thumbnail
3. Cancel action visibility: visible secondary button vs Quick Reply only
4. Complete state primary action: `รายงานล่าสุด` vs no primary until report generation finishes
