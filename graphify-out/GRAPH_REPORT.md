# Graph Report - app  (2026-05-03)

## Corpus Check
- 44 files · ~193,752 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 436 nodes · 898 edges · 24 communities detected
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 181 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_LINE Webhook Flow|LINE Webhook Flow]]
- [[_COMMUNITY_Message Builders|Message Builders]]
- [[_COMMUNITY_Google Vision OCR|Google Vision OCR]]
- [[_COMMUNITY_Command Parsing|Command Parsing]]
- [[_COMMUNITY_Batch Progress|Batch Progress]]
- [[_COMMUNITY_LINE Client API|LINE Client API]]
- [[_COMMUNITY_Sheet Storage|Sheet Storage]]
- [[_COMMUNITY_Meter Calculation|Meter Calculation]]
- [[_COMMUNITY_OCR Text Parsing|OCR Text Parsing]]
- [[_COMMUNITY_Report Image Generation|Report Image Generation]]
- [[_COMMUNITY_Google Sheets Client|Google Sheets Client]]
- [[_COMMUNITY_History Service|History Service]]
- [[_COMMUNITY_Start Collection Menu|Start Collection Menu]]
- [[_COMMUNITY_Help Menu|Help Menu]]
- [[_COMMUNITY_OCR Confidence|OCR Confidence]]
- [[_COMMUNITY_Rich Menu Composer|Rich Menu Composer]]
- [[_COMMUNITY_History Menu|History Menu]]
- [[_COMMUNITY_Latest Report Menu|Latest Report Menu]]
- [[_COMMUNITY_Session Store|Session Store]]
- [[_COMMUNITY_Weekly Summary Menu|Weekly Summary Menu]]
- [[_COMMUNITY_Settings Menu|Settings Menu]]
- [[_COMMUNITY_Sheets Setup|Sheets Setup]]
- [[_COMMUNITY_App Config|App Config]]
- [[_COMMUNITY_Storage Package|Storage Package]]

## God Nodes (most connected - your core abstractions)
1. `_handle_postback()` - 51 edges
2. `handle_webhook()` - 34 edges
3. `build_postback_data()` - 30 edges
4. `_text_with_actions()` - 29 edges
5. `get_or_create_session()` - 18 edges
6. `_build_text_reply()` - 17 edges
7. `confirm_pending()` - 16 edges
8. `_send_confirm_reading_result()` - 15 edges
9. `_process_ocr_and_confirm()` - 15 edges
10. `SheetsClient` - 12 edges

## Surprising Connections (you probably didn't know these)
- `create_pending_confirmation()` --calls--> `append_pending_confirmation()`  [INFERRED]
  services/confirmation_service.py → sheets/repositories.py
- `get_pending_confirmation()` --calls--> `get_latest_pending_confirmation()`  [INFERRED]
  services/confirmation_service.py → sheets/repositories.py
- `_safe_update_pending_status()` --calls--> `update_pending_confirmation_status()`  [INFERRED]
  services/confirmation_service.py → sheets/repositories.py
- `_process_ocr_and_confirm()` --calls--> `score_ocr_reading()`  [INFERRED]
  line/webhook.py → ocr/confidence.py
- `_process_ocr_and_confirm()` --calls--> `parse_meter_value()`  [INFERRED]
  line/webhook.py → ocr/value_parser.py

