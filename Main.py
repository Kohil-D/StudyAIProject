import streamlit as st
import requests
import json
import re
import random
from datetime import datetime

# -------------------------
# API Configuration
# -------------------------

# IMPORTANT: Replace this with your actual OpenRouter API key
API_KEY = "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"
    
# OpenRouter API endpoint (corrected)
URL = "https://api.openai.com/v1/chat/completions"

# -------------------------
# Backend: Quiz Generator
# -------------------------
def generate_quiz(text, num_questions=5):
    """Generate quiz questions from text using OpenRouter API"""
    if not text or not text.strip():
        return None, "Please provide text to generate questions from."
    
    if not API_KEY:
        return None, "API key is required."
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/study-smart",  # Optional but recommended
        "X-Title": "Study Smart Quiz Generator"  # Optional but recommended
    }

    prompt = f"""
    Generate exactly {num_questions} multiple-choice questions from the text below.
    Return ONLY valid JSON in this exact format (no markdown, no extra text):

    {{
      "quiz": [
        {{
          "question": "Question text here",
          "options": ["a) First option", "b) Second option", "c) Third option", "d) Fourth option"],
          "answer": "b) Second option",
          "explanation": "Brief explanation of why this is correct"
        }}
      ]
    }}

    Rules:
    - Create clear, unambiguous questions
    - Ensure only one correct answer per question
    - Include brief explanations for correct answers
    - Base all questions strictly on the provided text
    - Make distractors plausible but incorrect

    Text:
    {text}
    """

    data = {
        "model": "openai/gpt-4o-mini",  # OpenRouter model format
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 2000
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", "")
            except:
                pass
            
            if response.status_code == 401:
                return None, f"Invalid API key. Please check your OpenAI API key. {error_detail}"
            elif response.status_code == 402:
                return None, "Insufficient credits. Please add credits to your OpenRouter account."
            elif response.status_code == 429:
                return None, "Rate limit exceeded. Please try again in a moment."
            else:
                return None, f"API Error {response.status_code}: {error_detail or response.text}"

        result = response.json()["choices"][0]["message"]["content"]
        
        # Clean markdown formatting if present
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        result = result.strip()

        try:
            quiz_data = json.loads(result)
        except json.JSONDecodeError:
            # Try to extract JSON if wrapped in text
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                try:
                    quiz_data = json.loads(match.group())
                except:
                    return None, "Failed to parse quiz response."
            else:
                return None, "Failed to parse quiz response."

        quiz_questions = quiz_data.get("quiz", [])
        
        if not quiz_questions:
            return None, "No questions were generated. Try with more text."
        
        # Shuffle options while preserving correct answer
        for q in quiz_questions:
            if "options" in q and "answer" in q and "question" in q:
                correct = q["answer"]
                random.shuffle(q["options"])
                q["answer"] = correct
            else:
                return None, "Invalid question format received."

        return quiz_questions, None
        
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

# -------------------------
# Initialize Session State
# -------------------------
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "page": "main",
        "paragraphs": [],
        "quiz": [],
        "user_answers": {},
        "quiz_ready": False,
        "show_results": False,
        "quiz_history": [],
        "current_paragraph": "",
        "dark_mode": True,
        "num_questions": 5
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="🍰 Study Smart",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# Dynamic Theme System
# -------------------------
def get_colors():
    """Get color scheme based on dark/light mode"""
    if st.session_state.dark_mode:
        return {
            'bg_primary': '#0f172a',
            'bg_secondary': '#1e293b',
            'bg_card': '#1e293b',
            'bg_card_hover': '#334155',
            'text_primary': '#f1f5f9',
            'text_secondary': '#cbd5e1',
            'text_tertiary': '#94a3b8',
            'accent_primary': '#8b5cf6',
            'accent_secondary': '#a78bfa',
            'border_color': '#334155',
            'shadow': 'rgba(0, 0, 0, 0.5)',
            'success_bg': '#064e3b',
            'success_text': '#6ee7b7',
            'error_bg': '#7f1d1d',
            'error_text': '#fca5a5',
            'warning_bg': '#78350f',
            'warning_text': '#fcd34d',
            'info_bg': '#1e3a8a',
            'info_text': '#93c5fd'
        }
    else:
        return {
            'bg_primary': '#f1f5f9',
            'bg_secondary': '#ffffff',
            'bg_card': '#ffffff',
            'bg_card_hover': '#f8fafc',
            'text_primary': '#0f172a',
            'text_secondary': '#1e293b',
            'text_tertiary': '#475569',
            'accent_primary': '#7c3aed',
            'accent_secondary': '#6d28d9',
            'border_color': '#cbd5e1',
            'shadow': 'rgba(0, 0, 0, 0.15)',
            'success_bg': '#dcfce7',
            'success_text': '#14532d',
            'error_bg': '#fee2e2',
            'error_text': '#7f1d1d',
            'warning_bg': '#fef3c7',
            'warning_text': '#78350f',
            'info_bg': '#dbeafe',
            'info_text': '#1e3a8a'
        }

colors = get_colors()

# -------------------------
# CSS Styling
# -------------------------
st.markdown(f"""
<style>
    /* Base styling */
    .stApp {{
        background: {colors['bg_primary']};
        color: {colors['text_primary']};
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Force text colors everywhere */
    * {{
        color: {colors['text_primary']};
    }}
    
    /* Card styling */
    .card {{
        background: {colors['bg_card']};
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid {colors['border_color']};
        box-shadow: 0 4px 12px {colors['shadow']};
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }}
    
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px {colors['shadow']};
    }}
    
    /* Question boxes */
    .question-box {{
        background: {colors['bg_card']};
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid {colors['accent_primary']};
        border: 1px solid {colors['border_color']};
        margin-bottom: 1.5rem;
        color: {colors['text_primary']} !important;
    }}
    
    .question-box * {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Stats box */
    .stats-box {{
        background: {colors['bg_card']};
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid {colors['accent_primary']};
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px {colors['shadow']};
    }}
    
    .stats-number {{
        font-size: 2rem;
        font-weight: bold;
        color: {colors['accent_primary']} !important;
    }}
    
    .stats-label {{
        font-size: 0.9rem;
        color: {colors['text_primary']} !important;
        font-weight: 600;
    }}
    
    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {colors['accent_primary']} 0%, {colors['accent_secondary']} 100%) !important;
        color: white !important;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
        width: 100%;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
    }}
    
    .stButton > button p {{
        color: white !important;
    }}
    
    /* Progress bar */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {colors['accent_primary']} 0%, {colors['accent_secondary']} 100%);
    }}
    
    /* Radio buttons */
    .stRadio > div {{
        gap: 0.5rem;
    }}
    
    .stRadio > div > label {{
        background: {colors['bg_secondary']} !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        border: 2px solid {colors['border_color']} !important;
        margin-bottom: 0.5rem !important;
        color: {colors['text_primary']} !important;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex !important;
        align-items: center !important;
    }}
    
    .stRadio > div > label:hover {{
        border-color: {colors['accent_primary']} !important;
        background: {colors['bg_card_hover']} !important;
        transform: translateX(4px);
    }}
    
    .stRadio > div > label > div {{
        color: {colors['text_primary']} !important;
    }}
    
    .stRadio > div > label span {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Text areas and inputs */
    .stTextArea > div > div > textarea,
    .stTextInput > div > div > input {{
        background: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        border: 2px solid {colors['border_color']} !important;
        border-radius: 8px;
    }}
    
    .stTextArea > div > div > textarea::placeholder,
    .stTextInput > div > div > input::placeholder {{
        color: {colors['text_tertiary']} !important;
    }}
    
    .stTextArea label,
    .stTextInput label {{
        color: {colors['text_primary']} !important;
        font-weight: 600 !important;
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {colors['bg_secondary']} !important;
        border-right: 2px solid {colors['border_color']};
    }}
    
    section[data-testid="stSidebar"] * {{
        color: {colors['text_primary']} !important;
    }}
    
    section[data-testid="stSidebar"] .stMarkdown {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: {colors['text_primary']} !important;
        font-weight: 700 !important;
    }}
    
    /* Paragraphs and text */
    p, span, div {{
        color: {colors['text_primary']} !important;
    }}
    
    label {{
        color: {colors['text_primary']} !important;
        font-weight: 500 !important;
    }}
    
    /* Markdown content */
    .stMarkdown {{
        color: {colors['text_primary']} !important;
    }}
    
    .stMarkdown * {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background: {colors['bg_card']} !important;
        color: {colors['text_primary']} !important;
        border: 2px solid {colors['border_color']} !important;
        border-radius: 8px;
        font-weight: 600 !important;
    }}
    
    .streamlit-expanderHeader:hover {{
        background: {colors['bg_card_hover']} !important;
    }}
    
    .streamlit-expanderContent {{
        background: {colors['bg_card']} !important;
        border: 2px solid {colors['border_color']} !important;
        border-top: none !important;
        color: {colors['text_primary']} !important;
    }}
    
    details summary {{
        color: {colors['text_primary']} !important;
    }}
    
    /* Slider */
    .stSlider label {{
        color: {colors['text_primary']} !important;
        font-weight: 600 !important;
    }}
    
    .stSlider [data-baseweb="slider"] {{
        background: {colors['bg_secondary']} !important;
    }}
    
    /* Success/Error/Warning/Info */
    .stSuccess {{
        background: {colors['success_bg']} !important;
        color: {colors['success_text']} !important;
        border-radius: 8px;
        padding: 0.75rem;
        border: 2px solid {colors['success_text']};
    }}
    
    .stSuccess * {{
        color: {colors['success_text']} !important;
    }}
    
    .stError {{
        background: {colors['error_bg']} !important;
        color: {colors['error_text']} !important;
        border-radius: 8px;
        padding: 0.75rem;
        border: 2px solid {colors['error_text']};
    }}
    
    .stError * {{
        color: {colors['error_text']} !important;
    }}
    
    .stWarning {{
        background: {colors['warning_bg']} !important;
        color: {colors['warning_text']} !important;
        border-radius: 8px;
        padding: 0.75rem;
        border: 2px solid {colors['warning_text']};
    }}
    
    .stWarning * {{
        color: {colors['warning_text']} !important;
    }}
    
    .stInfo {{
        background: {colors['info_bg']} !important;
        color: {colors['info_text']} !important;
        border-radius: 8px;
        padding: 0.75rem;
        border: 2px solid {colors['info_text']};
    }}
    
    .stInfo * {{
        color: {colors['info_text']} !important;
    }}
    
    /* Score card */
    .score-card {{
        background: linear-gradient(135deg, {colors['accent_primary']} 0%, {colors['accent_secondary']} 100%);
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        color: white;
        margin: 2rem 0;
        box-shadow: 0 8px 24px {colors['shadow']};
    }}
    
    .score-card * {{
        color: white !important;
    }}
    
    /* Strong emphasis */
    strong, b {{
        color: {colors['text_primary']} !important;
        font-weight: 700 !important;
    }}
    
    /* Links */
    a {{
        color: {colors['accent_primary']} !important;
    }}
    
    /* Code blocks */
    code {{
        background: {colors['bg_secondary']} !important;
        color: {colors['text_primary']} !important;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
    }}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Sidebar Navigation
# -------------------------
with st.sidebar:
    st.title("📌 Navigation")
    
    # Theme toggle
    if st.button("🌙 Dark" if not st.session_state.dark_mode else "☀️ Light", key="theme_btn", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    
    st.markdown("---")
    
    # Settings
    st.subheader("⚙️ Settings")
    num_q = st.slider("Questions per quiz", 1, 20, st.session_state.num_questions, key="num_q_slider")
    st.session_state.num_questions = num_q
    
    st.markdown("---")
    
    # Navigation buttons
    if st.button("🏠 Home", key="nav_home", use_container_width=True):
        st.session_state.page = "main"
        st.session_state.show_results = False
        st.rerun()
    
    if st.session_state.quiz_ready:
        if st.button("🎮 Go to Quiz", key="nav_quiz", use_container_width=True):
            st.session_state.page = "quiz"
            st.rerun()
    
    if st.session_state.quiz_history:
        if st.button("📊 View History", key="nav_history", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    
    st.markdown("---")
    
    # Stats
    if st.session_state.quiz_history:
        avg_score = sum(h["score"] for h in st.session_state.quiz_history) / len(st.session_state.quiz_history)
        st.markdown(f"""
        <div class='stats-box'>
            <div class='stats-number'>{len(st.session_state.quiz_history)}</div>
            <div class='stats-label'>Quizzes Completed</div>
        </div>
        <div class='stats-box'>
            <div class='stats-number'>{avg_score:.1f}%</div>
            <div class='stats-label'>Average Score</div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------
# MAIN PAGE
# -------------------------
if st.session_state.page == "main":
    st.title("🍰 Study Smart")
    st.markdown("Play Quizzes from a Paragraph")
    
    # Input section
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    user_input = st.text_area(
        "📥 Paste Your Study Material",
        height=200,
        placeholder="Enter your paragraph, notes, or study material here...",
        key="main_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Paragraph", key="add_para", use_container_width=True):
            if user_input and user_input.strip():
                st.session_state.paragraphs.append(user_input.strip())
                st.success("✅ Paragraph added!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter some text first!")
    
    with col2:
        if st.session_state.paragraphs:
            if st.button("🗑️ Clear All", key="clear_all", use_container_width=True):
                st.session_state.paragraphs = []
                st.session_state.quiz = []
                st.session_state.quiz_ready = False
                st.success("🗑️ All cleared!")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Saved paragraphs
    if st.session_state.paragraphs:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(f"📚 Saved Paragraphs ({len(st.session_state.paragraphs)})")
        
        for i, para in enumerate(st.session_state.paragraphs):
            with st.expander(f"Paragraph {i+1} ({len(para)} characters)", expanded=(i == len(st.session_state.paragraphs) - 1)):
                st.markdown(f"{para[:300]}{'...' if len(para) > 300 else ''}")
                
                if st.button(f"⚡ Generate Quiz", key=f"gen_quiz_{i}", use_container_width=True):
                    with st.spinner("🧠 Generating quiz questions..."):
                        quiz, error = generate_quiz(para, st.session_state.num_questions)
                    
                    if error:
                        st.error(f"❌ {error}")
                    elif quiz:
                        st.session_state.quiz = quiz
                        st.session_state.quiz_ready = True
                        st.session_state.user_answers = {}
                        st.session_state.show_results = False
                        st.session_state.page = "quiz"
                        st.success(f"✅ Generated {len(quiz)} questions!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to generate quiz.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# QUIZ PAGE
# -------------------------
elif st.session_state.page == "quiz":
    if not st.session_state.quiz:
        st.warning("⚠️ No quiz available. Please go back and generate a quiz.")
        if st.button("🏠 Go to Home", key="quiz_home_btn"):
            st.session_state.page = "main"
            st.rerun()
    else:
        quiz = st.session_state.quiz
        
        col_main, col_side = st.columns([3, 1])
        
        with col_side:
            # Progress
            answered = len([k for k in st.session_state.user_answers.keys() if st.session_state.user_answers[k] is not None])
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{answered}/{len(quiz)}</div>
                <div class='stats-label'>Answered</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(answered / len(quiz))
            
            # Submit button
            if st.button("✅ Submit Quiz", key="submit_btn", use_container_width=True, disabled=(answered < len(quiz))):
                st.session_state.show_results = True
                st.rerun()
            
            if st.button("🔄 Reset", key="reset_btn", use_container_width=True):
                st.session_state.user_answers = {}
                st.session_state.show_results = False
                st.rerun()
            
            if st.button("🏠 Home", key="quiz_home_sidebar", use_container_width=True):
                st.session_state.page = "main"
                st.session_state.show_results = False
                st.rerun()
        
        with col_main:
            if not st.session_state.show_results:
                # Quiz questions
                st.title("🎮 Quiz Time!")
                
                for i, q in enumerate(quiz):
                    st.markdown(f"<div class='question-box'>", unsafe_allow_html=True)
                    st.markdown(f"**Question {i+1}**")
                    st.markdown(f"### {q['question']}")
                    
                    current = st.session_state.user_answers.get(i)
                    
                    answer = st.radio(
                        "Select your answer:",
                        options=q["options"],
                        index=None if current is None else (q["options"].index(current) if current in q["options"] else None),
                        key=f"radio_{i}",
                        label_visibility="collapsed"
                    )
                    
                    st.session_state.user_answers[i] = answer
                    st.markdown("</div>", unsafe_allow_html=True)
            
            else:
                # Results
                st.title("📊 Quiz Results")
                
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
                    
                    if "explanation" in q and q["explanation"]:
                        with st.expander("💡 Explanation"):
                            st.info(q["explanation"])
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # Score card
                percentage = (score / total) * 100
                
                if percentage >= 80:
                    emoji = "🏆"
                    message = "Excellent work!"
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
                    <h3>{percentage:.1f}% Score</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Save to history
                if not any(h.get("date") == datetime.now().strftime("%Y-%m-%d %H:%M") for h in st.session_state.quiz_history):
                    st.session_state.quiz_history.append({
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "score": percentage,
                        "correct": score,
                        "total": total
                    })
                
                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Try Again", key="try_again", use_container_width=True):
                        st.session_state.user_answers = {}
                        st.session_state.show_results = False
                        st.rerun()
                
                with col2:
                    if st.button("🏠 Back Home", key="results_home", use_container_width=True):
                        st.session_state.page = "main"
                        st.session_state.quiz_ready = False
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
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class='stats-box'>
                <div class='stats-number'>{len(st.session_state.quiz_history)}</div>
                <div class='stats-label'>Total Quizzes</div>
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
        
        st.markdown("### Recent Quizzes")
        
        for i, rec in enumerate(reversed(st.session_state.quiz_history)):
            idx = len(st.session_state.quiz_history) - i
            with st.expander(f"Quiz {idx} - {rec['date']} - Score: {rec['score']:.1f}%"):
                st.markdown(f"**Score:** {rec['correct']}/{rec['total']} ({rec['score']:.1f}%)")
                st.progress(rec['score'] / 100)
        
        if st.button("🗑️ Clear History", key="clear_history", use_container_width=True):
            st.session_state.quiz_history = []
            st.success("History cleared!")
            st.rerun()
        

        st.markdown("</div>", unsafe_allow_html=True)





