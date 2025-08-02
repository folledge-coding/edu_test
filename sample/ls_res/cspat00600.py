import asyncio
from dotenv import load_dotenv
import os
import win32com.client
from globals import LS_vars, send_telegram
from database.account_db import insertTempOrderingStock

load_dotenv()

class Cspat00600_res:
        
    # tr 요청이 잘 됐는지만 체크한다. 예수금이 모자르거나 하면 에러가 반환될 것이다.
    def OnReceiveMessage(xingAPI, systemError, messageCode, message):
        """
        TR Code가10자리인TR에한해서에러코드의범위는다음과같습니다.
        0000~0999 : 정상(ex ) 0040 : 매수주문이완료되었습니다.)
        1000~7999 : 업무오류메시지(1584 : 매도잔고가부족합니다.)
        8000~9999 : 시스템에러메시지
        """
        # 에러 났을 경우에만 실행
        if int(systemError) == 1 or int(messageCode) < 0 or (1000 <= int(messageCode) and int(messageCode) <= 9999):
            print("CSPAT00600: systemError: %s, messageCode: %s, message: %s" % (systemError, messageCode, message), flush=True)
        


class Cspat00600_req:
    def order(accnum="", IsuNo="006730", BnsTpCode="1", OrdQty=1, hname="",
              sunikrt=0.0, top_sunikrt=0.0, addup_cnt=0, trailing_rate=-5.0, addup_rate=30.0):
        """
        매수/매도 주문 넣기
        주문 들어가면 예수금 갱신해줘야 한다.
        """
    
        insertTempOrderingStock(
            expcode=IsuNo,
            hname=hname,
            mdposqt=OrdQty,
            sunikrt=sunikrt,
            top_sunikrt=top_sunikrt,
            addup_rate=addup_rate,
            addup_cnt=addup_cnt,
            trailing_rate=trailing_rate
        )

        if LS_vars.cspat00600_event is None:
            LS_vars.cspat00600_event = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", Cspat00600_res)
            LS_vars.cspat00600_event.ResFileName = "C:/LS_SEC/xingAPI/Res/CSPAT00600.res"

        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "AcntNo", 0, accnum)
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "InptPwd", 0, os.getenv('LS-ACC-PWD'))
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "IsuNo", 0, IsuNo)
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "OrdQty", 0, OrdQty)
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "OrdPrc", 0, 0)
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "BnsTpCode", 0, BnsTpCode)
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "OrdprcPtnCode", 0, "03")
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "MgntrnCode", 0, "000")
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "LoanDt", 0, "")
        LS_vars.cspat00600_event.SetFieldData("CSPAT00600InBlock1", "OrdCndiTpCode", 0, "0")
        LS_vars.cspat00600_event.Request(False)