"""
투자 메소드와
메소드를 통과한 종목들을 관리한다.
"""

from datetime import datetime
from globals import  MethodDict, PassedDict, cursor, conn


def createMethodsTable():
    """
    투자방법 테이블

    :param method_id: 투자방법 식별 이름
    :param accnum: 투자방법이 사용되는 계좌 (1:1 관계를 유지해라)
    :param detail: 투자방법 상세 설명
    """
    
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    method_id TEXT UNIQUE NOT NULL, 
                    accnum TEXT NOT NULL,
                    detail TEXT, 
                   
                    FOREIGN KEY (accnum) REFERENCES accounts (accnum)
                   )''')

    conn.commit()


def insertMethods(methods:list[MethodDict]):
    """
    매수에 사용하는 투자를 관리하는 테이블을 생성하고
    투자 기법들을 저장한다.
    """

    data = [(method['method_id'], method["accnum"], method["detail"]) for method in methods]  # 1만 개 데이터

    cursor.execute("BEGIN TRANSACTION")

    cursor.executemany("""
                       INSERT INTO methods (method_id, accnum, detail)
                       VALUES (?, ?, ?)
                       ON CONFLICT(method_id) DO NOTHING
                       """, data)

    conn.commit()


def clearPassedStocks():
    """
    보유중인 종목을 제외하고 전부 삭제
    excludeShcodes는 삭제에서 제외하려는 종목코드를 넣는다.
    """

    cursor.execute("""
    DELETE FROM passedStocks
    WHERE status != "account";
    """)

    conn.commit()

def createPassedStockTable():
    """
    매수하기 위해 주시하는 종목 테이블
    투자 분석에서 추출된 종목 모음 테이블이라고 봐도 된다.
    그리고 당일 장이 끝나면 테이블 중에 status가 "no" 또는 "complete"인 데이터들을 모두 삭제하고
    새로운 종목으로 채운다.

    :param shcode: 종목코드
    :param method_id: 투자방법 식별 이름
    :param addup_rate: 애드업을 위한 수익률 구간
    :param addup_cnt: 지금까지 진행된 애드업 횟수
    :param top_sunikrt: 최고 수익률이며 이를 기준으로 트레일링 스탑 비율이 정해진다
    :param status: "no": 진행된 게 없음 | "account": 보유중 | "complete": 매도까지 한사이클 돌았음
    :param create_date: 데이터 생성 날짜
    """
        
    cursor.execute("BEGIN TRANSACTION")
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS passedStocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shcode TEXT UNIQUE NOT NULL,
                    method_id TEXT NOT NULL,
                    addup_rate REAL DEFAULT 30.0,
                    addup_cnt INTEGER DEFAULT 0,
                    top_sunikrt REAL DEFAULT 0.0,
                    trailing_rate REAL DEFAULT -5.0,
                    status TEXT DEFAULT "no",
                    create_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                   
                    FOREIGN KEY (shcode) REFERENCES stocks (shcode)
                   )''')
    conn.commit()
    
def insertPassedStock(stock:PassedDict):
    """
    계좌가 여러개일 경우 종목을 동시간대에 중복으로 매매하게 될 수 있다.
    불법 거래로 오인될 수 있기 때문에 안정성을 위하여 종목을 중복으로 거래하면 안 된다.

    그러므로 거래중인 메소드와 종목은 1:1 관계로만 존재해야 한다.

    또한, 증권앱에서 매수 했을 경우에는 table에 종목이 없을 것이다. 그럴때는

    method_id를 "app"으로 저장한다.
    """

    # 중복 종목 저장 안 되도록 확인하기
    cursor.execute("""
        SELECT COUNT(*) FROM passedStocks 
        WHERE shcode = ?
    """, (stock['shcode'],))

    exists = cursor.fetchone()[0]

    if exists == 0:  # 동일한 데이터가 없을 때만 INSERT
        cursor.execute("""
            INSERT INTO passedStocks (shcode, method_id, status, create_date)
            VALUES (?, ?, ?, ?)
        """, (stock['shcode'], stock["method_id"], stock['status'], datetime.now().strftime("%Y-%m-%d"),))

        conn.commit()
    else: # 이미 존재하는 데이터로 인해 삽입하지 않고 업데이트만
        updatePassedOnlyStatus(
            shcode=stock['shcode'],
            status=stock["status"]
        )

