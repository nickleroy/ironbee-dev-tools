#!/bin/bash
gdb-trace --sources $IB_ROOT/modules/modhtp.c --levels 6 --prefix htp_tx_ htp_connp modhtp_htp_ --exclude htp_connp_get_last_error htp_connp_get_user_data htp_tx_get_user_data -p ./.libs/test_luajit --gtest_filter=IronBeeLuaApi.logError
