# Graph Report - repo-ptop-autometion  (2026-05-04)

## Corpus Check
- 84 files · ~1,583,456 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1297 nodes · 3355 edges · 31 communities detected
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 949 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]

## God Nodes (most connected - your core abstractions)
1. `_handle_postback()` - 127 edges
2. `build_postback_data()` - 50 edges
3. `handle_webhook()` - 46 edges
4. `ParsedPostback` - 45 edges
5. `build_postback_data()` - 45 edges
6. `_as_dict()` - 39 edges
7. `_text_with_actions()` - 33 edges
8. `parse_meter_value()` - 30 edges
9. `confirm_pending()` - 30 edges
10. `parse_energy_meter_value()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_get_worksheet_caches_by_tab_name()` --calls--> `SheetsClient`  [INFERRED]
  tests/test_sheets_client.py → app/sheets/client.py
- `test_get_worksheet_caches_each_tab_separately()` --calls--> `SheetsClient`  [INFERRED]
  tests/test_sheets_client.py → app/sheets/client.py
- `test_upsert_row_appends_when_key_is_missing()` --calls--> `SheetsClient`  [INFERRED]
  tests/test_sheets_client.py → app/sheets/client.py
- `test_upsert_row_updates_existing_key_row()` --calls--> `SheetsClient`  [INFERRED]
  tests/test_sheets_client.py → app/sheets/client.py
- `test_value_lower_than_last_reading_is_low_confidence()` --calls--> `score_ocr_reading()`  [INFERRED]
  tests/test_ocr_confidence.py → app/ocr/confidence.py

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

## Communities (57 total, 5 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (184): build_history_detail_message(), build_history_summary_message(), _history_detail_date_range(), _history_detail_footer_meta(), _history_detail_header(), _history_detail_meter_ids(), _history_detail_meter_row(), _history_detail_progress_panel() (+176 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (165): build_history_empty_message(), ParsedCommand, ParsedPostback, _after_successful_confirmation(), _build_duplicate_warning_for_pending(), _build_reply(), _build_settings_edit_prompt(), _build_settings_input_reply() (+157 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (97): build_confirmation_message(), cancel_pending(), clear_pending_confirmation(), confirm_pending(), _confirmation_method(), create_pending_confirmation(), _create_pending_confirmation_record(), _decimal_or_none() (+89 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (137): _body_text(), _bool_th(), build_batch_complete_card(), build_confirmation_card(), build_duplicate_warning_card(), build_help_menu_message(), build_history_batch_list_message(), build_history_detail_message() (+129 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (42): GoogleVisionOcrClient, _looks_like_mpr45s(), _make_mpr45s_detail_crop(), OcrResult, success(), TyphoonOcrClient, _flatten_paddle_result(), PaddleOcrClient (+34 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (17): _clean_decimal(), _find_energy_value(), _infer_window_unit(), _log_parse_result(), _merge_candidates(), _normalize_number(), _normalize_text(), _normalize_unit() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (48): Exception, _content_type_to_ext(), download_image(), ImageDownloadError, _is_https_url(), push_image(), push_message(), push_text() (+40 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (46): _decimal_diff(), is_valid_meter(), _iso_week(), _normalize_bool(), _normalize_history_period(), _normalize_meter_id(), _normalize_year(), parse_command() (+38 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (36): build_report_data(), _draw_centered_lines(), _draw_grid(), _fmt(), _fmt_baht(), _format_thai_date(), generate_report_image(), _load_font() (+28 more)

