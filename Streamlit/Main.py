import streamlit as st
import requests
import json
import random
from datetime import datetime
import os
import time

# -------------------------
# CONFIGURATION - OpenAI API Key
# -------------------------
def get_api_key():
    """Get API key from multiple sources"""
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except (FileNotFoundError, KeyError):
            pass
    
    return api_key

API_KEY = get_api_key()

if not API_KEY:
    st.error("🚨 No API key found!")
    st.warning("""
    **Please add your OpenAI API key using ONE of these methods:**
    
    **Method 1: Streamlit Secrets (For local development)**
    
    Create `.streamlit/secrets.toml` in your project root:
    ```toml
    OPENAI_API_KEY = "sk-proj-your-openai-api-key-here"
    ```
    
    **Method 2: Environment Variable**
    ```bash
    export OPENAI_API_KEY="sk-proj-your-openai-api-key-here"
    ```
    
    Get your API key at: https://platform.openai.com/api-keys
    
    ⚠️ **IMPORTANT:** Make sure you have:
    1. Added credits to your OpenAI account
    2. Set up billing at https://platform.openai.com/account/billing
    """)
    st.stop()

# OpenAI API endpoint
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# -------------------------
# Rate Limiting Configuration
# -------------------------
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 3,
    "min_delay_seconds": 20,
    "max_retries": 3,
    "retry_delay": 30
}

