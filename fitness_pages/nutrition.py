from datetime import date, timedelta
import hashlib
import pandas as pd
import streamlit as st
from fitness_core import RECOMMENDED_VISION_MODEL, ask, validate_meal
from fitness_ui import NUTRITION_PROMPT, add, data, flash, manage_entries, notify, page_header, plan_panel

flash()
page_header('Nutrition', 'Log your meals and keep an eye on your daily targets.', ':material/restaurant:')
view = st.segmented_control('Section', ['Today', 'Log meal', 'Meal plan'], default='Today', key='nutrition_view', label_visibility='collapsed')
meals = data('meal')
MACROS = [('kcal', 'Calories', 'kcal'), ('protein', 'Protein', 'g'), ('carbs', 'Carbs', 'g'), ('fat', 'Fat', 'g')]

if view == 'Meal plan':
    plan_panel('nutrition_plan', NUTRITION_PROMPT)

elif view == 'Today':
    targets = data('nutrition_targets')
    target = targets[-1] if targets else {}
    with st.container(horizontal=True, vertical_alignment='bottom'):
        day = st.date_input('Date', date.today(), key='nutrition_day', width=180)
        with st.popover('Daily targets', icon=':material/flag:'):
            st.caption('Optional values you set yourself. Use 0 to turn a target off.')
            with st.form('targets', border=False):
                values = {key: st.number_input(f'{label} ({unit})', 0., 10000., float(target.get(key, 0.))) for key, label, unit in MACROS}
                if st.form_submit_button('Save daily targets', icon=':material/save:', type='primary', width='stretch'):
                    add('nutrition_targets', date.today(), values)
                    notify('Daily targets saved.')
    selected = [m for m in meals if m['day'] == day.isoformat()]
    total = {key: sum(m[key] for m in selected) for key, _, _ in MACROS}
    with st.container(horizontal=True):
        for key, label, unit in MACROS:
            goal = target.get(key)
            st.metric(
                label, f'{total[key]:.0f} {unit}',
                f'{goal - total[key]:.0f} {unit} left' if goal and goal >= total[key] else f'{total[key] - goal:.0f} {unit} over' if goal else None,
                delta_color='off', delta_arrow='off', border=True,
            )
    if selected:
        st.dataframe(
            pd.DataFrame(selected)[['name', 'kcal', 'protein', 'carbs', 'fat']],
            column_config={'name': 'Meal', 'kcal': 'kcal', 'protein': 'Protein (g)', 'carbs': 'Carbs (g)', 'fat': 'Fat (g)'},
            hide_index=True,
        )
    else:
        st.info('No meals logged for this day yet. Switch to **Log meal** to add one.', icon=':material/add_circle:')
    recent = [m for m in meals if m['day'] >= (date.today() - timedelta(days=13)).isoformat()]
    if recent:
        with st.expander('Last 14 days', icon=':material/bar_chart:'):
            df = pd.DataFrame(recent).groupby('day', as_index=False)['kcal'].sum()
            st.bar_chart(df, x='day', y='kcal', x_label='', y_label='kcal', height=240)
    manage_entries('meal', 'Manage meals')

else:
    mode = st.segmented_control('Input', ['Enter manually', 'From photo'], default='Enter manually', key='meal_mode')
    photo = None
    detail = ''
    if mode == 'From photo':
        if not st.session_state.get('fitness_vision_available'):
            st.warning(
                'Photo analysis needs an image-capable model, and none is installed in Ollama yet. '
                f'Install one in a terminal, then reload this page:\n\n`ollama pull {RECOMMENDED_VISION_MODEL}`',
                icon=':material/photo_camera:',
            )
        with st.container(border=True):
            photo = st.file_uploader('Meal photo', type=['jpg', 'jpeg', 'png', 'webp'])
            detail = st.text_input('Portion size and hidden ingredients (optional)', placeholder='e.g. 200 g rice, 1 tbsp oil')
            if photo:
                st.image(photo, width=320)
                fingerprint = hashlib.sha256(photo.getvalue() + detail.encode()).hexdigest()
                if st.button('Estimate nutrition', type='primary', icon=':material/auto_awesome:'):
                    st.session_state.pop('meal_draft', None)
                    try:
                        with st.spinner('Analyzing your meal …'):
                            result = ask(st.session_state['fitness_vision_model'], 'Analyze the food photo. Return JSON with is_food (bool), name (string), kcal, protein, carbs, fat (numbers for the full portion; macros in grams), and assumptions (English description of portion assumptions and uncertainty). If no food is visible, set is_food=false. User details: ' + detail, photo.getvalue(), True)
                            st.session_state['meal_draft'] = {'fingerprint': fingerprint, 'data': validate_meal(result)}
                    except Exception as exc:
                        st.error(f'Photo analysis is unavailable: {exc}. You can still enter the meal manually.')
            st.caption('Photo values are estimates – review them before saving.')
    stored = st.session_state.get('meal_draft', {})
    draft = stored.get('data', {}) if photo and stored.get('fingerprint') == hashlib.sha256(photo.getvalue() + detail.encode()).hexdigest() else {}
    if draft:
        st.info('Estimate: ' + draft['assumptions'], icon=':material/info:')
    revision = hashlib.sha256(str(draft).encode()).hexdigest()[:12]
    with st.form('meal'):
        basics = st.columns([2, 1])
        name = basics[0].text_input('Meal', draft.get('name', ''), placeholder='e.g. Chicken with rice', key='meal_name_' + revision)
        day = basics[1].date_input('Date', date.today(), max_value=date.today())
        values = {}
        for column, (key, label, unit) in zip(st.columns(4), MACROS):
            values[key] = column.number_input(f'{label} ({unit})', 0., 10000., float(draft.get(key, 0.)), key='meal_' + key + revision)
        if st.form_submit_button('Save meal', type='primary', icon=':material/save:', width='stretch'):
            if not name.strip():
                st.error('Please enter a name.')
            else:
                add('meal', day, dict(name=name.strip(), **values, source='photo' if draft else 'manual'))
                st.session_state.pop('meal_draft', None)
                notify('Meal saved.')
