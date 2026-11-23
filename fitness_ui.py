"""Shared UI helpers: active profile, profile form, plans, and entry management."""
import json
from datetime import date
import uuid
import streamlit as st
import fitness_core as core

TRAINING_PROMPT = ('Create a personalized weekly training plan. Consider the training days, time, equipment, experience, and limitations in the profile. '
    'For each session, include exercises, sets, reps, rest periods, and alternatives. Add a warm-up, rest days, and cautious progression. Do not prescribe rehabilitation.')
NUTRITION_PROMPT = ('Create a personalized 7-day meal plan with portions in grams, estimated calories, protein, carbohydrates, and fat for each meal and daily totals. '
    'Include a shopping list and alternatives. Strictly follow allergies, dietary preferences, and self-defined nutrition targets. '
    'Explain assumptions, do not invent profile data, and avoid aggressive deficits or therapeutic diets.')

GOALS = ['Build muscle', 'Improve fitness', 'Lose weight']
LEVELS = ['Beginner', 'Advanced']
# Profiles saved by the original German version.
GOAL_NAMES = {'Muskelaufbau': 'Build muscle', 'Fitter werden': 'Improve fitness', 'Gewicht reduzieren': 'Lose weight'}
LEVEL_NAMES = {'Anfänger': 'Beginner', 'Fortgeschritten': 'Advanced'}


# ---------- Active profile and profile-scoped storage ----------

def owner():
    """Identifier of the profile whose data is currently shown."""
    return st.session_state.get('pending_profile_id') or st.session_state.get('profile_id') or core.DEFAULT_OWNER


def data(kind):
    return core.records(kind, owner())


def add(kind, day, payload):
    return core.save(kind, day, payload, owner())


def profile():
    return core.profiles().get(owner())


def profile_label(p):
    return (p or {}).get('name') or 'My profile'


def switch_profile(profile_id):
    """Activate a profile and drop session state that belongs to the previous one.

    The sidebar selector applies the change on the next run, because a widget's
    value cannot be changed after it was drawn in the current run.
    """
    st.session_state['pending_profile_id'] = profile_id
    reset_profile_session()


def reset_profile_session():
    st.session_state['fitness_chat'] = []
    st.session_state['coach_actions'] = {}
    st.session_state.pop('meal_draft', None)


def ai_context(include_targets=True):
    """Profile plus the latest weight and targets, as sent to the AI."""
    context = dict(profile() or {})
    weights = data('weight')
    if weights:
        context['Current weight (kg)'] = weights[-1]['kg']
    targets = data('nutrition_targets')
    if include_targets and targets:
        context['Self-defined nutrition targets'] = {k: v for k, v in targets[-1].items() if k not in ('id', 'day')}
    return context


# ---------- Small UI building blocks ----------

def page_header(title, subtitle, icon):
    """Render a consistent, compact header on every page."""
    st.title(title, icon=icon, anchor=False)
    st.caption(subtitle)


def flash():
    message = st.session_state.pop('fitness_flash', None)
    if message:
        st.toast(message, icon=':material/check_circle:')


def notify(message):
    st.session_state['fitness_flash'] = message
    st.rerun()


def require_profile():
    """Stop the page with a friendly hint when no profile exists yet."""
    if profile():
        return
    with st.container(border=True):
        st.markdown('**Create your profile first** so FitCoach can personalize everything for you.')
        st.page_link('fitness_pages/overview.py', label='Go to Home', icon=':material/arrow_forward:')


def profile_form(existing=None, profile_id=None, key='profile'):
    """Profile form with the essentials up front and optional details tucked away."""
    d = existing or {}
    with st.form(key):
        name = st.text_input('Name', d.get('name', ''), placeholder='e.g. Alex')
        current_goal = GOAL_NAMES.get(d.get('goal'), d.get('goal') or 'Improve fitness')
        goal = st.segmented_control('Your goal', GOALS, default=current_goal if current_goal in GOALS else 'Improve fitness', width='stretch')
        body = st.columns(4)
        age = body[0].number_input('Age', 18, 90, int(d.get('age', 30)))
        height = body[1].number_input('Height (cm)', 120, 230, int(d.get('height', 175)))
        weight = body[2].number_input('Weight (kg)', 35., 300., float(d.get('weight', 75.)))
        target = body[3].number_input('Target weight (kg)', 35., 300., d.get('target_weight'), placeholder='Optional')
        training = st.columns(3)
        current_level = LEVEL_NAMES.get(d.get('level'), d.get('level') or 'Beginner')
        level = training[0].selectbox('Experience', LEVELS, index=LEVELS.index(current_level) if current_level in LEVELS else 0)
        days = training[1].number_input('Training days / week', 1, 6, int(d.get('days', 3)))
        minutes = training[2].number_input('Minutes / session', 20, 90, int(d.get('minutes', 45)), step=5)
        with st.expander('More details (optional)', icon=':material/tune:'):
            st.caption('Helps the AI Coach tailor plans to you.')
            goal_notes = st.text_area('What would you like to achieve?', d.get('goal_notes', ''), placeholder='e.g. train consistently and get stronger', height=80)
            more = st.columns(3)
            equipment = more[0].text_input('Equipment', d.get('equipment', 'Gym'))
            activity = more[1].text_input('Daily activity', d.get('activity', 'Mostly sedentary'))
            diet = more[2].text_input('Diet', d.get('diet', 'Omnivore'))
            allergies = st.text_input('Allergies and foods you avoid', d.get('allergies', ''))
            limitations = st.text_input('Injuries and limitations', d.get('limitations', ''))
        submitted = st.form_submit_button('Save profile', type='primary', icon=':material/save:', width='stretch')
    if submitted:
        if not name.strip():
            st.error('Please enter a name so you can find this profile again.')
            return
        target_id = profile_id or owner()
        core.save('profile', date.today(), dict(
            name=name.strip(), age=age, height=height, weight=weight, goal=goal or 'Improve fitness',
            target_weight=target, goal_notes=goal_notes, level=level, days=days, minutes=minutes,
            equipment=equipment, activity=activity, diet=diet, allergies=allergies, limitations=limitations,
        ), target_id)
        if target_id != owner():
            switch_profile(target_id)
        notify(f'Profile for {name.strip()} saved.')


