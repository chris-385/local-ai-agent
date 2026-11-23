from datetime import date, timedelta

import pandas as pd
import streamlit as st

from fitness_ui import GOAL_NAMES, add, data, flash, manage_entries, notify, profile, profile_form

flash()
p = profile()

if not p:
    st.title('Welcome to FitCoach', icon=':material/waving_hand:', anchor=False)
    st.caption('Tell us a little about yourself – it takes less than a minute. You can change everything later.')
    profile_form(key='first_profile')
    st.stop()

goal = GOAL_NAMES.get(p.get('goal'), p.get('goal'))
st.title(f"Hi, {p['name']}" if p.get('name') else 'Home', icon=':material/home:', anchor=False)
st.caption(f"{date.today():%A, %d %B} · Goal: **{goal}**")

weights = data('weight')
meals = data('meal')
workouts = data('workout')
targets = data('nutrition_targets')
target = targets[-1] if targets else {}
today = date.today().isoformat()
week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

current_weight = weights[-1]['kg'] if weights else p.get('weight')
kcal_today = sum(m['kcal'] for m in meals if m['day'] == today)
this_week = [w for w in workouts if week_start <= w['day'] <= today]

# ---------- Today at a glance ----------
with st.container(horizontal=True):
    weight_trend = [w['kg'] for w in weights[-14:]]
    st.metric(
        'Weight', f'{current_weight:.1f} kg' if current_weight else '–',
        f"{current_weight - weights[0]['kg']:+.1f} kg" if len(weights) > 1 else None,
        delta_color='inverse' if goal == 'Lose weight' else 'normal' if goal == 'Build muscle' else 'off',
        delta_description='since start', border=True,
        chart_data=weight_trend if len(weight_trend) > 1 else None,
    )
    if p.get('target_weight') and current_weight:
        st.metric('To target', f"{abs(current_weight - p['target_weight']):.1f} kg", delta_description=f"Target {p['target_weight']:.1f} kg", border=True)
    st.metric(
        'Calories today', f'{kcal_today:.0f} kcal',
        f"{target['kcal'] - kcal_today:.0f} kcal left" if target.get('kcal') else None,
        delta_color='off', delta_arrow='off', border=True,
    )
    st.metric(
        'Workouts this week', f"{len(this_week)} / {p.get('days', 3)}",
        f"{sum(w['minutes'] for w in this_week)} min" if this_week else None,
        delta_color='off', delta_arrow='off', border=True,
    )

# ---------- Quick actions ----------
with st.container(horizontal=True):
    with st.popover('Log weight', icon=':material/monitor_weight:', type='primary'):
        with st.form('weight', border=False):
            day = st.date_input('Date', date.today(), max_value=date.today())
            kg = st.number_input('Weight (kg)', 35., 300., float(current_weight or 75.), step=0.1)
            if st.form_submit_button('Save weight', icon=':material/check:', type='primary', width='stretch'):
                add('weight', day, {'kg': kg})
                notify('Weight saved.')
    st.page_link('fitness_pages/nutrition.py', label='Log a meal', icon=':material/restaurant:')
    st.page_link('fitness_pages/training.py', label='Log a workout', icon=':material/fitness_center:')
    st.page_link('fitness_pages/coach.py', label='Ask the coach', icon=':material/auto_awesome:')

# ---------- Progress and plans ----------
progress_col, plans_col = st.columns([1.7, 1], gap='medium')

with progress_col.container(border=True, height='stretch'):
    st.subheader('Weight progress', icon=':material/query_stats:', anchor=False)
    if weights:
        df = pd.DataFrame(weights).groupby('day', as_index=False)['kg'].last().rename(columns={'kg': 'Weight'})
        if p.get('target_weight'):
            df['Target'] = p['target_weight']
        st.line_chart(df, x='day', y=[c for c in ('Weight', 'Target') if c in df], x_label='', y_label='kg', height=260)
        manage_entries('weight', 'Manage measurements')
    else:
        st.info('Use **Log weight** above to start tracking your progress.', icon=':material/monitoring:')

with plans_col.container(border=True, height='stretch'):
    st.subheader('Your plans', icon=':material/event_note:', anchor=False)
    for kind, label, path, icon in [
        ('training_plan', 'Training plan', 'fitness_pages/training.py', ':material/fitness_center:'),
        ('nutrition_plan', 'Meal plan', 'fitness_pages/nutrition.py', ':material/restaurant:'),
    ]:
        plans = data(kind)
        with st.container(horizontal=True, vertical_alignment='center'):
            st.page_link(path, label=label, icon=icon)
            st.space('stretch')
            if plans:
                st.badge(f"Active since {plans[-1]['day']}", color='green')
            else:
                st.badge('Not created', color='gray')
    st.caption('Create plans in Training and Nutrition or let the AI Coach suggest one.')

st.caption(':material/health_and_safety: For adults. Review AI suggestions and photo estimates before using them.')
