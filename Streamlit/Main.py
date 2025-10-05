import streamlit as st
import requests
import json
import re
import random
from datetime import datetime

# -------------------------
# CONFIGURATION - PASTE YOUR OPENAI API KEY HERE
# -------------------------
API_KEY = "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"  # Get it from: https://platform.openai.com/api-keys

# OpenAI API endpoint
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# -------------------------
# Backend: OpenAI Quiz Generator
# -------------------------
def generate_quiz(text, num_questions=5):
    """Generate quiz questions using OpenAI API"""
    if not text or not text.strip():
        return None, "Please provide text to generate questions from."
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""Create exactly {num_questions} multiple-choice questions from this text.

Return ONLY valid JSON in this exact format:

{{
  "quiz": [
    {{
      "question": "Question text here?",
      "options": ["a) First option", "b) Second option", "c) Third option", "d) Fourth option"],
      "answer": "b) Second option",
      "explanation": "Brief explanation"
    }}
  ]
}}

Text: {text[:1500]}"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 1500
    }

    try:
        response = requests.post(OPENAI_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            if response.status_code == 401:
                return None, "Invalid API key. Check your OpenAI API key!"
            elif response.status_code == 429:
                return None, "Rate limit exceeded. Wait 60 seconds and try again."
            else:
                return None, f"API Error {response.status_code}"

        result = response.json()["choices"][0]["message"]["content"]
        
        # Clean markdown
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'^```\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        result = result.strip()

        try:
            quiz_data = json.loads(result)
        except:
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                quiz_data = json.loads(match.group())
            else:
                return None, "Failed to parse response."

        quiz_questions = quiz_data.get("quiz", [])
        
        if not quiz_questions:
            return None, "No questions generated."
        
        # Shuffle options
        for q in quiz_questions:
            correct = q["answer"]
            random.shuffle(q["options"])
            q["answer"] = correct

        return quiz_questions, None
        
    except Exception as e:
        return None, f"Error: {str(e)}"

# -------------------------
# Initialize Session State
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "main"
if "paragraphs" not in st.session_state:
    st.session_state.paragraphs = []
if "saved_quizzes" not in st.session_state:
    st.session_state.saved_quizzes = {}
if "current_quiz_index" not in st.session_state:
    st.session_state.current_quiz_index = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "num_questions" not in st.session_state:
    st.session_state.num_questions = 5
if "api_calls" not in st.session_state:
    st.session_state.api_calls = 0

# -------------------------
# Page Configuration
# -------------------------
st.set_page_config(
    page_title="📘 Quiz Generator",
    page_icon="📘",
    layout="wide"
)

# -------------------------
# CSS Styling
# -------------------------
st.markdown("""
<style>
    .stApp {
        background: #0f172a;
        color: #f1f5f9;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
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
    
    .openai-badge {
        background: linear-gradient(135deg, #10a37f 0%, #1a7f64 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.title("📌 Menu")
    
    # OpenAI Badge
    st.markdown('<div class="openai-badge">🤖 Powered by OpenAI</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.subheader("⚙️ Settings")
    num_q = st.slider("Questions per quiz", 3, 10, st.session_state.num_questions)
    st.session_state.num_questions = num_q
    
    st.markdown("---")
    
    st.subheader("📊 Stats")
    st.markdown(f"""
    <div class='stats-box'>
        <div class='stats-number'>{st.session_state.api_calls}</div>
        <div class='stats-label'>API Calls Made</div>
    </div>
    <div class='stats-box'>
        <div class='stats-number'>{len(st.session_state.saved_quizzes)}</div>
        <div class='stats-label'>Quizzes Generated</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning("⚠️ **Free tier:** ~3 requests/min\n💡 Add payment for higher limits")
    
    st.markdown("---")
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "main"
        st.session_state.show_results = False
        st.rerun()
    
    if st.session_state.saved_quizzes:
        if st.button("📚 My Quizzes", use_container_width=True):
            st.session_state.page = "library"
            st.rerun()
# -------------------------
# MAIN PAGE
# -------------------------
if st.session_state.page == "main":
    st.title("📘 Quiz Generator")
    st.markdown("HIGHLY ACCURATE)")
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    user_input = st.text_area(
        "📥 Paste Your Study Material",
        height=200,
        placeholder="Enter your text here...",
        max_chars=2000
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Paragraph", use_container_width=True):
            if user_input and user_input.strip():
                st.session_state.paragraphs.append(user_input.strip())
                st.success("✅ Paragraph added!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter some text first!")
    
    with col2:
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
                    
                    col1, col2 = st.columns(2)
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
                
                else:
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
        
        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# QUIZ LIBRARY PAGE
# -------------------------
elif st.session_state.page == "library":
    st.title("📚 My Quiz Library")
    
    if not st.session_state.saved_quizzes:
        st.info("No quizzes yet. Go to Home and create one!")
        if st.button("🏠 Go Home"):
            st.session_state.page = "main"
            st.rerun()
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        for idx, quiz in st.session_state.saved_quizzes.items():
            para_preview = st.session_state.paragraphs[idx][:100] + "..."
            
            with st.expander(f"📖 Quiz {idx+1} - {len(quiz)} questions"):
                st.markdown(f"**Source:** {para_preview}")
                
                if st.button(f"▶️ Take This Quiz", key=f"lib_{idx}", use_container_width=True):
                    st.session_state.current_quiz_index = idx
                    st.session_state.user_answers = {}
                    st.session_state.show_results = False
                    st.session_state.page = "quiz"
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

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
            answered = len([k for k in st.session_state.user_answers.keys() if st.session_state.user_answers[k] is not None])
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
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Retake", use_container_width=True):
                        st.session_state.user_answers = {}
                        st.session_state.show_results = False
                        st.rerun()
                
                with col2:
                    if st.button("🏠 Home", key="results_home", use_container_width=True):
                        st.session_state.page = "main"
                        st.session_state.show_results = False
                        st.rerun()
