from datetime import date

import pandas as pd
import streamlit as st

from fitness_core import records, save
from fitness_ui import flash, manage_entries, notify, page_header, profile


flash()
p = profile()
weights = records('weight')
current_weight = weights[-1]['kg'] if weights else (p.get('weight') if p else None)

goal_names = {'Muskelaufbau':'Build muscle','Fitter werden':'Improve fitness','Gewicht reduzieren':'Lose weight'}
level_names = {'Anfänger':'Beginner','Fortgeschritten':'Advanced'}
greeting = f"Welcome back, {p['name']}" if p and p.get('name') else 'Your overview'
page_header(greeting, 'Your goals and progress at a glance.', ':material/home:')

metrics = st.columns(4)
metrics[0].metric('Current weight', f'{current_weight:.1f} kg' if current_weight else '–', border=True)
metrics[1].metric('Goal', goal_names.get(p['goal'],p['goal']) if p else 'Not set', border=True)
metrics[2].metric(
    'Target weight',
    f"{p['target_weight']:.1f} kg" if p and p.get('target_weight') else 'Not set',
    border=True,
)
metrics[3].metric(
    'Change',
    f"{current_weight - weights[0]['kg']:+.1f} kg" if weights else 'No measurements yet',
    border=True,
)

profile_col, progress_col = st.columns([1, 1.35], gap='large')

with profile_col:
    with st.container(border=True, height='stretch'):
        st.subheader('Your profile', icon=':material/person:', anchor=False)
        if p:
            st.markdown(f"**{p['age']} years** · {p['height']} cm · {level_names.get(p['level'],p['level'])}")
            st.caption(f"{p['days']} training days/week · {p['minutes']} min/session")
            st.markdown(f":material/fitness_center: {p['equipment']}  \n:material/restaurant: {p['diet']}")
            if p.get('goal_notes'):
                st.markdown(f"**Your focus:** {p['goal_notes']}")
        else:
            st.info('Create your profile so plans and coach responses can be personalized.', icon=':material/arrow_downward:')

        with st.expander('Edit profile' if p else 'Create profile', expanded=not p, icon=':material/edit:'):
            d = p or {}
            with st.form('profile'):
                identity = st.columns(3)
                name = identity[0].text_input('First name', d.get('name', ''))
                age = identity[1].number_input('Age', 18, 90, int(d.get('age', 30)))
                height = identity[2].number_input('Height (cm)', 120, 230, int(d.get('height', 175)))

                goals = ['Build muscle', 'Improve fitness', 'Lose weight']
                current_goal = goal_names.get(d.get('goal','Improve fitness'),d.get('goal','Improve fitness'))
                goal = st.selectbox('Your goal', goals, index=goals.index(current_goal) if current_goal in goals else 1)
                weight_cols = st.columns(2)
                weight = weight_cols[0].number_input('Starting weight (kg)', 35., 300., float(d.get('weight', 75.)))
                target = weight_cols[1].number_input('Target weight (kg)', 35., 300., float(d.get('target_weight') or weight))
                target_enabled = st.checkbox('Use target weight', bool(d.get('target_weight')))
                goal_notes = st.text_area('What would you like to achieve?', d.get('goal_notes', ''), placeholder='e.g. train consistently and get stronger')

                training_cols = st.columns(3)
                levels = ['Beginner', 'Advanced']
                current_level = level_names.get(d.get('level','Beginner'),d.get('level','Beginner'))
                level = training_cols[0].selectbox('Experience', levels, index=levels.index(current_level) if current_level in levels else 0)
                days = training_cols[1].number_input('Days/week', 1, 6, int(d.get('days', 3)))
                minutes = training_cols[2].number_input('Min/session', 20, 90, int(d.get('minutes', 45)), step=5)

                equipment = st.text_input('Training location and equipment', d.get('equipment', 'Gym'))
                lifestyle = st.columns(2)
                activity = lifestyle[0].text_input('Daily activity', d.get('activity', 'Mostly sedentary'))
                diet = lifestyle[1].text_input('Dietary preference', d.get('diet', 'Omnivore'))
                allergies = st.text_area('Allergies and foods you avoid', d.get('allergies', ''))
                limitations = st.text_area('Injuries and limitations', d.get('limitations', ''))

                if st.form_submit_button('Save profile', type='primary', icon=':material/save:', width='stretch'):
                    save('profile', date.today(), dict(
                        name=name, age=age, height=height, weight=weight, goal=goal,
                        target_weight=target if target_enabled else None, goal_notes=goal_notes,
                        level=level, days=days, minutes=minutes, equipment=equipment,
                        activity=activity, diet=diet, allergies=allergies, limitations=limitations,
                    ))
                    notify('Profile and goal saved.')

with progress_col:
    with st.container(border=True, height='stretch'):
        st.subheader('Weight progress', icon=':material/query_stats:', anchor=False)
        with st.form('weight', border=False):
            with st.container(horizontal=True, vertical_alignment='bottom'):
                day = st.date_input('Measurement date', date.today(), max_value=date.today())
                kg = st.number_input('Weight (kg)', 35., 300., float(current_weight or 75.))
                save_weight = st.form_submit_button('Save weight', icon=':material/add:', type='primary')
            if save_weight:
                save('weight', day, {'kg': kg})
                notify('Weight saved.')

        if weights:
            df = pd.DataFrame(weights).groupby('day', as_index=False)['kg'].last()
            if p and p.get('target_weight'):
                df['Target weight'] = p['target_weight']
            st.line_chart(
                df, x='day', y=['kg', 'Target weight'] if 'Target weight' in df else ['kg'],
                x_label='Date', y_label='Weight (kg)', height=300,
            )
            manage_entries('weight', 'Manage measurements')
        else:
            st.info('Save your first measurement to start tracking your progress.', icon=':material/monitoring:')

st.subheader('Your plans', icon=':material/event_note:', anchor=False)
plan_columns = st.columns(2, gap='medium')
for column, (kind, label, description, path, icon) in zip(plan_columns, [
    ('training_plan', 'Training plan', 'Exercises, sets, and your weekly structure', 'fitness_pages/training.py', ':material/fitness_center:'),
    ('nutrition_plan', 'Meal plan', 'Meals, portions, and nutrition values', 'fitness_pages/nutrition.py', ':material/restaurant:'),
]):
    plans = records(kind)
    with column.container(border=True, height='stretch'):
        st.subheader(label, icon=icon, anchor=False)
        st.caption(description)
        st.markdown(':green-badge[Active]' if plans else ':gray-badge[Not created yet]')
        if plans:
            st.caption(f"Active since {plans[-1]['day']}")
        st.page_link(path, label=f'Open {label.lower()}', icon=':material/arrow_forward:')

st.caption(':material/health_and_safety: For adults. Review AI suggestions and photo estimates before using them.')
