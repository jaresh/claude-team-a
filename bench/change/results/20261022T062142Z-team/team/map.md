# Repo map: 18 files, 2283 lines (18 skipped). Detail: definitions and methods.
Format: `file lines: name:line ...`. Find code by name with `grep -n`, then read the
range with `sed -n 'A,Bp'`; open a whole file only when the task is about all of it.
Regenerate: `python3 .claude/skills/team/team_kit.py map`

tests/
 test_archive_credit.py 174: Base:11{run_wms:26,ok:31,bad:36} AtBoundary:45 Archive:54 Credit:102{order:107} ArchiveHttp:141
 test_smoke.py 33: Smoke:11{run_wms:12}
wms/
 __init__.py 2
 __main__.py 6
 catalog.py 178: check_product:7 insert_product:30 product_add:35 product_json:44 product_obj:52 product_list:56 product_archive:69 product_edit:95 import_products:111 warehouse_add:141 location_add:155 warehouse_list:171 location_list:175
 cli.py 222: Parser:20{error:21} build_parser:25 dispatch:136 main:198
 core.py 234: UserError:11 NotFound:15 HttpError:19{__init__:20} ImportErrors:25{__init__:26} r2:43 r4:47 money:51 cost4:56 fq:60 floor_unit:68 parse_qty:72 parse_cost:82 parse_amount:89 parse_percent:96 parse_time:103 parse_date:112 wh_of:121 Ctx:177{__init__:178,q:185,one:188,ex:191,meta:194,set_meta:198,next_doc:201,audit:206,product:210,live_product:216,location:223,warehouse:229}
 http.py 185: strings:19 serve:25 products_page:172
 ledger.py 244: load_movements:8 unit_keys:13 stock_map:23 Layer:31{__init__:34,key:37} Engine:41{__init__:44,_avg:56,_recompute:60,_add_layer:67,_in:73,_out:86,apply:112,stock_value:181} replay:189 _replay_with_value:196 add_movement:203 mv_json:220 current_stock:227 reserved_map:231 free_at:239
 orders.py 312: so_get:12 line_figures:19 so_status:31 so_show:46 so_list:62 so_create:67 allocate:92 so_confirm:131 so_allocate:175 so_pick:186 so_ship:208 so_cancel:227 expire_reservations:239 stock_report:248 figures:273 available:291 reorder:299
 pricing.py 113: customer_json:7 parse_limit:15 customer_limit:22 customer_add:34 customer_list:50 price_set:54 price_list:65 promo_add:72 promo_json:95 promo_list:100 unit_price:104
 purchasing.py 99: po_get:8 po_received:15 po_status:20 po_show:31 po_create:46 po_receive:67 po_close:88 po_list:96
 reports.py 58: cut_for:8 valuation:14 aging:39
 returns.py 68: rt_json:10 return_create:16 return_list:60 audit_list:64
 session.py 42: connect:7 authorize:13 run:23
 stock.py 183: check_tracking:9 split_serials:30 do_receive:34 receive:65 take_check:71 move:82 adjust:97 scrap:123 movement_list:136 movement_void:153
 transfers.py 56: tr_get:9 tr_json:16 transfer_create:21 transfer_finish:42 transfer_list:54
 users.py 74: valid_name:6 init:11 enabled_admins:25 user_add:29 get_user:40 user_role:47 user_disable:58 user_json:67 user_list:72

Non-code files (folder, count), not listed:
 ./ 3
 docs/ 1
