import asyncio
import pythoncom
from datetime import datetime, time
import sys

from ls_res.login import Login_req
from ls_res.t0424 import T0424_req
from ls_res.cspaq12200 import Cspaq12200_req
from ls_res.sc0 import SC0_req
from ls_res.sc1 import SC1_req
from remote.telegram_bot import telegram_init
from database.trading_db import (
    create_positions_table,
    create_orders_table,
    load_positions,
    save_position,
    cleanup_completed_positions
)
from globals import LS_vars, send_telegram, cursor


async def main():
    """메인 실행 함수"""
    
    # 시작 메시지
    send_telegram("🚀 LS증권 자동매매 시스템 시작")
    
    # 텔레그램 초기화
    await telegram_init()
    
    # LS증권 로그인
    Login_req().req()
    
    # 데이터베이스 초기화
    create_positions_table()
    create_orders_table()
    
    # 기존 포지션 로드
    LS_vars.stock_positions = load_positions()
    send_telegram(f"📂 기존 포지션 {len(LS_vars.stock_positions)}개 로드완료")
    
    # 실시간 데이터 구독
    SC1_req.subscribe()  # 주문체결
    
    # 예수금 조회
    await Cspaq12200_req.req()
    
    # 보유종목 조회
    await T0424_req.req()
    
    # 실시간 시세 구독 (보유종목이 있는 경우)
    if LS_vars.stock_positions:
        SC0_req.subscribe_stocks()
    
    # 백그라운드 작업 시작
    asyncio.create_task(T0424_req.loop())  # 보유종목 조회 루프
    asyncio.create_task(Cspaq12200_req.loop())  # 예수금 조회 루프
    asyncio.create_task(market_time_monitor())  # 장시간 모니터링
    asyncio.create_task(position_backup_loop())  # 포지션 백업
    
    LS_vars.is_market_open = True
    send_telegram("✅ 자동매매 시스템 준비완료! 매수는 수동으로 진행해주세요.")
    
    # 메인 루프
    while True:
        await asyncio.sleep(0.01)
        pythoncom.PumpWaitingMessages()


async def market_time_monitor():
    """장시간 모니터링"""
    while True:
        now = datetime.now()
        current_time = now.time()
        
        # 장시작 (09:00)
        if current_time >= time(9, 0) and current_time <= time(9, 1):
            if not LS_vars.is_market_open:
                LS_vars.is_market_open = True
                send_telegram("📈 장시작! 자동매매 시스템 활성화")
                
                # 보유종목이 있으면 실시간 시세 구독
                if LS_vars.stock_positions:
                    SC0_req.subscribe_stocks()
        
        # 장마감 (15:30)
        elif current_time >= time(15, 30):
            if LS_vars.is_market_open:
                LS_vars.is_market_open = False
                send_telegram("📉 장마감! 자동매매 시스템 대기모드")
                
                # 오늘 거래 요약
                await send_daily_summary()
                
                # 완료된 포지션 정리
                cleanup_completed_positions()
        
        await asyncio.sleep(60)  # 1분마다 체크


async def position_backup_loop():
    """포지션 정보 주기적 백업"""
    while True:
        await asyncio.sleep(300)  # 5분마다
        
        # 모든 포지션 저장
        for position in LS_vars.stock_positions.values():
            save_position(position)


async def send_daily_summary():
    """일일 거래 요약 전송"""
    if not LS_vars.stock_positions:
        send_telegram("📊 오늘 거래 없음")
        return
    
    total_positions = len(LS_vars.stock_positions)
    active_positions = sum(
        1 for p in LS_vars.stock_positions.values() 
        if p["status"] == "active"
    )
    
    summary_msg = f"📊 오늘 거래 요약\n\n"
    summary_msg += f"총 포지션: {total_positions}개\n"
    summary_msg += f"활성 포지션: {active_positions}개\n"
    
    # 각 종목별 상태
    for position in LS_vars.stock_positions.values():
        summary_msg += f"\n{position['hname']}:\n"
        summary_msg += f"  수익률: {position['profit_rate']:.2f}%\n"
        
        sell_status = []
        if position["sell_3_done"]:
            sell_status.append("3%완료")
        if position["sell_5_done"]:
            sell_status.append("5%완료")
        if position["sell_7_done"]:
            sell_status.append("7%완료")
        
        if sell_status:
            summary_msg += f"  매도: {', '.join(sell_status)}\n"
        else:
            summary_msg += "  매도: 대기중\n"
    
    send_telegram(summary_msg)


async def emergency_stop():
    """긴급 중지"""
    LS_vars.is_market_open = False
    
    # 모든 포지션 저장
    for position in LS_vars.stock_positions.values():
        save_position(position)
    
    # DB 연결 종료
    cursor.close()
    
    send_telegram("🚨 시스템 긴급 중지됨")
    sys.exit()


if __name__ == "__main__":
    try:
        print("🤖 LS증권 자동매매 시스템 시작")
        send_telegram("🔧 시스템 초기화 중...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("사용자 중지 요청")
        asyncio.run(emergency_stop())
    except Exception as e:
        print(f"시스템 오류: {e}")
        send_telegram(f"🚨 시스템 오류 발생: {e}")
        asyncio.run(emergency_stop())
