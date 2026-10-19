from .database import get_connections

def create_user(telegram_id: int, name: str):
    # создаёт нового пользователя, возвращает его id
    conn = get_connections()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
        (telegram_id, name)
    )
    conn.commit()
    user_id=cur.lastrowid
    conn.close()
    return user_id

def get_user_by_telegram_id(telegram_id: int):
    # находит пользователя по его Telegram ID, или None если его нет
    conn = get_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_check_with_items(payer_id: int, title: str, payment_info: str, items: list):
    # создаёт чек и сразу все его позиции одним вызовом
    conn = get_connections()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO checks (payer_id, title, payment_info) VALUES (?, ?, ?)",
        (payer_id, title, payment_info)
    )
    check_id = cur.lastrowid


    for item in items:
        cur.execute(
            "INSERT INTO items (check_id, name, price, type) VALUES (?, ?, ?, ?)",
            (check_id, item.name, item.price, item.type)
        )

    conn.commit()
    conn.close()
    return check_id



def get_check_with_items(check_id: int):
    # возвращает чек вместе со списком его позиций, или None если чека нет
    conn = get_connections()
    cur = conn.cursor()

    cur.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
    check_row = cur.fetchone()

    if check_row is None:
        conn.close()
        return None

    cur.execute("SELECT * FROM items WHERE check_id = ?", (check_id,))
    item_rows = cur.fetchall()

    conn.close()
    check=dict(check_row)
    check["items"] = [dict(row) for row in item_rows]
    return check

def close_check(check_id: int):
    conn = get_connections()
    cur = conn.cursor()

    cur.execute("UPDATE checks SET status = 'closed' WHERE id = ?", (check_id,))
    conn.commit()
    conn.close()


def update_item(item_id: int, name: str = None, price: int = None, item_type: str = None):
    # обновляет только переданные поля позиции (остальные не трогает)
    conn = get_connections()
    cur = conn.cursor()

    fields = []
    values = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if price is not None:
        fields.append("price = ?")
        values.append(price)
    if item_type is not None:
        fields.append("type = ?")
        values.append(item_type)


    if not fields:
        conn.close()
        return

    values.append(item_id)
    query = f"UPDATE items SET {', '.join(fields)} WHERE id = ?"
    cur.execute(query, values)

    conn.commit()
    conn.close()


def delete_item(item_id: int):
    # удаляет позицию и все связанные с ней отметки claims
    conn = get_connections()
    cur = conn.cursor()

    cur.execute("DELETE FROM claims WHERE item_id = ?", (item_id,))
    cur.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def create_claims(item_id: int, user_id: int):
    # отмечает, что пользователь ел эту позицию
    conn = get_connections()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO claims (item_id, user_id) VALUES (?, ?)",
        (item_id, user_id)
    )
    conn.commit()
    claim_id = cur.lastrowid
    conn.close()
    return claim_id


def get_item_claims(item_id: int):
    # все отметки по конкретной позиции
    conn = get_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM claims WHERE item_id = ?", (item_id, ))
    rows = cur.fetchall()
    conn.close()
    return  [dict(row) for row in rows]

def get_check_claims(check_id: int):
    # все отметки по всем позициям чека сразу
    conn = get_connections()
    cur = conn.cursor()

    cur.execute("""
        SELECT claims.* FROM claims 
        JOIN items ON claims.item_id = items.id
        WHERE items.check_id = ?
    """, (check_id, ))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user(user_id: int):
    # Возвращает пользователя по внутреннему id или None
    conn = get_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_item(item_id: int):
    # Возвращает позицию по id или None
    conn = get_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_check(check_id: int):
    # Возвращает чек (без позиций) или None
    conn = get_connections()
    cur = conn.cursor()
    cur.execute("SELECT * FROM checks WHERE id = ?", (check_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_claim(item_id: int, user_id: int):
    # Ищет отметку конкретного человека на конкретной позиции
    conn = get_connections()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM claims WHERE item_id = ? AND user_id = ?",
        (item_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_claim(item_id: int, user_id: int):
    # Снимает отметку человека с позиции
    conn = get_connections()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM claims WHERE item_id = ? AND user_id = ?",
        (item_id, user_id)
    )
    conn.commit()
    conn.close()

def get_users_names(user_ids: list[int])->dict[int, str]:
    # Возвращает словарь {user_id: имя} для списка id.
    if not user_ids:
        return {}
    conn = get_connections()
    cur = conn.cursor()
    marks = ','.join("?" for _ in user_ids)
    cur.execute(f"SELECT id, name FROM users WHERE id IN ({marks})", user_ids)
    rows = cur.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row["id"]] = row["name"]
    return result