# -------------------------
# Backend: OpenAI Quiz Generator with Rate Limiting
# -------------------------
def generate_quiz(text, num_questions=5):
    """Generate quiz questions using OpenAI API with rate limiting"""
    if not text or not text.strip():
        return None, "Please provide text to generate questions from."
    
    if not API_KEY:
        return None, "API key is required."
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    prompt = f"""Create exactly {num_questions} multiple-choice questions from the following text.

IMPORTANT: Return ONLY valid JSON in this EXACT format with no additional text:

{{
  "quiz": [
    {{
      "question": "What is the main topic?",
      "options": ["a) Option 1", "b) Option 2", "c) Option 3", "d) Option 4"],
      "answer": "b) Option 2",
      "explanation": "Brief explanation here"
    }}
  ]
}}

Rules:
- Create clear questions based ONLY on the text below
- Each question must have exactly 4 options (a, b, c, d)
- Only ONE correct answer per question
- Include brief explanations
- Return ONLY the JSON, no markdown, no extra text

Text to analyze:
{text[:2000]}"""

    data = {
        "model": "gpt-4o-mini",  # Using newer model instead of gpt-3.5-turbo
        "messages": [
            {"role": "system", "content": "You are a helpful quiz generator that returns only valid JSON responses."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 1500  # Reduced from 2048
    }

    # Retry logic
    for attempt in range(RATE_LIMIT_CONFIG["max_retries"]):
        try:
            response = requests.post(OPENAI_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', RATE_LIMIT_CONFIG["retry_delay"])
                try:
                    retry_after = int(retry_after)
                except:
                    retry_after = RATE_LIMIT_CONFIG["retry_delay"]
                
                if attempt < RATE_LIMIT_CONFIG["max_retries"] - 1:
                    st.warning(f"⏳ Rate limit hit from OpenAI. Waiting {retry_after} seconds... (Attempt {attempt + 1}/{RATE_LIMIT_CONFIG['max_retries']})")
                    time.sleep(retry_after)
                    continue
                else:
                    return None, f"""⏳ **OpenAI Rate Limit Exceeded**
                    
Your OpenAI API is being throttled. This means:

1. **No Credits/Billing**: You need to add payment method
2. **Free Tier Exhausted**: Daily/monthly quota used up
3. **Too Many Requests**: Hitting OpenAI's rate limits

**Solutions:**
✅ Add credits: https://platform.openai.com/account/billing/overview
✅ Check usage: https://platform.openai.com/usage
✅ Wait a few minutes and try again
✅ Reduce questions to 3-5 per quiz

**Make sure:**
- Your API key is valid
- Billing is set up
- You have available credits
"""
            
            if response.status_code == 401:
                return None, """❌ **Invalid API Key**

Your API key is not working. Please check:

1. Copy your key again from: https://platform.openai.com/api-keys
2. Make sure it starts with 'sk-proj-' or 'sk-'
3. Update your `.streamlit/secrets.toml` file:
   ```
   OPENAI_API_KEY = "sk-proj-your-actual-key"
   ```
4. Restart the Streamlit app
"""
            
            if response.status_code == 403:
                return None, """❌ **Access Denied - No Billing Setup**
                
Your API key exists but has no access. This means:

**You MUST set up billing first:**
1. Go to: https://platform.openai.com/account/billing/overview
2. Click "Add payment method"
3. Add a credit/debit card
4. Add at least $5 in credits
5. Wait 5-10 minutes for activation

**Note:** Even with a valid API key, you CANNOT use the API without adding a payment method and credits.

Check your account status: https://platform.openai.com/account/billing/overview
"""
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                
                # Show detailed error
                return None, f"""❌ **OpenAI API Error {response.status_code}**

{error_message}

**Common Issues:**
- 401: Invalid API key
- 403: No billing/credits set up
- 429: Rate limit or quota exceeded
- 500: OpenAI server error (try again)

**Check:**
1. API Key: https://platform.openai.com/api-keys
2. Billing: https://platform.openai.com/account/billing/overview
3. Usage: https://platform.openai.com/usage

**Full error:** {error_data}
"""

            result = response.json()
            generated_text = result['choices'][0]['message']['content'].strip()
            
            # Clean markdown
            if generated_text.startswith('```json'):
                generated_text = generated_text[7:]
            if generated_text.startswith('```'):
                generated_text = generated_text[3:]
            if generated_text.endswith('```'):
                generated_text = generated_text[:-3]
            generated_text = generated_text.strip()

            try:
                quiz_data = json.loads(generated_text)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if match:
                    try:
                        quiz_data = json.loads(match.group())
                    except:
                        return None, "Failed to parse quiz response."
                else:
                    return None, "Failed to parse quiz response."

            quiz_questions = quiz_data.get("quiz", [])
            
            if not quiz_questions:
                return None, "No questions generated. Try with more detailed text."
            
            for q in quiz_questions:
                if "options" in q and "answer" in q and "question" in q:
                    correct = q["answer"]
                    random.shuffle(q["options"])
                    q["answer"] = correct
                else:
                    return None, "Invalid question format received."

            return quiz_questions, None
            
        except requests.exceptions.Timeout:
            if attempt < RATE_LIMIT_CONFIG["max_retries"] - 1:
                time.sleep(5)
                continue
            return None, "⏱️ Request timed out."
        except requests.exceptions.RequestException as e:
            return None, f"🌐 Network error: {str(e)}"
        except Exception as e:
            return None, f"❌ Unexpected error: {str(e)}"
    
    return None, "Failed after multiple retries."

# -------------------------
# Initialize Session State
# -------------------------
def init_session_state():
    defaults = {
        "page": "main",
        "paragraphs": [],
        "saved_quizzes": {},
        "current_quiz_index": None,
        "user_answers": {},
        "show_results": False,
        "quiz_history": [],
        "num_questions": 5,
        "api_calls_made": 0,
        "last_api_call": 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="📘 Smart Study Partner",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# CSS Styling - Dark Mode Only
# -------------------------
st.markdown("""
<style>
    .stApp {
        background: #0f172a;
        color: #f1f5f9;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .api-badge {
        position: fixed;
        top: 10px;
        left: 10px;
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
    }
    
    .card {
        background: #1e293b;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 1.5rem;
    }
    
    .question-box {
        background: #1e293b;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #8b5cf6;
        margin-bottom: 1.5rem;
    }
    
    .stats-box {
        background: #1e293b;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #8b5cf6;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .stats-number {
        font-size: 2rem;
        font-weight: bold;
        color: #8b5cf6;
    }
    
    .stats-label {
        font-size: 0.9rem;
        color: #cbd5e1;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        color: white;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        border: none;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
    }
    
    .stRadio > div > label {
        background: #1e293b;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 2px solid #334155;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }
    
    .stRadio > div > label:hover {
        border-color: #8b5cf6;
        transform: translateX(4px);
    }
    
    .score-card {
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        color: white;
        margin: 2rem 0;
    }
    
    .history-item {
        background: #1e293b;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #8b5cf6;
        margin-bottom: 1rem;
    }
    
    .mini-stat {
        background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# API Usage Badge (Top Left)
st.markdown(f'<div class="api-badge">🤖 API Calls: {st.session_state.api_calls}</div>', unsafe_allow_html=True)

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.title("📌 Navigation")
    
    st.markdown("---")
    
    # Navigation Buttons
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "main"
        st.session_state.show_results = False
        st.rerun()
    
    if st.button("📚 My Quizzes", use_container_width=True):
        st.session_state.page = "library"
        st.rerun()
    
    if st.button("📊 Statistics", use_container_width=True):
        st.session_state.page = "stats"
        st.rerun()
    
    if st.button("📜 History", use_container_width=True):
        st.session_state.page = "history"
        st.rerun()
    
    st.markdown("---")
    
    # Quick Stats
    st.subheader("📈 Quick Stats")
    
    accuracy = 0
    if st.session_state.total_questions_answered > 0:
        accuracy = (st.session_state.total_correct_answers / st.session_state.total_questions_answered) * 100
    
    st.markdown(f"""
    <div class='mini-stat'>
        <div style='font-size: 1.5rem; font-weight: bold; color: #8b5cf6;'>{len(st.session_state.saved_quizzes)}</div>
        <div style='font-size: 0.8rem; color: #cbd5e1;'>Total Quizzes</div>
    </div>
    <div class='mini-stat'>
        <div style='font-size: 1.5rem; font-weight: bold; color: #8b5cf6;'>{st.session_state.total_questions_answered}</div>
        <div style='font-size: 0.8rem; color: #cbd5e1;'>Questions Answered</div>
    </div>
    <div class='mini-stat'>
        <div style='font-size: 1.5rem; font-weight: bold; color: #8b5cf6;'>{accuracy:.1f}%</div>
        <div style='font-size: 0.8rem; color: #cbd5e1;'>Overall Accuracy</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Settings
    st.subheader("⚙️ Settings")
    num_q = st.slider("Questions per quiz", 3, 10, st.session_state.num_questions)
    st.session_state.num_questions = num_q
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    if st.button("🗑️ Clear All Data", use_container_width=True):
        if st.session_state.paragraphs or st.session_state.saved_quizzes:
            st.session_state.paragraphs = []
            st.session_state.saved_quizzes = {}
            st.session_state.quiz_history = []
            st.success("🗑️ All data cleared!")
            st.rerun()
    
    if st.button("🔄 Reset Stats", use_container_width=True):
        st.session_state.api_calls = 0
        st.session_state.total_questions_answered = 0
        st.session_state.total_correct_answers = 0
        st.success("📊 Stats reset!")
        st.rerun()
    
    if st.session_state.saved_quizzes:
        if st.button("🎲 Random Quiz", use_container_width=True):
            random_idx = random.choice(list(st.session_state.saved_quizzes.keys()))
            st.session_state.current_quiz_index = random_idx
            st.session_state.user_answers = {}
            st.session_state.show_results = False
            st.session_state.page = "quiz"
            st.rerun()
    
    st.markdown("---")
    st.caption("💡 Powered by OpenAI GPT-4o-mini")

# -------------------------
# MAIN PAGE
# -------------------------
if st.session_state.page == "main":
    st.title("📘 Quiz Generator")
    st.markdown("### Create intelligent quizzes from your study material")
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    user_input = st.text_area(
        "📥 Paste Your Study Material",
        height=200,
        placeholder="Enter your text here (max 2000 characters)...",
        max_chars=2000
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Add Paragraph", use_container_width=True):
            if user_input and user_input.strip():
                st.session_state.paragraphs.append(user_input.strip())
                st.success("✅ Paragraph added!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter some text first!")
    
    with col2:
        if st.button("⚡ Add & Generate", use_container_width=True):
            if user_input and user_input.strip():
                st.session_state.paragraphs.append(user_input.strip())
                idx = len(st.session_state.paragraphs) - 1
                
                with st.spinner("🧠 Generating quiz..."):
                    quiz, error = generate_quiz(user_input.strip(), st.session_state.num_questions)
                
                if error:
                    st.error(f"❌ {error}")
                elif quiz:
                    st.session_state.saved_quizzes[idx] = quiz
                    st.session_state.api_calls += 1
                    st.success(f"✅ Generated {len(quiz)} questions!")
                    st.rerun()
            else:
                st.warning("⚠️ Please enter some text first!")
    
    with col3:
        if st.session_state.paragraphs:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.paragraphs = []
                st.session_state.saved_quizzes = {}
                st.success("🗑️ All cleared!")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Saved paragraphs
    if st.session_state.paragraphs:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(f"📚 Saved Paragraphs ({len(st.session_state.paragraphs)})")
        
        for i, para in enumerate(st.session_state.paragraphs):
            with st.expander(f"Paragraph {i+1} ({len(para)} characters)"):
                st.markdown(f"{para[:300]}{'...' if len(para) > 300 else ''}")
                
                if i in st.session_state.saved_quizzes:
                    st.success(f"✅ Quiz ready! ({len(st.session_state.saved_quizzes[i])} questions)")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"📖 Take Quiz", key=f"take_{i}", use_container_width=True):
                            st.session_state.current_quiz_index = i
                            st.session_state.user_answers = {}
                            st.session_state.show_results = False
                            st.session_state.page = "quiz"
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🔄 Regenerate", key=f"regen_{i}", use_container_width=True):
                            del st.session_state.saved_quizzes[i]
                            with st.spinner("🧠 Generating..."):
                                quiz, error = generate_quiz(para, st.session_state.num_questions)
                            
                            if error:
                                st.error(f"❌ {error}")
                            elif quiz:
                                st.session_state.saved_quizzes[i] = quiz
                                st.session_state.api_calls += 1
                                st.success(f"✅ New quiz generated!")
                                st.rerun()
                    
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"del_{i}", use_container_width=True):
                            del st.session_state.paragraphs[i]
                            if i in st.session_state.saved_quizzes:
                                del st.session_state.saved_quizzes[i]
                            st.success("🗑️ Deleted!")
                            st.rerun()
                
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"⚡ Generate Quiz", key=f"gen_{i}", use_container_width=True):
                            with st.spinner("🧠 Generating quiz..."):
                                quiz, error = generate_quiz(para, st.session_state.num_questions)
                            
                            if error:
                                st.error(f"❌ {error}")
                            elif quiz:
                                st.session_state.saved_quizzes[i] = quiz
                                st.session_state.api_calls += 1
                                st.success(f"✅ Generated {len(quiz)} questions!")
                                st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ Delete", key=f"del2_{i}", use_container_width=True):
                            del st.session_state.paragraphs[i]
                            st.success("🗑️ Deleted!")
                            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# QUIZ LIBRARY PAGE
# -------------------------
elif st.session_state.page == "library":
    st.title("📚 My Quiz Library")
    
    if not st.session_state.saved_quizzes:
        st.info("No quizzes yet. Go to Home and create one!")
        if st.button("🏠 Go Home", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**Total Quizzes:** {len(st.session_state.saved_quizzes)}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        for idx, quiz in st.session_state.saved_quizzes.items():
            para_preview = st.session_state.paragraphs[idx][:100] + "..."
            
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 📖 Quiz {idx+1}")
                st.markdown(f"**Questions:** {len(quiz)}")
                st.markdown(f"**Source:** {para_preview}")
            
            with col2:
                if st.button(f"▶️ Take", key=f"lib_{idx}", use_container_width=True):
                    st.session_state.current_quiz_index = idx
                    st.session_state.user_answers = {}
                    st.session_state.show_results = False
                    st.session_state.page = "quiz"
                    st.rerun()
                
                if st.button(f"🗑️ Delete", key=f"libdel_{idx}", use_container_width=True):
                    del st.session_state.saved_quizzes[idx]
                    del st.session_state.paragraphs[idx]
                    st.success("🗑️ Quiz deleted!")
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# STATISTICS PAGE
# -------------------------
elif st.session_state.page == "stats":
    st.title("📊 Your Statistics")
    
    accuracy = 0
    if st.session_state.total_questions_answered > 0:
        accuracy = (st.session_state.total_correct_answers / st.session_state.total_questions_answered) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{st.session_state.api_calls}</div>
            <div class='stats-label'>API Calls Made</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{len(st.session_state.saved_quizzes)}</div>
            <div class='stats-label'>Quizzes Generated</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{len(st.session_state.quiz_history)}</div>
            <div class='stats-label'>Quizzes Taken</div>
        </div>
        """, unsafe_allow_html=True)
    
    col4, col5 = st.columns(2)
    
    with col4:
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{st.session_state.total_questions_answered}</div>
            <div class='stats-label'>Total Questions Answered</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{accuracy:.1f}%</div>
            <div class='stats-label'>Overall Accuracy</div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.session_state.quiz_history:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📈 Performance Over Time")
        
        scores = [h['percentage'] for h in st.session_state.quiz_history]
        avg_score = sum(scores) / len(scores)
        
        st.markdown(f"**Average Score:** {avg_score:.1f}%")
        st.markdown(f"**Best Score:** {max(scores):.1f}%")
        st.markdown(f"**Latest Score:** {scores[-1]:.1f}%")
        
        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# HISTORY PAGE
# -------------------------
elif st.session_state.page == "history":
    st.title("📜 Quiz History")
    
    if st.button("🏠 Go Home", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()
    
    if not st.session_state.quiz_history:
        st.info("No quiz history yet. Take some quizzes to see your history!")
    else:
        st.markdown(f"**Total Attempts:** {len(st.session_state.quiz_history)}")
        
        for i, record in enumerate(reversed(st.session_state.quiz_history)):
            st.markdown(f"""
            <div class='history-item'>
                <h4>📝 Attempt #{len(st.session_state.quiz_history) - i}</h4>
                <p><strong>Date:</strong> {record['date']}</p>
                <p><strong>Quiz:</strong> Quiz {record['quiz_index'] + 1}</p>
                <p><strong>Score:</strong> {record['score']}/{record['total']} ({record['percentage']:.1f}%)</p>
            </div>
            """, unsafe_allow_html=True)

# -------------------------
# QUIZ PAGE
# -------------------------
elif st.session_state.page == "quiz":
    if st.session_state.current_quiz_index is None:
        st.warning("⚠️ No quiz selected.")
        if st.button("🏠 Go Home"):
            st.session_state.page = "main"
            st.rerun()
    else:
        quiz = st.session_state.saved_quizzes[st.session_state.current_quiz_index]
        
        col_main, col_side = st.columns([3, 1])
        
        with col_side:
            # Count answered questions more accurately
            answered = sum(1 for i in range(len(quiz)) if st.session_state.user_answers.get(i) is not None)
            
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{answered}/{len(quiz)}</div>
                <div class='stats-label'>Answered</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(answered / len(quiz))
            
            if st.button("✅ Submit", use_container_width=True, disabled=(answered < len(quiz))):
                st.session_state.show_results = True
                st.rerun()
            
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.user_answers = {}
                st.session_state.show_results = False
                st.rerun()
            
            if st.button("🏠 Home", use_container_width=True):
                st.session_state.page = "main"
                st.session_state.show_results = False
                st.rerun()
            
            if st.button("📚 My Quizzes", use_container_width=True):
                st.session_state.page = "library"
                st.session_state.show_results = False
                st.rerun()
        
        with col_main:
            if not st.session_state.show_results:
                st.title("🎮 Quiz Time!")
                st.info("💡 Retake unlimited times - no extra API calls!")
                
                for i, q in enumerate(quiz):
                    st.markdown(f"<div class='question-box'>", unsafe_allow_html=True)
                    st.markdown(f"**Question {i+1}**")
                    st.markdown(f"### {q['question']}")
                    
                    current = st.session_state.user_answers.get(i)
                    
                    answer = st.radio(
                        "Select:",
                        options=q["options"],
                        index=None if current is None else q["options"].index(current),
                        key=f"radio_{i}",
                        label_visibility="collapsed"
                    )
                    
                    # Update answer immediately when selected
                    if answer is not None:
                        st.session_state.user_answers[i] = answer
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            else:
                st.title("📊 Results")
                
                score = 0
                total = len(quiz)
                
                for i, q in enumerate(quiz):
                    user_ans = st.session_state.user_answers.get(i)
                    correct_ans = q["answer"]
                    
                    if user_ans == correct_ans:
                        score += 1
                    
                    st.markdown(f"<div class='question-box'>", unsafe_allow_html=True)
                    
                    if user_ans == correct_ans:
                        st.success(f"✅ Question {i+1}: Correct!")
                    else:
                        st.error(f"❌ Question {i+1}: Incorrect")
                    
                    st.markdown(f"**{q['question']}**")
                    st.markdown(f"**Your answer:** {user_ans if user_ans else 'No answer'}")
                    
                    if user_ans != correct_ans:
                        st.markdown(f"**Correct answer:** {correct_ans}")
                    
                    if "explanation" in q:
                        with st.expander("💡 Explanation"):
                            st.info(q["explanation"])
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                percentage = (score / total) * 100
                
                # Update global stats
                st.session_state.total_questions_answered += total
                st.session_state.total_correct_answers += score
                
                # Add to history
                st.session_state.quiz_history.append({
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'quiz_index': st.session_state.current_quiz_index,
                    'score': score,
                    'total': total,
                    'percentage': percentage
                })
                
                if percentage >= 80:
                    emoji = "🏆"
                    message = "Excellent!"
                elif percentage >= 60:
                    emoji = "👍"
                    message = "Good job!"
                else:
                    emoji = "📚"
                    message = "Keep studying!"
                
                st.markdown(f"""
                <div class='score-card'>
                    <h1>{emoji}</h1>
                    <h2>{message}</h2>
                    <h1 style='font-size: 3rem;'>{score}/{total}</h1>
                    <h3>{percentage:.1f}%</h3>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔄 Retake", use_container_width=True):
                        st.session_state.user_answers = {}
                        st.session_state.show_results = False
                        st.rerun()
                
                with col2:
                    if st.button("📚 My Quizzes", key="results_lib", use_container_width=True):
                        st.session_state.page = "library"
                        st.session_state.show_results = False
                        st.rerun()
                
                with col3:
                    if st.button("🏠 Home", key="results_home", use_container_width=True):
                        st.session_state.page = "main"
                        st.session_state.show_results = False
                        st.rerun()
# -------------------------
# HISTORY PAGE
# -------------------------
elif st.session_state.page == "history":
    st.title("📊 Quiz History")
    if not st.session_state.quiz_history:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.info("📝 No quiz history yet. Complete a quiz to see your progress!")
        if st.button("🏠 Go to Home", key="history_home", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{len(st.session_state.quiz_history)}</div>
                <div class='stats-label'>Total Attempts</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            avg = sum(h["score"] for h in st.session_state.quiz_history) / len(st.session_state.quiz_history)
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{avg:.1f}%</div>
                <div class='stats-label'>Average Score</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            best = max(h["score"] for h in st.session_state.quiz_history)
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{best:.1f}%</div>
                <div class='stats-label'>Best Score</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("### Recent Attempts")
        for i, rec in enumerate(reversed(st.session_state.quiz_history)):
            idx = len(st.session_state.quiz_history) - i
            with st.expander(f"Attempt {idx} - {rec['date']} - Score: {rec['score']:.1f}%"):
                st.markdown(f"**Quiz:** Paragraph {rec.get('quiz_index', 'Unknown') + 1}")
                st.markdown(f"**Score:** {rec['correct']}/{rec['total']} ({rec['score']:.1f}%)")
                st.progress(rec['score'] / 100)
        if st.button("🗑️ Clear History", key="clear_history", use_container_width=True):
            st.session_state.quiz_history = []
            st.success("History cleared!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)



