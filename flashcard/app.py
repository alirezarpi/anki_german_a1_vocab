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

@app.get("/stats", response_class=HTMLResponse)
async def read_stats(request: Request):
    return templates.TemplateResponse("stats.html", {"request": request})

@app.get("/test", response_class=HTMLResponse)
async def read_test(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.get("/api/test/generate")
def generate_test():
    conn = get_db()
    c = conn.cursor()
    
    # Get learned cards (box > 1)
    c.execute("SELECT * FROM cards WHERE box > 1")
    learned_cards = c.fetchall()
    
    # Get all english meanings for distractors
    c.execute("SELECT english FROM cards")
    all_meanings = [r['english'] for r in c.fetchall()]
    
    conn.close()
    
    if not learned_cards:
        return {"error": "No learned words yet! Learn some words first."}
        
    # Select up to 10 random learned cards
    num_questions = min(len(learned_cards), 10)
    selected_cards = random.sample(learned_cards, num_questions)
    
    quiz = []
    for card in selected_cards:
        correct_answer = card['english']
        
        # Pick 3 distractors
        # Filter out the correct answer from potential distractors
        potential_distractors = [m for m in all_meanings if m != correct_answer]
        # If we don't have enough distractors (unlikely unless DB is tiny), handle it
        if len(potential_distractors) < 3:
            distractors = potential_distractors
        else:
            distractors = random.sample(potential_distractors, 3)
            
        options = [{'text': correct_answer, 'is_correct': True}]
        for d in distractors:
            options.append({'text': d, 'is_correct': False})
            
        random.shuffle(options)
        
        quiz.append({
            "id": card['id'],
            "german": card['german'],
            "options": options
        })
        
    return {"questions": quiz}

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM cards")
    rows = c.fetchall()
    conn.close()
    
    total = len(rows)
    known = 0
    learning = 0
    new_cards = 0
    
    words_list = []
    
    for row in rows:
        box = row['box']
        next_review = row['next_review_ts']
        
        status = 'new'
        if box > 1:
            status = 'known'
            known += 1
        elif box == 1 and next_review > 0:
            status = 'learning'
            learning += 1
        else:
            status = 'new'
            new_cards += 1
            
        words_list.append({
            "id": row['id'],
            "german": row['german'],
            "english": row['english'],
            "status": status
        })
        
    return {
        "total": total,
        "known": known,
        "learning": learning,
        "new": new_cards,
        "words": words_list
    }

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
