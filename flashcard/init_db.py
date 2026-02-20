import sqlite3
import os

# Connect to database
os.makedirs('data', exist_ok=True)
conn = sqlite3.connect('data/flashcards.db')
c = conn.cursor()

# Create table with a "box" column for Spaced Repetition (Leitner system)
# box 1 = new/hard, box 5 = mastered
c.execute('''CREATE TABLE IF NOT EXISTS cards
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              german TEXT, 
              german_example TEXT, 
              english TEXT, 
              english_example TEXT, 
              audio_file TEXT,
              box INTEGER DEFAULT 1,
              next_review_ts INTEGER DEFAULT 0)''')

# Check if table has data
c.execute("SELECT count(*) FROM cards")
count = c.fetchone()[0]
if count > 0:
    print(f"Database already has {count} cards. Skipping import.")
    conn.close()
    exit(0)

# Read your specific file format
file_path = 'Goethe Institute A1 Wordlist.txt'
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    count = 0
    for line in f:
        try:
            parts = line.strip().split('\t')
            if len(parts) < 5: continue
            
            # Parse columns based on your file structure
            # Index 0 is ID, we skip it or use it? Let's use auto-increment ID for simplicity
            german = parts[1]
            german_ex = parts[2]
            english = parts[3]
            english_ex = parts[4]
            
            # Extract audio filename from [sound:...]
            # It seems to be at the end, but let's look for the tag in the line to be safe
            audio = ""
            for part in parts:
                if '[sound:' in part:
                    audio = part.split('[sound:')[1].split(']')[0]
                    break

            c.execute("INSERT INTO cards (german, german_example, english, english_example, audio_file) VALUES (?, ?, ?, ?, ?)",
                      (german, german_ex, english, english_ex, audio))
            count += 1
        except Exception as e:
            print(f"Skipping line: {line[:20]}... Error: {e}")

conn.commit()
conn.close()
print(f"Database initialized with {count} cards!")
