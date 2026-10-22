# Repo map: 5 files, 2061 lines (5 skipped). Detail: definitions and methods.
Format: `file lines: name:line ...`. Find code by name with `grep -n`, then read the
range with `sed -n 'A,Bp'`; open a whole file only when the task is about all of it.
Regenerate: `python3 .claude/skills/team/team_kit.py map`

tests/
 test_archive.py 77: Archive:11{run_wms:25,ok:30,bad:35}
 test_smoke.py 33: Smoke:11{run_wms:12}
wms/
 __init__.py 5
 __main__.py 6
 app.py 1940: UserError:18 NotFound:22 HttpError:26{__init__:27} ImportErrors:32{__init__:33} r2:44 r4:48 money:52 cost4:57 fq:61 floor_unit:69 parse_qty:73 parse_cost:83 parse_amount:90 parse_percent:97 parse_time:104 parse_date:113 wh_of:122 Ctx:170{__init__:171,q:176,one:179,ex:182,meta:185,set_meta:189,next_doc:192,audit:197,product:201,is_archived:209,live_product:212,location:219,warehouse:225} load_movements:234 unit_keys:239 stock_map:249 Layer:257{__init__:260,key:263} Engine:267{__init__:270,_avg:282,_recompute:286,_add_layer:293,_in:299,_out:312,apply:338,stock_value:407} replay:415 _replay_with_value:422 add_movement:429 mv_json:446 current_stock:453 reserved_map:457 free_at:465 valid_name:474 init:479 enabled_admins:493 user_add:497 get_user:508 user_role:515 user_disable:526 user_json:535 user_list:540 check_product:546 insert_product:569 product_add:574 product_json:583 product_list:591 product_archive:603 product_edit:627 import_products:643 warehouse_add:673 location_add:687 warehouse_list:703 location_list:707 check_tracking:714 split_serials:735 do_receive:739 receive:770 take_check:776 move:787 adjust:802 scrap:828 movement_list:841 movement_void:858 cut_for:892 valuation:898 aging:923 po_get:946 po_received:953 po_status:958 po_show:969 po_create:984 po_receive:1005 po_close:1026 po_list:1034 customer_add:1041 customer_list:1054 price_set:1058 price_list:1069 promo_add:1076 promo_json:1099 promo_list:1104 unit_price:1108 so_get:1121 line_figures:1128 so_status:1140 so_show:1155 so_list:1171 so_create:1176 allocate:1201 so_confirm:1240 so_allocate:1277 so_pick:1288 so_ship:1310 so_cancel:1329 expire_reservations:1341 stock_report:1350 figures:1375 available:1393 reorder:1401 tr_get:1420 tr_json:1427 transfer_create:1432 transfer_finish:1453 transfer_list:1465 rt_json:1471 return_create:1477 return_list:1521 audit_list:1525 connect:1533 authorize:1539 run:1549 Parser:1570{error:1571} build_parser:1575 dispatch:1685 main:1746 strings:1777 serve:1783 products_page:1927

Non-code files (folder, count), not listed:
 ./ 3
 docs/ 1