@st.dialog('New profile', icon=':material/person_add:', width='large')
def new_profile_dialog():
    st.caption('Each profile has its own goals, plans, meals, and workouts.')
    profile_form(profile_id=uuid.uuid4().hex[:10], key='new_profile')


@st.dialog('Edit profile', icon=':material/edit:', width='large')
def edit_profile_dialog():
    profile_form(profile(), key='edit_profile')
    st.divider()
    st.markdown('**Delete profile**')
    st.caption('Removes this profile with all its plans, meals, workouts, and chats. This cannot be undone.')
    confirm = st.checkbox(f'Yes, delete {profile_label(profile())} and all its data', key='confirm_delete_profile')
    if st.button('Delete profile', icon=':material/delete:', disabled=not confirm, key='delete_profile'):
        delete_active_profile()
        notify('Profile deleted.')


def delete_active_profile():
    """Delete the active profile and its data, then switch to a remaining profile."""
    core.delete_owner(owner())
    remaining = list(core.profiles())
    if remaining:
        switch_profile(remaining[0])
    else:
        # No profile left: Home shows the onboarding form again.
        st.session_state.pop('pending_profile_id', None)
        st.session_state.pop('profile_id', None)
        reset_profile_session()


def request_dialog(name):
    """Open a dialog outside the sidebar; dialogs must not be called within st.sidebar."""
    st.session_state['open_dialog'] = name


def show_requested_dialog():
    name = st.session_state.pop('open_dialog', None)
    if name == 'new':
        new_profile_dialog()
    elif name == 'edit' and profile():
        edit_profile_dialog()


# ---------- Plans and entries ----------

def plan_panel(kind, instruction):
    p = profile()
    plan_name = 'training plan' if kind == 'training_plan' else 'meal plan'
    plans = data(kind)
    active = plans[-1] if plans else None
    if not p:
        require_profile()
        return
    with st.container(horizontal=True, vertical_alignment='center'):
        st.caption(f"Active since {active['day']}" if active else 'No active plan yet.')
        generate = st.button(
            f'Create new {plan_name}' if active else f'Create my {plan_name}', key='generate_' + kind,
            type='secondary' if active else 'primary', icon=':material/auto_awesome:', width='content',
        )
    if generate:
        try:
            with st.status('Creating your plan …', expanded=True) as status:
                content = st.write_stream(core.stream_coach(st.session_state['fitness_text_model'], ai_context(kind == 'nutrition_plan'), [], instruction, plan=True))
                status.update(label='Plan created', state='complete', expanded=False)
            if 'Response limit reached.' in content:
                st.warning('The draft is incomplete and was not saved. Ask the AI Coach for a shorter plan.')
            else:
                add(kind, date.today(), {'content': content, 'profile': p, 'source': 'generator'})
                notify('Your new plan is saved and active.')
        except Exception as exc:
            st.error(f'The plan could not be created: {exc}')
    if not active:
        st.info(f'Let FitCoach create a {plan_name} for you, or ask the AI Coach for one.', icon=':material/lightbulb:')
        return
    if active.get('profile') != p:
        st.caption(':material/info: Your profile changed since this plan was created – consider creating a new one.')
    with st.container(border=True):
        st.markdown(active['content'])
    with st.container(horizontal=True):
        st.download_button('Download', active['content'], file_name=kind + '.md', key='download_' + kind, icon=':material/download:', type='tertiary')
        if len(plans) > 1:
            with st.popover('Previous versions', icon=':material/history:', type='tertiary'):
                old = st.selectbox('Version', plans[:-1][::-1], format_func=lambda r: f"{r['day']} · #{r['id']}", key='history_' + kind)
                st.markdown(old['content'])


def manage_entries(kind, title):
    entries = data(kind)
    if entries:
        with st.expander(title, icon=':material/settings:'):
            selected = st.selectbox('Entry', entries[::-1], format_func=lambda r: f"{r['day']} · {r.get('name', str(r.get('kg', '')) + ' kg')}", key='manage_' + kind)
            with st.container(horizontal=True):
                if st.button('Delete entry', key='delete_' + kind, icon=':material/delete:'):
                    core.delete(selected['id'])
                    notify('Entry deleted.')
                st.download_button('Export all', json.dumps(entries, ensure_ascii=False, indent=2), file_name=kind + '.json', key='export_' + kind, icon=':material/download:', type='tertiary')
