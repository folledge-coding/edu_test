from globals import cursor, conn
from datetime import datetime


def create_positions_table():
    """
    보유종목 포지션 테이블 생성
    """
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shcode TEXT UNIQUE NOT NULL,
            hname TEXT NOT NULL,
            qty INTEGER NOT NULL,
            avg_price INTEGER NOT NULL,
            today_low INTEGER NOT NULL,
            sell_3_qty INTEGER NOT NULL,
            sell_5_qty INTEGER NOT NULL,
            sell_7_qty INTEGER NOT NULL,
            sell_3_done BOOLEAN DEFAULT FALSE,
            sell_5_done BOOLEAN DEFAULT FALSE,
            sell_7_done BOOLEAN DEFAULT FALSE,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def create_orders_table():
    """
    주문 내역 테이블 생성
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shcode TEXT NOT NULL,
            hname TEXT NOT NULL,
            order_type TEXT NOT NULL,
            qty INTEGER NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    ''')
    conn.commit()


def save_position(position_data):
    """
    포지션 정보 저장/업데이트
    """
    cursor.execute('''
        INSERT INTO positions 
        (shcode, hname, qty, avg_price, today_low, sell_3_qty, 
         sell_5_qty, sell_7_qty, sell_3_done, sell_5_done, 
         sell_7_done, status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(shcode) DO UPDATE SET
            qty = excluded.qty,
            today_low = excluded.today_low,
            sell_3_done = excluded.sell_3_done,
            sell_5_done = excluded.sell_5_done,
            sell_7_done = excluded.sell_7_done,
            status = excluded.status,
            updated_at = excluded.updated_at
    ''', (
        position_data["shcode"],
        position_data["hname"],
        position_data["qty"],
        position_data["avg_price"],
        position_data["today_low"],
        position_data["sell_3_qty"],
        position_data["sell_5_qty"],
        position_data["sell_7_qty"],
        position_data["sell_3_done"],
        position_data["sell_5_done"],
        position_data["sell_7_done"],
        position_data["status"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()


def load_positions():
    """
    저장된 포지션 정보 로드
    """
    cursor.execute('''
        SELECT * FROM positions 
        WHERE status IN ('active', 'stop_loss')
        ORDER BY created_at DESC
    ''')
    
    positions = {}
    for row in cursor.fetchall():
        positions[row["shcode"]] = {
            "shcode": row["shcode"],
            "hname": row["hname"],
            "qty": row["qty"],
            "avg_price": row["avg_price"],
            "current_price": row["avg_price"],  # 초기값
            "today_low": row["today_low"],
            "profit_rate": 0.0,
            "sell_3_qty": row["sell_3_qty"],
            "sell_5_qty": row["sell_5_qty"],
            "sell_7_qty": row["sell_7_qty"],
            "sell_3_done": row["sell_3_done"],
            "sell_5_done": row["sell_5_done"],
            "sell_7_done": row["sell_7_done"],
            "low_updated": False,
            "status": row["status"]
        }
    
    return positions


def save_order(order_data):
    """
    주문 내역 저장
    """
    cursor.execute('''
        INSERT INTO orders 
        (shcode, hname, order_type, qty, price, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        order_data["shcode"],
        order_data["hname"],
        order_data["order_type"],
        order_data["qty"],
        order_data["price"],
        order_data["status"]
    ))
    conn.commit()


def update_order_status(shcode, order_type, status):
    """
    주문 상태 업데이트
    """
    cursor.execute('''
        UPDATE orders 
        SET status = ?, completed_at = ?
        WHERE shcode = ? AND order_type = ? AND status = 'pending'
    ''', (
        status,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        shcode,
        order_type
    ))
    conn.commit()


def get_daily_summary():
    """
    일일 거래 요약 조회
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN order_type LIKE '%매도' THEN qty * price ELSE 0 END) as total_sell_amount
        FROM orders 
        WHERE DATE(created_at) = ?
    ''', (today,))
    
    return cursor.fetchone()


def cleanup_completed_positions():
    """
    완료된 포지션 정리
    """
    cursor.execute('''
        UPDATE positions 
        SET status = 'completed'
        WHERE qty <= 0 OR status = 'stop_loss'
    ''')
    conn.commit()