def deletePassedStock(shcode:str):
    """
    주시하고 있는 종목 삭제하기
    """

    cursor.execute("""
    DELETE FROM passedStocks
    WHERE shcode = ?;
    """, (shcode,))

    conn.commit()
      
def getPassedStocksNotTrading():
    """
    거래를 한적 없는 종목들만 가져온다.
    """

    pass_stocks: list[PassedDict] = []

    query = """
        SELECT
            id,
            shcode,
            method_id,
            create_date,
            addup_rate,
            addup_cnt,
            top_sunikrt,
            trailing_rate,
            status
        FROM passedStocks
        WHERE status = "no"
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    ### 가장 최신 종목들 ###
    for passed in rows:
        pass_stocks.append(
            {
                "shcode": passed["shcode"],
                "method_id": passed["method_id"],
                "create_date": passed["create_date"],
                "addup_rate": passed["addup_rate"],
                "addup_cnt": passed["addup_cnt"],
                "top_sunikrt": passed["top_sunikrt"],
                "trailing_rate": passed["trailing_rate"],
                "status": passed["status"]
            }
        )

    return pass_stocks

def getPassedStock(shcode: str, status: str=None):
    """
    특정 조건의 종목만 가져온다.

    :param status: "no": 거래없음, "account": 보유중, "complete": 매매완료
    """

    if status is not None:
        query = """
            SELECT *
            FROM passedStocks
            WHERE shcode = ? AND status = ?
        """
        cursor.execute(query, (shcode, status,))
    else:
        query = """
            SELECT *
            FROM passedStocks
            WHERE shcode = ?
        """
        cursor.execute(query, (shcode,))
    
    row = cursor.fetchone()
    
    if row is not None:
        passed:PassedDict = {
            "shcode": row["shcode"],
            "method_id": row["method_id"],
            "create_date": row["create_date"],
            "addup_rate": row["addup_rate"],
            "addup_cnt": row["addup_cnt"],
            "top_sunikrt": row["top_sunikrt"],
            "trailing_rate": row["trailing_rate"],
            "status": row["status"]
        }
        return passed
    
    passed:PassedDict = {}
    return passed


def updatePassedToInfo(shcode:str, addup_rate:float, addup_cnt:int, top_sunikrt:float, trailing_rate:float, status:str):
    """
    종목의 정보들를 업데이트 한다.
    """

    cursor.execute("""
        UPDATE passedStocks
        SET 
            addup_rate = ?,
            addup_cnt = ?,
            top_sunikrt = ?,
            trailing_rate = ?,
            status = ?
        WHERE shcode = ?
    """, (addup_rate, addup_cnt, top_sunikrt, trailing_rate, status, shcode,))

    conn.commit()

    
def updatePassedOnlyStatus(shcode:str, status:str):
    """
    종목의 상태만 업데이트
    """

    cursor.execute("""
        UPDATE passedStocks
        SET 
            status = ?
        WHERE shcode = ?
    """, (status, shcode,))

    conn.commit()

      
def updatePassedOnlyTrailing(shcode:str, top_sunikrt:float, trailing_rate:float):
    """
    트레일링 비율만 업데이트
    """

    cursor.execute("""
        UPDATE passedStocks
        SET 
            top_sunikrt = ?,
            trailing_rate = ?
        WHERE shcode = ?
    """, (top_sunikrt, trailing_rate, shcode,))

    conn.commit()

def countPassedAccountedStocks():
    cursor.execute("""
        SELECT COUNT(*) FROM passedStocks 
        WHERE status = "account"
    """)
    
    result = cursor.fetchone()
    row_count = result[0]

    return row_count
