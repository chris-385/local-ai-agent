import streamlit as st
import fitness_core as core
from fitness_ui import profile_label, request_dialog, reset_profile_session, show_requested_dialog

st.set_page_config(
    page_title='FitCoach AI',
    page_icon='assets/fitcoach-ai-logo.svg',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.logo('assets/fitcoach-ai-logo.svg', size='large')


@st.cache_data(ttl=15, max_entries=1)
def available_models():
    try:
        return core.models()
    except Exception:
        return []


@st.cache_data(ttl=15, max_entries=1)
def available_vision_models():
    try:
        return core.vision_models()
    except Exception:
        return []


st.session_state.setdefault('fitness_chat', [])
st.session_state.setdefault('coach_actions', {})

page = st.navigation([
    st.Page('fitness_pages/overview.py', title='Home', icon=':material/home:', default=True),
    st.Page('fitness_pages/training.py', title='Training', icon=':material/fitness_center:'),
    st.Page('fitness_pages/nutrition.py', title='Nutrition', icon=':material/restaurant:'),
    st.Page('fitness_pages/coach.py', title='AI Coach', icon=':material/auto_awesome:'),
], position='sidebar')

with st.sidebar:
    profiles = core.profiles()
    if profiles:
        # A stale or missing selection (e.g. after deleting a profile) falls back to the first one.
        pending = st.session_state.pop('pending_profile_id', None)
        if pending in profiles:
            st.session_state['profile_id'] = pending
        if st.session_state.get('profile_id') not in profiles:
            st.session_state['profile_id'] = next(iter(profiles))
        st.selectbox(
            'Profile', list(profiles), key='profile_id',
            format_func=lambda pid: profile_label(profiles[pid]),
            on_change=reset_profile_session,
        )
        with st.container(horizontal=True):
            st.button('New', icon=':material/person_add:', key='new_profile_button', width='stretch', on_click=request_dialog, args=('new',))
            st.button('Edit', icon=':material/edit:', key='edit_profile_button', width='stretch', on_click=request_dialog, args=('edit',))
    st.space('stretch')
    with st.expander('AI settings', icon=':material/tune:'):
        choices = available_models()
        st.session_state['fitness_text_model'] = st.selectbox('Language model', choices, key='text_model_choice') if choices else st.text_input('Language model', 'llama3.2:3b', key='text_model_fallback')
        vision_choices = available_vision_models()
        st.session_state['fitness_vision_available'] = bool(vision_choices)
        st.session_state['fitness_vision_model'] = st.selectbox('Vision model (photos)', vision_choices, key='vision_model_choice') if vision_choices else st.text_input('Vision model (photos)', core.RECOMMENDED_VISION_MODEL, key='vision_model_fallback')
        if not choices:
            st.caption('Ollama is currently unavailable. Tracking still works.')
    st.caption(':material/lock: Your data stays on this computer.')

show_requested_dialog()
page.run()
