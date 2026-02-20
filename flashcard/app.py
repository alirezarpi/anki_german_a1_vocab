from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import time
import random
import os

app = FastAPI()

# Serve audio files
# Assuming audio/ is in the root directory
if not os.path.exists("audio"):
    os.makedirs("audio")
app.mount("/static/audio", StaticFiles(directory="audio"), name="audio")

templates = Jinja2Templates(directory="templates")

def get_db():
    conn = sqlite3.connect('data/flashcards.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/card")
def get_card():
    conn = get_db()
    c = conn.cursor()
    now = int(time.time())
    
    # Logic: Get cards due for review (next_review_ts < now)
    # Order by box (lower box = harder = show first)
    c.execute("SELECT * FROM cards WHERE next_review_ts < ? ORDER BY box ASC, random() LIMIT 1", (now,))
    card = c.fetchone()
    
    # If no cards are "due", just pick a random one to keep studying
    if not card:
        c.execute("SELECT * FROM cards ORDER BY random() LIMIT 1")
        card = c.fetchone()
        
    conn.close()
    if card:
        return dict(card)
    return {"error": "No cards found"}

@app.post("/api/result/{card_id}/{result}")
def submit_result(card_id: int, result: str):
    conn = get_db()
    c = conn.cursor()
    
    # Simple Leitner System
    # result = 'correct' -> move to next box, wait longer
    # result = 'wrong'   -> reset to box 1, show again soon
    
    c.execute("SELECT box FROM cards WHERE id = ?", (card_id,))
    row = c.fetchone()
    if not row: 
        conn.close()
        return {"error": "Card not found"}
    
    current_box = row['box']
    
    if result == 'correct':
        new_box = min(current_box + 1, 5) # Max box 5
        # Box 1=1min, 2=10min, 3=1day, 4=3days, 5=7days (simplified)
        wait_times = {1: 60, 2: 600, 3: 86400, 4: 259200, 5: 604800}
        next_review = int(time.time()) + wait_times.get(new_box, 60)
    else:
        new_box = 1
        next_review = int(time.time()) # Show immediately
        
    c.execute("UPDATE cards SET box = ?, next_review_ts = ? WHERE id = ?", 
              (new_box, next_review, card_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}
