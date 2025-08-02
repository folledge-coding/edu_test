import asyncio
import win32com
from globals import LS_vars, send_telegram
from datetime import datetime, timedelta

class T8410_res:
    def OnReceiveData(xingApi, szCode):
        nDecompSize = xingApi.Decompress("t8410OutBlock1")
        if nDecompSize == 0:
            LS_vars.t8410_whileloop = True
            return
            
        shcode = xingApi.GetFieldData("t8410OutBlock", "shcode", 0)

        cnt = xingApi.GetBlockCount("t8410OutBlock1")
        prevDate = xingApi.GetFieldData("t8410OutBlock1", "date", 0)
        prevLow = int(xingApi.GetFieldData("t8410OutBlock1", "low", 0))
        prevHight = int(xingApi.GetFieldData("t8410OutBlock1", "high", 0))
        prevPrice = int(xingApi.GetFieldData("t8410OutBlock1", "close", 0))
        curDate = xingApi.GetFieldData("t8410OutBlock1", "date", cnt-1)
        curLow = int(xingApi.GetFieldData("t8410OutBlock1", "low", cnt-1))
        curHigh = int(xingApi.GetFieldData("t8410OutBlock1", "high", cnt-1))
        curPrice = int(xingApi.GetFieldData("t8410OutBlock1", "close", cnt-1))

        # 요청한 시작날짜와 끝날짜의 월/주/일자수를 계산한다.
        days = T8410_res.get_days_difference( prevDate, curDate )
        if days < LS_vars.code_days:
            LS_vars.t8410_whileloop = True
            return

        # 일자봉인지 확인한다. 일자봉은 거래가 없었기 때문에 패쓰해야 한다.
        lineCandle = prevLow == prevHight or curLow == curHigh
        
        drate = (curPrice - prevPrice) / prevPrice * 100
        drate = round(drate)

        if shcode == "069500":
        
            if drate >= LS_vars.korea_drate:
                print(f"한국증시 통과, 등락율차이:{drate}")
                LS_vars.korea_drate_pass = True

        elif drate >= LS_vars.code_drate and lineCandle is False:
            LS_vars.code_drate_pass = True

        LS_vars.t8410_whileloop = True

    def get_days_difference(start_date: str, end_date: str) -> int:
        """
        YYYYMMDD 형식의 문자열로 된 시작 날짜와 끝 날짜를 받아
        두 날짜 사이의 일수 차이를 반환합니다.
        
        매개변수:
            start_date (str): 시작 날짜 (예: "20221020")
            end_date (str): 끝 날짜 (예: "20241020")
        
        반환값:
            int: 두 날짜 사이의 일수 차이 (end_date - start_date)
                start_date가 end_date보다 이후면 음수로 반환됩니다.
        """
        date_format = "%Y%m%d"
        dt_start = datetime.strptime(start_date, date_format)
        dt_end = datetime.strptime(end_date, date_format)
        delta = dt_end - dt_start

        days = delta.days

        # 월봉/주봉/일봉이 공휴일 및 여러 가지 이유로 인해
        # 내가 주시하는 기간 내에 봉 한~두 개가 덜 선택되었을 수도 있다.
        # 이를 감안하여, 내가 요청한 일자 수보다 약간 더 길게 범위를 설정한다.
        # 즉, 누락된 봉의 수에 해당하는 대략적인 일자 수를 추가로 고려한다.
        if LS_vars.code_gubun == "4":
            days = days + 30
        elif LS_vars.code_gubun == "3":
            days = days + 10
        elif LS_vars.code_gubun == "2":
            days = days + 7

        return days


    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        # 에러 났을 경우에만 실행
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            LS_vars.code_drate_pass = False
            LS_vars.t8410_whileloop = True
            print("systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        
            
class T8410_req:

    async def req(days:int=365, shcode:str="", gubun:str="4"):
        current_date = datetime.now()
        endDateStr = current_date.strftime('%Y%m%d')
        startDate = current_date - timedelta(days=days)
        startDateStr = startDate.strftime('%Y%m%d')

        if LS_vars.t8410_event is None:
            LS_vars.t8410_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", T8410_res)
            LS_vars.t8410_event.ResFileName = "C:/LS_SEC/xingAPI/Res/t8410.res"

        LS_vars.t8410_event.SetFieldData("t8410InBlock", "shcode", 0, shcode)
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "gubun", 0, gubun)
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "qrycnt", 0, 2000)
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "sdate", 0, startDateStr)
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "edate", 0, endDateStr)
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "cts_date", 0, "")
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "comp_yn", 0, "Y")
        LS_vars.t8410_event.SetFieldData("t8410InBlock", "sujung", 0, "N")
        LS_vars.t8410_event.Request(False)

        LS_vars.code_drate_pass = False
        LS_vars.t8410_whileloop = False
        while LS_vars.t8410_whileloop == False:
            await asyncio.sleep(0.01)