### Community 9 - "Community 9"
Cohesion: 0.1
Nodes (14): build_progress_message(), _expected_meter_count(), format_progress_message(), generate_batch_id(), get_batch_progress(), get_or_create_batch(), _iso_week(), _now() (+6 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (27): append_audit_log(), append_batch(), append_pending_confirmation(), append_reading(), _enqueue_if_sqlite(), get_active_meters(), get_all_batches(), get_all_readings() (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.18
Nodes (20): _build_spec(), compose_richmenu_image(), _default_buttons(), _load_image(), RichMenuButtonSpec, _save_line_compatible_image(), _create_richmenu(), _headers() (+12 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (5): SheetsClient, test_get_worksheet_caches_by_tab_name(), test_get_worksheet_caches_each_tab_separately(), test_upsert_row_appends_when_key_is_missing(), test_upsert_row_updates_existing_key_row()

### Community 14 - "Community 14"
Cohesion: 0.26
Nodes (16): _batches_for_source(), BatchSummary, get_batch_summary(), get_current_batch_summary(), get_latest_report_batch_id(), get_meter_history(), get_previous_batch_summary(), get_recent_batch_summaries() (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.22
Nodes (15): ConfidenceResult, _get_last_value(), _get_max_produced_unit(), _has_conflicting_candidates(), is_low(), score_ocr_reading(), test_conflicting_large_candidates_are_low_confidence(), test_fallback_generic_parse_is_low_confidence() (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (4): health(), sheets_health(), storage_sync_health(), test_health_includes_release_version()

### Community 17 - "Community 17"
Cohesion: 0.26
Nodes (9): main(), flush_outbox(), _now(), pull_all_from_sheets(), pull_business_config_from_sheets(), _pull_tables_from_sheets(), _refresh_last_error(), _sheets_client() (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (9): test_empty_flush_keeps_startup_pull_error_visible(), test_flush_outbox_failure_marks_failed_and_successful_retry_marks_synced(), test_flush_outbox_syncs_to_sheets_and_marks_synced(), test_manual_pull_replaces_all_sqlite_tables_from_sheets(), test_repeated_batch_updates_coalesce_to_latest_payload(), test_repository_writes_enqueue_sync_outbox(), test_startup_pull_clears_pending_settings_outbox(), test_startup_pull_replaces_business_config_from_sheets() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.36
Nodes (8): apply_setting_change(), get_current_settings(), get_meter_detail(), get_meter_settings(), is_admin(), setting_impact(), setting_label(), validate_setting_input()

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (10): Camera Icon, Capture 8 Meters In Order Instruction, Chat Bubble Indicator, Green Energy Theme, Richmenu Start Collection Image, LINE Rich Menu Call To Action, Solar Meter Robot Mascot, Solar Panel (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.43
Nodes (8): Admin Contact, Chat Contact Icon, Green Renewable Energy Visual Theme, Help Action, Rich Menu Help Image, Solar Energy Context, Support Mascot, Usage Problem Questions

### Community 24 - "Community 24"
Cohesion: 0.43
Nodes (7): Richmenu History Asset, Clock Arrow History Symbol, Green Folder History Icon, Thai Primary Label ประวัติ, Rounded Pale Green Rich Menu Tile Layout, Thai Secondary Label ดูประวัติการบันทึกค่าย้อนหลัง, View Historical Recorded Values Action

### Community 25 - "Community 25"
Cohesion: 0.38
Nodes (7): View And Download Latest Report Action, Rich Menu Latest Report Asset, Rounded Rich Menu Card Layout, Green And Yellow Donut Chart Graphic, ดูรายงานและดาวน์โหลดรายงานล่าสุด Description Text, Document Report Icon, รายงานล่าสุด Title Text

### Community 26 - "Community 26"
Cohesion: 0.6
Nodes (5): test_sqlite_batch_updates_preserve_hot_path_data(), test_sqlite_latest_reading_uses_newest_created_at(), test_sqlite_pending_confirmation_status_transition(), test_sqlite_reads_and_updates_settings(), _use_sqlite()

### Community 28 - "Community 28"
Cohesion: 0.53
Nodes (6): Bar Chart Icon, Green Status Visual Language, Weekly Production and Income Summary, Weekly Summary Rich Menu Image, สรุปสัปดาห์, Weekly Summary Rich Menu Tile

### Community 29 - "Community 29"
Cohesion: 0.47
Nodes (6): Rich Menu Settings Image, Meter Configuration, Notification Configuration, Rich Menu Tile, Settings Action, Settings Gear Icon

## Ambiguous Edges - Review These
- `Chat Bubble Indicator` → `LINE Rich Menu Call To Action`  [AMBIGUOUS]
  app/assets/richmenu/richmenu-start-collection.png · relation: conceptually_related_to

## Knowledge Gaps
- **80 isolated node(s):** `SyncState`, `Download image from LINE Content API and save to disk.      Returns the local fi`, `Send a text message via LINE push API (no reply token needed).`, `Send one or more prepared LINE message objects via push API.`, `Send an image message via LINE push API (no reply token needed).` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Chat Bubble Indicator` and `LINE Rich Menu Call To Action`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `_handle_postback()` connect `Community 1` to `Community 0`, `Community 3`, `Community 6`, `Community 7`, `Community 9`?**
  _High betweenness centrality (0.210) - this node is a cross-community bridge._
- **Why does `_process_ocr_and_confirm()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 15`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Why does `parse_meter_value()` connect `Community 5` to `Community 1`, `Community 4`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Are the 110 inferred relationships involving `_handle_postback()` (e.g. with `set_collection_state()` and `clear_collection_skip_meters()`) actually correct?**
  _`_handle_postback()` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `handle_webhook()` (e.g. with `parse_postback_action()` and `get_collection_state()`) actually correct?**
  _`handle_webhook()` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `ParsedPostback` (e.g. with `_FakeSheetsResponse` and `test_start_collection_postback_starts_linear_flow()`) actually correct?**
  _`ParsedPostback` has 42 INFERRED edges - model-reasoned connections that need verification._