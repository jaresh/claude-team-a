# Repo map: 18 files, 2291 lines (18 skipped). Detail: definitions and methods.
Format: `file lines: name:line ...`. Find code by name with `grep -n`, then read the
range with `sed -n 'A,Bp'`; open a whole file only when the task is about all of it.
Regenerate: `python3 .claude/skills/team/team_kit.py map`

tests/
 test_changes.py 195: Base:14{run_wms:30,ok:35,bad:40} AtBug:47 Archive:58 Http:117{req:118} Credit:154{order:159}
 test_smoke.py 33: Smoke:11{run_wms:12}
wms/
 __init__.py 2
 __main__.py 6
 catalog.py 170: check_product:7 insert_product:30 product_add:35 product_json:44 product_list:52 product_edit:64 product_archive:80 import_products:103 warehouse_add:133 location_add:147 warehouse_list:163 location_list:167
 cli.py 222: Parser:20{error:21} build_parser:25 dispatch:136 main:198
 core.py 235: UserError:11 NotFound:15 HttpError:19{__init__:20} ImportErrors:25{__init__:26} r2:43 r4:47 money:51 cost4:56 fq:60 floor_unit:68 parse_qty:72 parse_cost:82 parse_amount:89 parse_percent:96 parse_time:103 parse_date:112 wh_of:121 migrate:170 Ctx:180{__init__:181,q:186,one:189,ex:192,meta:195,set_meta:199,next_doc:202,audit:207,product:211,live_product:217,location:224,warehouse:230}
 http.py 184: strings:19 serve:25 products_page:171
 ledger.py 244: load_movements:8 unit_keys:13 stock_map:23 Layer:31{__init__:34,key:37} Engine:41{__init__:44,_avg:56,_recompute:60,_add_layer:67,_in:73,_out:86,apply:112,stock_value:181} replay:189 _replay_with_value:196 add_movement:203 mv_json:220 current_stock:227 reserved_map:231 free_at:239
 orders.py 312: so_get:12 line_figures:19 so_status:31 so_show:46 so_list:62 so_create:67 allocate:92 so_confirm:131 so_allocate:175 so_pick:186 so_ship:208 so_cancel:227 expire_reservations:239 stock_report:248 figures:273 available:291 reorder:299
 pricing.py 107: parse_limit:7 customer_json:14 customer_limit:21 customer_add:30 customer_list:44 price_set:48 price_list:59 promo_add:66 promo_json:89 promo_list:94 unit_price:98
 purchasing.py 99: po_get:8 po_received:15 po_status:20 po_show:31 po_create:46 po_receive:67 po_close:88 po_list:96
 reports.py 58: cut_for:8 valuation:14 aging:39
 returns.py 68: rt_json:10 return_create:16 return_list:60 audit_list:64
 session.py 43: connect:7 authorize:13 run:23
 stock.py 183: check_tracking:9 split_serials:30 do_receive:34 receive:65 take_check:71 move:82 adjust:97 scrap:123 movement_list:136 movement_void:153
 transfers.py 56: tr_get:9 tr_json:16 transfer_create:21 transfer_finish:42 transfer_list:54
 users.py 74: valid_name:6 init:11 enabled_admins:25 user_add:29 get_user:40 user_role:47 user_disable:58 user_json:67 user_list:72

Non-code files (folder, count), not listed:
 ./ 3
 docs/ 1
