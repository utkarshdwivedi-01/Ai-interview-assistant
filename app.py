from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import PyPDF2
import io
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key'  # Required for sessions
DB_NAME = 'interview_app.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                role TEXT NOT NULL,
                quiz_score INTEGER,
                resume_score INTEGER,
                selection_prob INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()

# Call init on startup
init_db()

# Keywords for Resume Analysis
ROLE_KEYWORDS = {
    "Software Engineer": [
        "python", "java", "c++", "c#", "javascript", "react", "node", "sql", 
        "nosql", "git", "docker", "kubernetes", "aws", "azure", "api", "rest", 
        "agile", "cicd", "oop", "algorithms", "data structures"
    ],
    "Data Analyst": [
        "sql", "excel", "python", "r", "tableau", "powerbi", "pandas", 
        "numpy", "statistics", "data visualization", "a/b testing", 
        "machine learning", "regression", "metrics", "dashboard"
    ],
    "AI Engineer": [
        "python", "pytorch", "tensorflow", "keras", "machine learning", 
        "deep learning", "nlp", "computer vision", "transformers", "llm", 
        "pandas", "numpy", "scikit-learn", "data science", "neural networks"
    ]
}

# Mock database of MCQ questions based on job roles
QUESTIONS = {
    "Software Engineer": [
        {
            "question": "Which of the following is NOT a core principle of Object-Oriented Programming (OOP)?",
            "options": ["Encapsulation", "Compilation", "Inheritance", "Polymorphism"],
            "answer": "Compilation",
            "explanation": "Compilation is a process of converting source code into machine code, not a core principle of OOP. The 4 main OOP principles are Encapsulation, Inheritance, Polymorphism, and Abstraction.",
            "category": "Architecture & Paradigms"
        },
        {
            "question": "What is the time complexity of searching in a balanced Binary Search Tree (BST)?",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
            "answer": "O(log n)",
            "explanation": "In a balanced BST, each comparison halves the remaining search space, leading to a logarithmic time complexity O(log n).",
            "category": "Data Structures & Algorithms"
        },
        {
            "question": "Which HTTP method is typically used to update an existing resource completely?",
            "options": ["GET", "POST", "PUT", "PATCH"],
            "answer": "PUT",
            "explanation": "PUT is used to completely replace an existing resource. PATCH is used for partial updates, POST for creation, and GET for retrieval.",
            "category": "Web APIs & Networking"
        },
        {
            "question": "What does ACID stand for in the context of databases?",
            "options": [
                "Atomicity, Consistency, Isolation, Durability",
                "Accuracy, Completeness, Integration, Dependency",
                "Association, Connection, Interchange, Data",
                "Allocation, Control, Indexing, Domain"
            ],
            "answer": "Atomicity, Consistency, Isolation, Durability",
            "explanation": "ACIL are the defining properties of database transactions that guarantee data validity despite errors, power failures, or other mishaps.",
            "category": "Databases"
        },
        {
            "question": "Which design pattern ensures only one instance of a class is created?",
            "options": ["Factory", "Observer", "Singleton", "Decorator"],
            "answer": "Singleton",
            "explanation": "The Singleton pattern restricts the instantiation of a class to one single instance, often useful when exactly one object is needed to coordinate actions across the system.",
            "category": "Architecture & Paradigms"
        },
        {
            "question": "Which of these is considered a NoSQL database?",
            "options": ["PostgreSQL", "MySQL", "MongoDB", "SQLite"],
            "answer": "MongoDB",
            "explanation": "MongoDB is a widely used document-oriented NoSQL database. The others are relational (SQL) databases.",
            "category": "Databases"
        }
    ],
    "Data Analyst": [
        {
            "question": "Which SQL statement is used to combine rows from two or more tables based on a related column?",
            "options": ["MERGE", "JOIN", "COMBINE", "LINK"],
            "answer": "JOIN",
            "explanation": "A JOIN clause is used to combine rows from two or more tables, based on a related column between them.",
            "category": "Databases & SQL"
        },
        {
            "question": "What is the median of the following dataset: 2, 5, 9, 3, 5?",
            "options": ["2", "3", "5", "9"],
            "answer": "5",
            "explanation": "To find the median, sort the data (2, 3, 5, 5, 9). The middle value is 5.",
            "category": "Statistics"
        },
        {
            "question": "Which of the following describes a 'Type I error' in hypothesis testing?",
            "options": [
                "False Positive",
                "False Negative",
                "True Positive",
                "True Negative"
            ],
            "answer": "False Positive",
            "explanation": "A Type I error occurs when a true null hypothesis is incorrectly rejected (a false positive).",
            "category": "Statistics"
        },
        {
            "question": "In Python's Pandas library, which method is used to remove missing values?",
            "options": ["dropna()", "fillna()", "remove_na()", "delete_null()"],
            "answer": "dropna()",
            "explanation": "The dropna() method is used to analyze and remove missing values from Pandas Series and DataFrames.",
            "category": "Data Manipulation (Pandas)"
        },
        {
            "question": "What is the main purpose of A/B testing?",
            "options": [
                "To fix database bugs",
                "To build machine learning models",
                "To compare two versions of a variable to determine which performs better",
                "To clean a dataset"
            ],
            "answer": "To compare two versions of a variable to determine which performs better",
            "explanation": "A/B testing is a randomized experimentation process wherein two or more versions of a variable are shown to different segments of users simultaneously to determine which version leaves the maximum impact.",
            "category": "Experimentation"
        }
    ],
    "AI Engineer": [
        {
            "question": "What is the primary purpose of an activation function in a neural network?",
            "options": [
                "To initialize the weights",
                "To introduce non-linearity into the network",
                "To calculate the loss",
                "To reduce the dimensionality of the data"
            ],
            "answer": "To introduce non-linearity into the network",
            "explanation": "Activation functions (like ReLU, Sigmoid, Tanh) introduce non-linear properties to the network, allowing it to learn more complex relationships.",
            "category": "Deep Learning"
        },
        {
            "question": "Which of the following is a common technique used to prevent overfitting?",
            "options": ["Gradient Descent", "Backpropagation", "Dropout", "One-hot encoding"],
            "answer": "Dropout",
            "explanation": "Dropout randomly ignores a set of neurons during training, which prevents the network from becoming too dependent on specific weights and thereby reduces overfitting.",
            "category": "Model Training & Tuning"
        },
        {
            "question": "In natural language processing, what does 'TF-IDF' stand for?",
            "options": [
                "Term Frequency-Inverse Document Frequency",
                "Time Frequency-Index Data Format",
                "Text Format-Internal Data Feature",
                "Token Feature-Inverse Data Frequency"
            ],
            "answer": "Term Frequency-Inverse Document Frequency",
            "explanation": "TF-IDF is a statistical measure that evaluates how relevant a word is to a document in a collection of documents.",
            "category": "NLP"
        },
        {
            "question": "What architecture is most famous for introducing the 'Attention Is All You Need' mechanism?",
            "options": ["CNNs", "RNNs", "Transformers", "GANs"],
            "answer": "Transformers",
            "explanation": "The 2017 paper 'Attention Is All You Need' introduced the Transformer architecture, which strictly relies on attention mechanisms rather than recurrence (RNNs) for sequence modeling.",
            "category": "NLP / Deep Learning"
        },
        {
            "question": "Which algorithm is a popular choice for unsupervised clustering?",
            "options": ["Linear Regression", "Decision Trees", "K-Means", "Support Vector Machines"],
            "answer": "K-Means",
            "explanation": "K-Means is a classic unsupervised learning algorithm used for clustering unlabeled data into k different clusters based on feature similarity.",
            "category": "Machine Learning Algorithms"
        }
    ]
}

