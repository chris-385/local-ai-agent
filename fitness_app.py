import streamlit as st
from fitness_core import models

st.set_page_config(
    page_title='Form · Fitness & Health',
    page_icon=':material/fitness_center:',
    layout='wide',
    initial_sidebar_state='expanded',
)

@st.cache_data(ttl=15, max_entries=1)
def available_models():
    try:
        return models()
    except Exception:
        return []

st.session_state.setdefault('fitness_chat', [])
st.session_state.setdefault('coach_actions', {})
with st.sidebar:
    st.title('Form', anchor=False)
    st.caption('Your personal fitness companion')
    with st.expander('AI settings', icon=':material/tune:'):
        choices = available_models()
        st.session_state['fitness_text_model'] = st.selectbox('Language model', choices, key='text_model_choice') if choices else st.text_input('Language model', 'llama3.2:3b', key='text_model_fallback')
        st.session_state['fitness_vision_model'] = st.text_input('Vision model', 'llama3.2-vision:11b', key='vision_model_choice')
        if not choices:
            st.caption('Ollama is currently unavailable. Tracking still works.')
    st.caption(':material/lock: Your data stays local on this computer.')

page = st.navigation([
    st.Page('fitness_pages/overview.py', title='Overview', icon=':material/home:', default=True),
    st.Page('fitness_pages/training.py', title='Training', icon=':material/fitness_center:'),
    st.Page('fitness_pages/nutrition.py', title='Nutrition', icon=':material/restaurant:'),
    st.Page('fitness_pages/coach.py', title='Coach', icon=':material/forum:'),
], position='sidebar')
page.run()
