Check: npm test 167/167 + game/accept 52/52 pass (incl. lead's e6-shop.test.js, e2 balance).
Fix rounds: 0 (core and ui teammates, one wave).
Staging: http://127.0.0.1:8101/shop-A/game/ (port 8101: the 8100 server serves another checkout's dir and staging there was denied).
Odd: shop = level start tile ($); UI DOM path of the shop panel only smoke-tested, not played in a browser.
Assumptions: gold per kill = 2*xp+depth, unlimited stock, buying takes no turn.
