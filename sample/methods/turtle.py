import asyncio
from globals import LS_vars, send_telegram
from ls_res.t8436 import T8436_req
from ls_res.g3204 import G3204_req
from ls_res.t8410 import T8410_req
from database.method_db import insertPassedStock, clearPassedStocks
from database.account_db import clearTempOrderingStocks
from database.stock_db import insertStocks


class Method_req:
    async def calculator():

        print("계싼 들어감")

        clearTempOrderingStocks()
        print("clearTempOrderingStocks")
        clearPassedStocks()

        ## 미국 증시 장기 상승장 ##
        await Method_req.americaMarket(days=365, drate=5)
        if LS_vars.america_drate_pass == False:
            send_telegram("🌎 해외지수 장기 추세가 안 옴")
            send_telegram(
                "🤖 해외시장 장기 추세가 좋아지길 기다려 보죠."
            )
            return
        send_telegram("🌎 해외지수 장기 추세 좋음")
        #####
        
        ## 미국 증시 단기 상승장 ##
        await Method_req.americaMarket(days=7, drate=2)
        if LS_vars.america_drate_pass == False:
            send_telegram("🌎 해외지수 단기 추세가 안 옴")
            send_telegram(
                "🤖 해외시장 단기 추세가 좋아지길 기다려 보죠."
            )
            return
        send_telegram("🌎 해외지수 단기 추세 좋음")
        #####

        ## 코스피 장기 상승장 ##
        await Method_req.koreaMarket(days=365, drate=5, gubun="2")
        if LS_vars.korea_drate_pass == False:
            send_telegram("\U0001F1F0\U0001F1F7 국내지수 장기 추세가 안 옴")
            send_telegram(
                "🤖 욕심부리지말고 국내시장 추세가 좋아지길 기다려 보죠."
            )
            return
        send_telegram("\U0001F1F0\U0001F1F7 국내지수 장기 추세 좋음")
        #####

        
        ## 코스피 단기 상승장 ##
        await Method_req.koreaMarket(days=7, drate=1, gubun="2")
        if LS_vars.korea_drate_pass == False:
            send_telegram("\U0001F1F0\U0001F1F7 국내지수 단기 추세가 안 옴")
            send_telegram(
                "🤖 욕심부리지말고 국내시장 추세가 좋아지길 기다려 보죠."
            )
            return
        send_telegram("\U0001F1F0\U0001F1F7 국내지수 단기 추세 좋음")
        #####

        ## 코스피 종목들 모두 가져오기 ##
        await T8436_req.req()
        insertStocks(LS_vars.t8436_scodes)
        send_telegram(f"\U0001F1F0\U0001F1F7 국내 상장 주식 {len(LS_vars.t8436_scodes)}개 분석 시작")
        #####
        
        ## 월로 1년 추세 확인 (LS에서 연봉은 더이상 제공 안 된다고 함) ##
        await Method_req.monthsMarket(days=365, drate=50, gubun="4")
        #####

        ## 주봉으로 6개월 추세 확인 ##
        await Method_req.weeksMarket(days=180, drate=30, gubun="3")
        #####
        
        ## 일봉으로 30일 추세 확인 ##
        await Method_req.daysMarket(days=30, drate=15, gubun="2")
        #####

        ## 일봉으로 5일 추세 확인 ##
        await Method_req.daysShortMarket(days=5, drate=10, gubun="2")
        #####

        if len(LS_vars.day_short_scodes) == 0:
            send_telegram(
                "🤖 추세를 따르는 국내 종목이 아직 없네요. 내일은 나타나기를 바래보죠!"
            )
            return

        result = ""
        cnt = 0
        for data in LS_vars.day_short_scodes:
            cnt += 1
            
            # 필터링된 종목들 저장하기
            insertPassedStock({
                "method_id":"turtle",
                "shcode": data["shcode"],
                "status": "no"
            })

            result += f"""
분석완료된 종목 번호: {cnt}
종목코드: {data["shcode"]}
종목명: {data["hname"]}
            """
        
        # 최종 추출된 종목들
        send_telegram(
            result
        )

    async def americaMarket(days=365, drate=10):

        await asyncio.sleep(3)
        
        LS_vars.america_drate=drate
        LS_vars.america_drate_pass = False
        await G3204_req.req(days=days)

    async def koreaMarket(days=365, drate=10, gubun="4"):

        await asyncio.sleep(3)

        LS_vars.korea_drate=drate
        LS_vars.code_gubun = gubun
        LS_vars.code_days = days
        LS_vars.korea_drate_pass = False
        await T8410_req.req(days=days, shcode="069500", gubun=gubun)


    async def monthsMarket(days=0, drate=10, gubun="4"):
        LS_vars.code_drate = drate
        LS_vars.code_gubun = gubun
        LS_vars.code_days = days

        for data in LS_vars.t8436_scodes:
            await asyncio.sleep(3.5)

            shcode = data.get("shcode")
            hname = data.get("hname")

            await T8410_req.req(days=days, shcode=shcode, gubun=gubun)

            if LS_vars.code_drate_pass == True:
                print(f"{hname} 종목 월간 추세 통과")
                LS_vars.month_scodes.append({
                    "shcode": shcode,
                    "hname":hname
                })

    async def weeksMarket(days=0, drate=10, gubun="3"):
        
        LS_vars.code_drate = drate
        LS_vars.code_gubun = gubun
        LS_vars.code_days = days

        for data in LS_vars.month_scodes:
            await asyncio.sleep(3.5)

            shcode = data.get("shcode")
            hname = data.get("hname")

            await T8410_req.req(days=days, shcode=shcode, gubun=gubun)

            if LS_vars.code_drate_pass == True:
                print(f"{hname} 종목 주봉 추세 통과")
                LS_vars.week_scodes.append({
                    "shcode": shcode,
                    "hname":hname
                })

    
    async def daysMarket(days=0, drate=10, gubun="2"):
        
        LS_vars.code_drate = drate
        LS_vars.code_gubun = gubun
        LS_vars.code_days = days

        for data in LS_vars.week_scodes:
            await asyncio.sleep(3.5)

            shcode = data.get("shcode")
            hname = data.get("hname")

            await T8410_req.req(days=days, shcode=shcode, gubun=gubun)

            if LS_vars.code_drate_pass == True:
                print(f"{hname} 종목 일봉 장기 추세 통과")
                LS_vars.day_scodes.append({
                    "shcode": shcode,
                    "hname":hname
                })
    
    async def daysShortMarket(days=0, drate=5, gubun="2"):
        
        LS_vars.code_drate = drate
        LS_vars.code_gubun = gubun
        LS_vars.code_days = days

        for data in LS_vars.day_scodes:
            await asyncio.sleep(3.5)

            shcode = data.get("shcode")
            hname = data.get("hname")

            await T8410_req.req(days=days, shcode=shcode, gubun=gubun)

            if LS_vars.code_drate_pass == True:
                print(f"{hname} 종목 일봉 단기 추세 통과")
                LS_vars.day_short_scodes.append({
                    "shcode": shcode,
                    "hname":hname
                })