@app.route('/')
def index():
    """Render the dashboard page if logged in, otherwise redirect to login."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({"success": True, "redirect": url_for('index')})
        else:
            return jsonify({"success": False, "error": "Invalid credentials"}), 401
            
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json if request.is_json else request.form
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
        
    hashed_pass = generate_password_hash(password)
    db = get_db()
    
    try:
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pass))
        db.commit()
        # Auto-login after register
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({"success": True, "redirect": url_for('index')})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "Username already exists"}), 409

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/dashboard_data')
def dashboard_data():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    db = get_db()
    results = db.execute(
        'SELECT * FROM results WHERE user_id = ? ORDER BY date ASC', 
        (session['user_id'],)
    ).fetchall()
    
    # Format for charts
    history = [dict(row) for row in results]
    
    # Calculate some aggregates
    total_practices = len(history)
    latest_prob = history[-1]['selection_prob'] if history else 0
    avg_score = float(sum([r['quiz_score'] for r in history])) / total_practices if total_practices > 0 else 0.0
    
    return jsonify({
        "history": history,
        "total_practices": total_practices,
        "latest_prob": latest_prob,
        "avg_score": round(avg_score, 1)
    })

@app.route('/get_quiz', methods=['POST'])
def get_quiz():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    """Retrieve exactly 5 questions based on the selected role for the SPA quiz, and analyze an uploaded resume."""
    # Since we are sending FormData now, use form and files instead of json
    role = request.form.get('role')
    resume_file = request.files.get('resume')
    
    # Analyze Resume if provided
    resume_fit_score = 0
    matched_keywords = []
    missing_keywords = []
    formatting_feedback = []
    
    target_keywords = ROLE_KEYWORDS.get(role, [])
    
    extracted_text = ""
    
    if resume_file and resume_file.filename.endswith('.pdf'):
        try:
            # Read PDF in memory
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(resume_file.read()))
            for page in pdf_reader.pages:
                extracted_text += page.extract_text()
            
            text = extracted_text.lower()
            
            # Match keywords
            for keyword in target_keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            # --- Formatting / Layout Heuristics ---
            num_pages = len(pdf_reader.pages)
            char_count = len(text)
            
            # Check length constraint
            if num_pages > 2:
                formatting_feedback.append("Your resume is too long. Try to condense it into 1 or 2 pages for maximum impact.")
            elif num_pages == 0 or char_count < 500:
                formatting_feedback.append("Your resume appears too sparse. Ensure you have clear sections for Experience, Education, and Skills.")
            
            # Check text density (Too many words per page = poor readable font size/margins)
            words_per_page = (char_count / 5) / max(1, num_pages) # average 5 chars per word
            if words_per_page > 600:
                formatting_feedback.append("This resume is extremely text-dense. Increase your font size to at least 11pt-12pt and break up long paragraphs into bullet points for better readability.")
            
            # Check for Logo/Profile picture placeholders or structure
            has_linkedIn = "linkedin" in text
            has_github = "github" in text
            
            if not has_linkedIn and not has_github:
                formatting_feedback.append("Consider placing professional links (LinkedIn or GitHub) near the top. You may also add a minimalist professional logo or profile picture in the top corner to stand out visually.")
            
            if not formatting_feedback:
                formatting_feedback.append("Your resume layout and length look well-structured and optimal for ATS systems.")
                
            # --- End Formatting Heuristics ---
            
            # Calculate match percentage
            max_expected_keywords = min(10, len(target_keywords)) # Cap expectations
            raw_score = (len(matched_keywords) / max_expected_keywords) * 100
            resume_fit_score = min(int(raw_score), 100)
            
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            resume_fit_score = 50 
            missing_keywords = list(target_keywords)[:5]
            formatting_feedback = ["Could not parse PDF formatting. Please ensure the document is not encrypted."]
    else:
        # If no resume uploaded, give a baseline score and suggest keywords
        resume_fit_score = 40 
        missing_keywords = list(target_keywords)[:5] if target_keywords else []
        formatting_feedback = ["No resume uploaded for formatting analysis."]
    
    if role in QUESTIONS:
        # Get up to 5 random questions
        pool = QUESTIONS[role]
        selected_questions = random.sample(pool, min(5, len(pool)))
        
        # Send everything including answers and explanations directly to frontend 
        # so SPA can handle evaluation without server roundtrips
        quiz_data = []
        for q in selected_questions:
            # Shuffle options for variety
            shuffled_options = list(q["options"])
            random.shuffle(shuffled_options)
            quiz_data.append({
                "question": q["question"],
                "options": shuffled_options,
                "answer": q["answer"],
                "explanation": q.get("explanation", ""),
                "category": q.get("category", "")
            })
            
        return jsonify({
            "quiz": quiz_data,
            "resume_fit_score": resume_fit_score,
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "formatting_feedback": formatting_feedback
        })
        
    return jsonify({"error": "Invalid role selected."}), 400

@app.route('/api/save_result', methods=['POST'])
def save_result():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    try:
        db = get_db()
        db.execute('''
            INSERT INTO results (user_id, date, role, quiz_score, resume_score, selection_prob)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            data.get('role', 'Unknown'),
            data.get('quiz_score', 0),
            data.get('resume_score', 0),
            data.get('selection_prob', 0)
        ))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"DB Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
