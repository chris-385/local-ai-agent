from datetime import date, timedelta
import pandas as pd
import streamlit as st
from fitness_ui import TRAINING_PROMPT, add, data, flash, manage_entries, notify, page_header, plan_panel

flash()
page_header('Training', 'Log your workouts, see your progress, and follow your plan.', ':material/fitness_center:')
view = st.segmented_control('Section', ['Log workout', 'Progress', 'Plan'], default='Log workout', key='training_view', label_visibility='collapsed')
workouts = data('workout')
exercises = data('exercise')

if view == 'Plan':
    plan_panel('training_plan', TRAINING_PROMPT)

elif view == 'Progress':
    week_start = date.today() - timedelta(days=date.today().weekday())
    this_week = [w for w in workouts if week_start.isoformat() <= w['day'] <= date.today().isoformat()]
    with st.container(horizontal=True):
        st.metric('Workouts this week', len(this_week), border=True)
        st.metric('Minutes this week', sum(w['minutes'] for w in this_week), border=True)
        st.metric('Workouts total', len(workouts), border=True)
    if not workouts:
        st.info('Log your first workout to see your progress here.', icon=':material/trending_up:')
        st.stop()
    chart_col, lift_col = st.columns(2, gap='medium')
    with chart_col.container(border=True, height='stretch'):
        st.subheader('Training time per week', anchor=False)
        week_df = pd.DataFrame(workouts)
        week_df['Week'] = pd.to_datetime(week_df['day']).dt.to_period('W').dt.start_time.dt.date.astype(str)
        st.bar_chart(week_df.groupby('Week', as_index=False)['minutes'].sum(), x='Week', y='minutes', x_label='', y_label='Minutes', height=260)
    with lift_col.container(border=True, height='stretch'):
        st.subheader('Exercise progress', anchor=False)
        if exercises:
            selected = st.selectbox('Exercise', sorted({e['name'] for e in exercises}), key='progress_exercise')
            df = pd.DataFrame([e for e in exercises if e['name'] == selected])
            trend = df.groupby('day', as_index=False)['load'].max()
            st.line_chart(trend, x='day', y='load', x_label='', y_label='Max weight (kg)', height=200)
        else:
            st.caption('Add exercises when logging a workout to track your strength.')
    with st.expander('Workout history', icon=':material/history:'):
        st.dataframe(
            pd.DataFrame(workouts[::-1])[['day', 'name', 'minutes', 'notes']],
            column_config={'day': 'Date', 'name': 'Workout', 'minutes': 'Minutes', 'notes': 'Notes'},
            hide_index=True,
        )
        if exercises:
            st.dataframe(
                pd.DataFrame(exercises[::-1])[['day', 'name', 'sets', 'reps', 'load']],
                column_config={'day': 'Date', 'name': 'Exercise', 'sets': 'Sets', 'reps': 'Reps', 'load': 'Weight (kg)'},
                hide_index=True,
            )
    manage_entries('workout', 'Manage workouts')
    if exercises:
        manage_entries('exercise', 'Manage exercises')

else:
    with st.form('workout'):
        basics = st.columns([1, 1.6, 0.8])
        day = basics[0].date_input('Date', date.today(), max_value=date.today())
        title = basics[1].text_input('Workout', placeholder='e.g. Full body A')
        minutes = basics[2].number_input('Minutes', 1, 600, 45, step=5)
        st.caption('Exercises (optional) – add one row per exercise.')
        rows = st.data_editor(
            pd.DataFrame({'name': pd.Series(dtype='str'), 'sets': pd.Series(dtype='int'), 'reps': pd.Series(dtype='int'), 'load': pd.Series(dtype='float')}),
            num_rows='dynamic', hide_index=True, key='exercise_rows',
            column_config={
                'name': st.column_config.TextColumn('Exercise', required=True),
                'sets': st.column_config.NumberColumn('Sets', min_value=1, max_value=30, default=3),
                'reps': st.column_config.NumberColumn('Reps', min_value=1, max_value=200, default=10),
                'load': st.column_config.NumberColumn('Weight (kg)', min_value=0., max_value=1000., step=0.5, default=0.),
            },
        )
        notes = st.text_input('Notes', placeholder='Optional: how did it feel?')
        if st.form_submit_button('Save workout', type='primary', icon=':material/save:', width='stretch'):
            if not title.strip():
                st.error('Please give your workout a name.')
            else:
                workout_id = add('workout', day, {'name': title.strip(), 'minutes': minutes, 'notes': notes})
                count = 0
                for row in rows.dropna(subset=['name']).to_dict('records'):
                    if str(row['name']).strip():
                        add('exercise', day, dict(
                            name=str(row['name']).strip(), sets=int(row.get('sets') or 1), reps=int(row.get('reps') or 1),
                            load=float(row.get('load') or 0.), notes='', workout_id=workout_id,
                        ))
                        count += 1
                notify(f'Workout saved{f" with {count} exercises" if count else ""}.')
    if workouts:
        last = workouts[-1]
        st.caption(f":material/history: Last workout: **{last['name']}** on {last['day']} ({last['minutes']} min)")
