"""
Mini Shop API —— 第 2 周的"被测系统"（SUT）

只用内存字典存数据，重启即清空。
目的不是做一个产品，是给你一个"可以测的靶子"。

启动：
    python -m uvicorn app:app --reload

打开接口文档：
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mini Shop API", version="0.1.0")

# ---------------- 内存数据 ----------------
users: dict[str, dict] = {}      # username -> {id, username, password}
tokens: dict[str, int] = {}      # token -> user_id
products: dict[int, dict] = {
    1: {"id": 1, "name": "机械键盘", "price": 399.0, "stock": 5},
    2: {"id": 2, "name": "显示器", "price": 1299.0, "stock": 2},
    3: {"id": 3, "name": "鼠标垫", "price": 29.0, "stock": 0},
}
orders: dict[int, dict] = {}

_next_user_id = 1
_next_order_id = 1


# ---------------- 请求体模型 ----------------
class RegisterIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class OrderIn(BaseModel):
    product_id: int
    quantity: int = 1


# ---------------- 健康检查 ----------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- 用户 ----------------
@app.post("/users/register")
def register(body: RegisterIn):
    global _next_user_id
    if body.username in users:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    user = {"id": _next_user_id, "username": body.username, "password": body.password}
    users[body.username] = user
    _next_user_id += 1
    return {"id": user["id"], "username": user["username"]}


@app.post("/users/login")
def login(body: LoginIn):
    user = users.get(body.username)
    if user is None or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = f"token-{user['id']}"
    tokens[token] = user["id"]
    return {"token": token, "user_id": user["id"]}


# ---------------- 商品 ----------------
@app.get("/products")
def list_products():
    return list(products.values())


@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


# ---------------- 订单 ----------------
@app.post("/orders")
def create_order(body: OrderIn, authorization: str | None = Header(default=None)):
    global _next_order_id

    user_id = tokens.get(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="未登录")

    product = products.get(body.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="数量必须大于 0")
    if product["stock"] < body.quantity:
        raise HTTPException(status_code=400, detail="库存不足")

    product["stock"] -= body.quantity
    order = {
        "id": _next_order_id,
        "user_id": user_id,
        "product_id": body.product_id,
        "quantity": body.quantity,
        "amount": round(product["price"] * body.quantity, 2),
        "status": "created",
    }
    orders[_next_order_id] = order
    _next_order_id += 1
    return order


@app.get("/orders")
def list_orders(user_id: int):
    return [o for o in orders.values() if o["user_id"] == user_id]


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@app.post("/orders/{order_id}/pay")
def pay_order(order_id: int, authorization: str | None = Header(default=None)):
    if tokens.get(authorization) is None:
        raise HTTPException(status_code=401, detail="未登录")
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] == "paid":
        raise HTTPException(status_code=400, detail="订单已支付")
    order["status"] = "paid"
    return order
