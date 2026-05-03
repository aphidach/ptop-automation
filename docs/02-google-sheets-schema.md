# Google Sheets Schema

## Spreadsheet Tabs

Recommended spreadsheet name:

```text
solar_meter_bot
```

Recommended tabs:

- `meters`
- `readings`
- `batches`
- `pending_confirmations`
- `settings`
- `audit_log`

## Tab: meters

Master data for all meter devices.

| column | type | required | example | notes |
| --- | --- | --- | --- | --- |
| meter_id | string | yes | M1 | Unique meter code used in LINE |
| name | string | yes | Solar 1 | Human-readable name |
| location | string | no | อาคาร A | Site/building/area |
| sort_order | number | yes | 1 | Report display order |
| active | boolean | yes | TRUE | Ignore inactive meters |
| default_rate | number | yes | 4.2 | THB/unit or configured billing rate |

Example:

| meter_id | name | location | sort_order | active | default_rate |
| --- | --- | --- | ---: | --- | ---: |
| M1 | Solar 1 | อาคาร A | 1 | TRUE | 4.2 |
| M2 | Solar 2 | อาคาร A | 2 | TRUE | 4.2 |

## Tab: readings

Confirmed meter readings. This is the main business data.

| column | type | required | example | notes |
| --- | --- | --- | --- | --- |
| reading_id | string | yes | rdg_20260504_M1 | Unique id |
| batch_id | string | yes | 2026-W19-Uxxxx | Weekly batch id |
| date | date | yes | 2026-05-04 | Reading date |
| week | string | yes | 2026-W19 | ISO week |
| line_source_id | string | yes | Uxxxx/Cxxxx/Rxxxx | User/group/room id |
| line_user_id | string | no | Uxxxx | Sender id |
| meter_id | string | yes | M1 | Foreign key to `meters` |
| current_value | number | yes | 12500 | Confirmed meter value |
| last_value | number | yes | 12000 | Previous confirmed value |
| produced_unit | number | yes | 500 | `current_value - last_value` |
| rate | number | yes | 4.2 | Rate used for calculation |
| amount | number | yes | 2100 | `produced_unit * rate` |
| ocr_raw_text | string | no | 12,500 | Raw OCR output or shortened text |
| ocr_value | number | no | 12500 | Parsed OCR value before confirmation |
| confirmation_method | string | yes | ok | `ok`, `manual_edit`, `manual_entry` |
| image_message_id | string | no | 123456 | LINE message id |
| image_file_id | string | no | gs://... | Optional stored image reference |
| created_at | datetime | yes | 2026-05-04T09:00:00+07:00 | Backend timestamp |

## Tab: batches

Tracks completion of a weekly set.

| column | type | required | example | notes |
| --- | --- | --- | --- | --- |
| batch_id | string | yes | 2026-W19-Uxxxx | Unique batch id |
| week | string | yes | 2026-W19 | ISO week |
| date | date | yes | 2026-05-04 | Reading date |
| line_source_id | string | yes | Uxxxx/Cxxxx/Rxxxx | LINE source |
| expected_meter_count | number | yes | 8 | Usually 8 |
| confirmed_meter_count | number | yes | 6 | Count from readings |
| status | string | yes | collecting | `collecting`, `complete`, `reported` |
| report_image_url | string | no | https://... | Public report image URL if needed |
| created_at | datetime | yes | 2026-05-04T09:00:00+07:00 | Created timestamp |
| updated_at | datetime | yes | 2026-05-04T09:10:00+07:00 | Updated timestamp |

## Tab: pending_confirmations

Temporary records waiting for user confirmation. If Redis or SQLite is used, this tab can be skipped.

| column | type | required | example | notes |
| --- | --- | --- | --- | --- |
| confirmation_id | string | yes | cnf_xxx | Unique id |
| line_source_id | string | yes | Uxxxx | LINE source |
| line_user_id | string | no | Uxxxx | Sender |
| meter_id | string | yes | M1 | Meter waiting for confirmation |
| batch_id | string | yes | 2026-W19-Uxxxx | Batch id |
| image_message_id | string | yes | 123456 | LINE image id |
| ocr_value | number | no | 12500 | Parsed value |
| ocr_raw_text | string | no | 12,500 | Raw OCR output |
| status | string | yes | pending | `pending`, `confirmed`, `edited`, `expired` |
| expires_at | datetime | yes | 2026-05-04T10:00:00+07:00 | Auto-expiry |
| created_at | datetime | yes | 2026-05-04T09:00:00+07:00 | Created timestamp |

## Tab: settings

Key-value settings.

| key | value | notes |
| --- | --- | --- |
| expected_meter_count | 8 | Number of meters per batch |
| default_rate | 4.2 | Default THB/unit |
| timezone | Asia/Bangkok | Used for date/week |
| report_title | Solar Weekly Report | Header in generated image |

## Tab: audit_log

Append-only event log for debugging.

| column | type | example |
| --- | --- | --- |
| event_id | string | evt_xxx |
| timestamp | datetime | 2026-05-04T09:00:00+07:00 |
| event_type | string | ocr_completed |
| line_source_id | string | Uxxxx |
| meter_id | string | M1 |
| payload_json | string | {"value":12500} |

## Calculation Rules

```text
last_value = latest confirmed current_value for the same meter_id before this batch
produced_unit = current_value - last_value
amount = produced_unit * rate
```

Validation:

- `current_value` must be numeric
- `current_value` should be greater than or equal to `last_value`
- Negative `produced_unit` should require manual confirmation
- Duplicate `meter_id` in the same `batch_id` should require replace confirmation
