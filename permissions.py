from config import OWNER_ID
from db import get_user

# Проверка владельца
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# Проверка директора ресторана
def is_director(user_id: int) -> bool:
    user = get_user(user_id)
    return user and user.get("role") in ("director")

# Проверка директора или заместителя директора
def is_director_or_deputy(user_id: int) -> bool:
    user = get_user(user_id)    
    return user and user.get("role") in ("director", "deputy_director")

# Проверка контентмейкера (офисные сотрудники)
def is_content_maker(user_id: int) -> bool:
    user = get_user(user_id)
    return user and user.get("role") == "content_maker"

# Проверка шеф-повара
def is_chef(user_id: int) -> bool:
    user = get_user(user_id)
    return user and user.get("role") == "chef"

# Проверка официанта или бармена (обычный персонал ресторана)
def is_staff(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    # staff are users with a restaurant position, or chefs by role
    pos = user.get("position")
    return (pos in ["waiter", "bartender", "admin", "cook"]) or user.get("role") == "chef"

# Проверка администратора ресторана
def is_restaurant_admin(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    # admin of a restaurant is represented by position == 'admin'
    return user.get("position") == "admin"

# Общая проверка прав на админский функционал (CRUD)
def can_manage_bot(user_id: int) -> bool:
    return is_owner(user_id)


