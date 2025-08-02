
from telegram.ext import CommandHandler
from globals import LS_vars

async def help(update, context):
    await update.message.reply_text(
"""
/help 도움말
/t0424 보유종목 조회
/cspaq12200 증거금 조회
"""
    )

async def t0424_telegram(update, context):
        """
        보유종목 조회 명령
        """
        if LS_vars.t0424_telegram_requesting == False:
            await update.message.reply_text("보유 종목 요청중입니다. 잠시만 기다려주세요.")
            LS_vars.t0424_telegram_requesting = True

            return
        
        await update.message.reply_text("이전 요청이 진행중입니다. 잠시만 기다려주세요.")

async def cspaq12200_telegram(update, context):
        """
        예수금 조회 명령
        """
        if LS_vars.cspaq12200_telegram_requesting == False:
            LS_vars.cspaq12200_telegram_requesting = True
            await update.message.reply_text("예수금 요청중입니다. 잠시만 기다려주세요.")

            return
        
        await update.message.reply_text("이전 요청이 진행중입니다. 잠시만 기다려주세요.")

async def telegram_init():
    """
    텔레그램 명령어 초기화
    """

    LS_vars.telegram_app.add_handler(CommandHandler("help", help))
    LS_vars.telegram_app.add_handler(CommandHandler("t0424", t0424_telegram))
    LS_vars.telegram_app.add_handler(CommandHandler("cspaq12200", cspaq12200_telegram))

    await LS_vars.telegram_app.initialize()
    await LS_vars.telegram_app.start()
    await LS_vars.telegram_app.updater.start_polling()