## Hyperedges (group relationships)
- **Weekly Summary Tile Composition** — richmenu_weekly_summary_rich_menu_tile, richmenu_bar_chart_icon, richmenu_weekly_summary_label, richmenu_weekly_production_income_summary, richmenu_green_status_visual_language [EXTRACTED 1.00]
- **Settings Rich Menu Tile Composition** — richmenu-settings_rich_menu_tile, richmenu-settings_settings_icon, richmenu-settings_settings_action, richmenu-settings_meter_configuration, richmenu-settings_notification_configuration [EXTRACTED 1.00]
- **Richmenu History Tile Composition** — richmenu_history_asset, richmenu_history_green_folder_icon, richmenu_history_clock_arrow_symbol, richmenu_history_primary_label, richmenu_history_secondary_label, richmenu_history_rounded_tile_layout [EXTRACTED 1.00]
- **History Navigation Affordance** — richmenu_history_clock_arrow_symbol, richmenu_history_green_folder_icon, richmenu_history_secondary_label, richmenu_history_view_records_action [INFERRED 0.85]
- **Latest Report Rich Menu Tile** — richmenu_latest_report_asset, richmenu_latest_report_document_icon, richmenu_latest_report_chart_graphic, richmenu_latest_report_title_text, richmenu_latest_report_description_text, richmenu_latest_report_action, richmenu_latest_report_card_layout [INFERRED 0.90]
- **Rich Menu Meter Recording Flow** — richmenu_start_collection_weekly_meter_recording, richmenu_start_collection_capture_8_meters_instruction, richmenu_start_collection_start_record_button, richmenu_start_collection_camera_icon [INFERRED 0.85]
- **Solar Meter Green Energy Visual Identity** — richmenu_start_collection_solar_meter_robot, richmenu_start_collection_solar_panel, richmenu_start_collection_green_energy_theme, richmenu_start_collection_chat_bubble_indicator [INFERRED 0.80]
- **Rich Menu Help Support Message** — richmenu_help_help_action, richmenu_help_usage_questions, richmenu_help_admin_contact [EXTRACTED 1.00]
- **Rich Menu Help Visual Composition** — richmenu_help_support_mascot, richmenu_help_chat_contact_icon, richmenu_help_solar_energy_context, richmenu_help_green_visual_theme [EXTRACTED 1.00]

## Communities (35 total, 4 thin omitted)

### Community 0 - "LINE Webhook Flow"
Cohesion: 0.07
Nodes (69): is_valid_meter(), _after_successful_confirmation(), _build_reply(), _build_settings_edit_prompt(), _build_settings_input_reply(), _build_status_message(), _build_text_reply(), _coerce_manual_value_command() (+61 more)

### Community 1 - "Message Builders"
Cohesion: 0.13
Nodes (46): _bool_th(), build_confirmation_card(), build_duplicate_warning_card(), build_help_flow_response(), build_help_menu_message(), build_history_batch_list_message(), build_history_detail_message(), build_history_empty_message() (+38 more)

### Community 2 - "Google Vision OCR"
Cohesion: 0.09
Nodes (13): GoogleVisionOcrClient, _looks_like_mpr45s(), _make_mpr45s_detail_crop(), OcrResult, TyphoonOcrClient, _flatten_paddle_result(), PaddleOcrClient, _connected_components() (+5 more)

### Community 3 - "Command Parsing"
Cohesion: 0.12
Nodes (29): _decimal_diff(), _iso_week(), _normalize_bool(), _normalize_meter_id(), _normalize_year(), parse_command(), parse_postback_action(), _parse_report_date() (+21 more)

### Community 4 - "Batch Progress"
Cohesion: 0.15
Nodes (28): BatchProgress, build_progress_message(), _expected_meter_count(), format_progress_message(), generate_batch_id(), get_batch_progress(), get_or_create_batch(), update_batch_after_reading() (+20 more)

### Community 5 - "LINE Client API"
Cohesion: 0.12
Nodes (25): Exception, _content_type_to_ext(), download_image(), ImageDownloadError, _is_https_url(), push_image(), push_text(), Send an image message via LINE push API (no reply token needed). (+17 more)

### Community 6 - "Sheet Storage"
Cohesion: 0.1
Nodes (3): append_pending_confirmation(), get_latest_pending_confirmation(), update_pending_confirmation_status()

### Community 7 - "Meter Calculation"
Cohesion: 0.17
Nodes (17): calculate_reading(), _get_default_rate_setting(), _get_last_value(), _get_rate(), _is_duplicate_in_batch(), _iso_week(), Get the latest confirmed current_value for a meter. Returns 0 if no previous rea, Get rate from meter master data, fallback to DEFAULT_RATE. (+9 more)

### Community 8 - "OCR Text Parsing"
Cohesion: 0.27
Nodes (14): _clean_decimal(), _find_energy_value(), _infer_window_unit(), _log_parse_result(), _merge_candidates(), _normalize_number(), _normalize_text(), _normalize_unit() (+6 more)

### Community 9 - "Report Image Generation"
Cohesion: 0.24
Nodes (14): build_report_data(), _draw_centered_lines(), _draw_grid(), _fmt(), _fmt_baht(), _format_thai_date(), generate_report_image(), _load_font() (+6 more)

