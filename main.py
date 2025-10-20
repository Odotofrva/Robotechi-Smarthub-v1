from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import matplotlib.pyplot as plt
from fastapi.responses import FileResponse
import os

import pg8000


app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Database connection must be conneted via .env file (security)
# Will achieve this later once app is completed.

def get_db_connection():
    conn = pg8000.connect(
        user="postgres",
        password="12345",
        host="localhost",
        port=5432,
        database="robotechi"
    )
    return conn


### Database connection ENDS ******


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with get_db_connection() as conn:
        cursor = conn.cursor() 
        cursor.execute("SELECT * FROM inventory ORDER BY id;") 
        inventory = cursor.fetchall()
    return templates.TemplateResponse("inventory.html", {"request": request, "inventory": inventory})



@app.get("/members", response_class=HTMLResponse)
async def members(request: Request):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members ORDER BY last_name")
        members = cursor.fetchall()
    return templates.TemplateResponse("members.html", {"request": request, "members": members})





@app.get("/purchases", response_class=HTMLResponse)
async def purchases(request: Request):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchases")
        purchases = cursor.fetchall()
    return templates.TemplateResponse("purchases.html", {"request": request, "purchases": purchases})


@app.get("/update_inventory/{item_id}", response_class=HTMLResponse)
async def update_inventory_form(request: Request, item_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return templates.TemplateResponse("404.html", {"request": request})  # 404 error 
    return templates.TemplateResponse("update_inventory.html", {"request": request, "item": item})

@app.post("/update_inventory/{item_id}")
async def update_inventory(
    item_id: int,
    part_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    unit_price: float = Form(...),
    quantity: int = Form(...)
):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inventory
                SET part_id = %s, name = %s, description = %s, unit_price = %s, quantity = %s
                WHERE id = %s
            """, (part_id, name, description, unit_price, quantity, item_id))
            conn.commit()
    except Exception as e:
        print(f"Error updating inventory: {e}")  
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/visualization", response_class=HTMLResponse)
async def visualization(request: Request):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetch purchases with member info and calculate totals
        cursor.execute("""
            SELECT m.first_name, m.last_name, SUM(p.total_price) AS total_spent
            FROM purchases p
            JOIN members m ON p.member_id = m.id
            GROUP BY m.id
            ORDER BY total_spent DESC
        """)
        purchase_totals = cursor.fetchall()

    # Prepare data for the plot
    names = [f"{member[0]} {member[1]}" for member in purchase_totals]
    totals = [member[2] for member in purchase_totals]

    # Create a bar plot
    plt.figure(figsize=(10, 5))
    plt.bar(names, totals, color='blue')
    plt.xlabel('Members')
    plt.ylabel('Total Spent ($)')
    plt.title('Total Purchase Amounts by Member')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save the plot as an image file
    image_path = "static/purchase_totals.png"
    plt.savefig(image_path)
    plt.close()  # Close the plot to free memory

    return templates.TemplateResponse("visualization.html", {"request": request, "image_path": image_path})