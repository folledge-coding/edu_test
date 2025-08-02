from telegram.ext import CommandHandler
from globals import LS_vars, send_telegram
from database.trading_db import get_daily_summary


async def help_command(update, context):
    """도움말 명령어"""
    await update.message.reply_text(
        """
🤖 LS증권 자동매매 시스템 명령어

/help - 도움말
/status - 현재 보유종목 상태
/summary - 오늘 거래 요약
/positions - 포지션 상세정보
/stop - 시스템 중지 (긴급시)
/start - 시스템 재시작
        """
    )


async def status_command(update, context):
    """현재 상태 조회"""
    if not LS_vars.stock_positions:
        await update.message.reply_text("📭 현재 보유중인 종목이 없습니다.")
        return
    
    status_msg = "📊 현재 보유종목 상태\n\n"
    
    for shcode, position in LS_vars.stock_positions.items():
        profit_rate = position["profit_rate"]
        status_icon = "🟢" if profit_rate > 0 else "🔴" if profit_rate < 0 else "⚪"
        
        status_msg += f"{status_icon} {position['hname']} ({shcode})\n"
        status_msg += f"   보유: {position['qty']:,}주\n"
        status_msg += f"   수익률: {profit_rate:.2f}%\n"
        status_msg += f"   당일저가: {position['today_low']:,}원\n"
        status_msg += f"   매도상태: "
        
        if position["sell_7_done"]:
            status_msg += "전량매도완료\n"
        else:
            sell_status = []
            if position["sell_3_done"]:
                sell_status.append("3%✅")
            else:
                sell_status.append("3%⏳")
            if position["sell_5_done"]:
                sell_status.append("5%✅")
            else:
                sell_status.append("5%⏳")
            if position["sell_7_done"]:
                sell_status.append("7%✅")
            else:
                sell_status.append("7%⏳")
            status_msg += " ".join(sell_status) + "\n"
        
        status_msg += "\n"
    
    await update.message.reply_text(status_msg)


async def summary_command(update, context):
    """오늘 거래 요약"""
    summary = get_daily_summary()
    
    if summary:
        await update.message.reply_text(
            f"📈 오늘 거래 요약\n\n"
            f"총 주문 수: {summary['total_orders']}건\n"
            f"체결 완료: {summary['completed_orders']}건\n"
            f"매도 금액: {summary['total_sell_amount']:,}원"
        )
    else:
        await update.message.reply_text("📭 오늘 거래 내역이 없습니다.")


async def positions_command(update, context):
    """포지션 상세정보"""
    if not LS_vars.stock_positions:
        await update.message.reply_text("📭 현재 보유중인 종목이 없습니다.")
        return
    
    for shcode, position in LS_vars.stock_positions.items():
        today_low = position["today_low"]
        target_3 = int(today_low * 1.03)
        target_5 = int(today_low * 1.05)
        target_7 = int(today_low * 1.07)
        
        detail_msg = f"📋 {position['hname']} ({shcode}) 상세정보\n\n"
        detail_msg += f"보유수량: {position['qty']:,}주\n"
        detail_msg += f"평균단가: {position['avg_price']:,}원\n"
        detail_msg += f"현재가: {position['current_price']:,}원\n"
        detail_msg += f"수익률: {position['profit_rate']:.2f}%\n"
        detail_msg += f"당일저가: {today_low:,}원\n\n"
        detail_msg += f"매도 목표가:\n"
        detail_msg += f"  3% 목표: {target_3:,}원 "
        detail_msg += "✅" if position["sell_3_done"] else "⏳"
        detail_msg += f" ({position['sell_3_qty']}주)\n"
        detail_msg += f"  5% 목표: {target_5:,}원 "
        detail_msg += "✅" if position["sell_5_done"] else "⏳"
        detail_msg += f" ({position['sell_5_qty']}주)\n"
        detail_msg += f"  7% 목표: {target_7:,}원 "
        detail_msg += "✅" if position["sell_7_done"] else "⏳"
        detail_msg += f" ({position['sell_7_qty']}주)\n"
        
        await update.message.reply_text(detail_msg)


async def stop_command(update, context):
    """시스템 중지"""
    LS_vars.is_market_open = False
    await update.message.reply_text("🛑 자동매매 시스템이 중지되었습니다.")
    send_telegram("🚨 사용자 요청으로 시스템이 중지되었습니다.")


async def start_command(update, context):
    """시스템 재시작"""
    LS_vars.is_market_open = True
    await update.message.reply_text("▶️ 자동매매 시스템이 재시작되었습니다.")
    send_telegram("✅ 사용자 요청으로 시스템이 재시작되었습니다.")


async def telegram_init():
    """텔레그램 명령어 초기화"""
    LS_vars.telegram_app.add_handler(CommandHandler("help", help_command))
    LS_vars.telegram_app.add_handler(CommandHandler("status", status_command))
    LS_vars.telegram_app.add_handler(CommandHandler("summary", summary_command))
    LS_vars.telegram_app.add_handler(CommandHandler("positions", positions_command))
    LS_vars.telegram_app.add_handler(CommandHandler("stop", stop_command))
    LS_vars.telegram_app.add_handler(CommandHandler("start", start_command))

    await LS_vars.telegram_app.initialize()
    await LS_vars.telegram_app.start()
    await LS_vars.telegram_app.updater.start_polling()