### Community 11 - "History Service"
Cohesion: 0.27
Nodes (10): BatchSummary, get_batch_summary(), get_current_batch_summary(), get_previous_batch_summary(), get_recent_batch_summaries(), _parse_datetime(), _row_datetime(), _to_decimal() (+2 more)

### Community 12 - "Start Collection Menu"
Cohesion: 0.29
Nodes (10): Camera Icon, Capture 8 Meters In Order Instruction, Chat Bubble Indicator, Green Energy Theme, Richmenu Start Collection Image, LINE Rich Menu Call To Action, Solar Meter Robot Mascot, Solar Panel (+2 more)

### Community 14 - "Help Menu"
Cohesion: 0.43
Nodes (8): Admin Contact, Chat Contact Icon, Green Renewable Energy Visual Theme, Help Action, Rich Menu Help Image, Solar Energy Context, Support Mascot, Usage Problem Questions

### Community 15 - "OCR Confidence"
Cohesion: 0.48
Nodes (5): ConfidenceResult, _get_last_value(), _get_max_produced_unit(), _has_conflicting_candidates(), score_ocr_reading()

### Community 16 - "Rich Menu Composer"
Cohesion: 0.52
Nodes (6): _build_spec(), compose_richmenu_image(), _default_buttons(), _load_image(), RichMenuButtonSpec, _save_line_compatible_image()

### Community 17 - "History Menu"
Cohesion: 0.43
Nodes (7): Richmenu History Asset, Clock Arrow History Symbol, Green Folder History Icon, Thai Primary Label ประวัติ, Rounded Pale Green Rich Menu Tile Layout, Thai Secondary Label ดูประวัติการบันทึกค่าย้อนหลัง, View Historical Recorded Values Action

### Community 18 - "Latest Report Menu"
Cohesion: 0.38
Nodes (7): View And Download Latest Report Action, Rich Menu Latest Report Asset, Rounded Rich Menu Card Layout, Green And Yellow Donut Chart Graphic, ดูรายงานและดาวน์โหลดรายงานล่าสุด Description Text, Document Report Icon, รายงานล่าสุด Title Text

### Community 19 - "Session Store"
Cohesion: 0.33
Nodes (3): Protocol, Protocol for session storage backends. Swap InMemorySessionStore for Redis/SQLit, SessionStore

### Community 20 - "Weekly Summary Menu"
Cohesion: 0.53
Nodes (6): Bar Chart Icon, Green Status Visual Language, Weekly Production and Income Summary, Weekly Summary Rich Menu Image, สรุปสัปดาห์, Weekly Summary Rich Menu Tile

### Community 21 - "Settings Menu"
Cohesion: 0.47
Nodes (6): Rich Menu Settings Image, Meter Configuration, Notification Configuration, Rich Menu Tile, Settings Action, Settings Gear Icon

## Ambiguous Edges - Review These
- `Chat Bubble Indicator` → `LINE Rich Menu Call To Action`  [AMBIGUOUS]
  app/assets/richmenu/richmenu-start-collection.png · relation: conceptually_related_to

## Knowledge Gaps
- **30 isolated node(s):** `Settings`, `Initialize Google Sheets tabs with headers.  Usage:     python -m app.sheets.set`, `Storage helpers for generated media assets.`, `Download image from LINE Content API and save to disk.      Returns the local fi`, `Send a text message via LINE push API (no reply token needed).` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Chat Bubble Indicator` and `LINE Rich Menu Call To Action`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `_handle_postback()` connect `Message Builders` to `LINE Webhook Flow`, `LINE Client API`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `_process_ocr_and_confirm()` connect `LINE Webhook Flow` to `Message Builders`, `Batch Progress`, `Meter Calculation`, `OCR Text Parsing`, `OCR Confidence`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `send_report()` connect `LINE Client API` to `LINE Webhook Flow`, `Message Builders`, `Report Image Generation`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `_handle_postback()` (e.g. with `set_collection_state()` and `clear_collection_skip_meters()`) actually correct?**
  _`_handle_postback()` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `handle_webhook()` (e.g. with `parse_postback_action()` and `get_collection_state()`) actually correct?**
  _`handle_webhook()` has 19 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Settings`, `Initialize Google Sheets tabs with headers.  Usage:     python -m app.sheets.set`, `Storage helpers for generated media assets.` to the rest of the system?**
  _30 weakly-connected nodes found - possible documentation gaps or missing edges._