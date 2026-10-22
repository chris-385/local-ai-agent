"""Shared UI actions; each of the four pages owns its page content."""
import json
from datetime import date
import streamlit as st
from fitness_core import records, save, stream_coach, delete

TRAINING_PROMPT = ('Create a personalized weekly training plan. Consider the training days, time, equipment, experience, and limitations in the profile. '
    'For each session, include exercises, sets, reps, rest periods, and alternatives. Add a warm-up, rest days, and cautious progression. Do not prescribe rehabilitation.')
NUTRITION_PROMPT = ('Create a personalized 7-day meal plan with portions in grams, estimated calories, protein, carbohydrates, and fat for each meal and daily totals. '
    'Include a shopping list and alternatives. Strictly follow allergies, dietary preferences, and self-defined nutrition targets. '
    'Explain assumptions, do not invent profile data, and avoid aggressive deficits or therapeutic diets.')


def profile():
    rows = records('profile')
    return {k:v for k,v in rows[-1].items() if k not in ('id','day')} if rows else None


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


def plan_panel(kind, instruction):
    p = profile()
    plan_name = 'training plan' if kind == 'training_plan' else 'meal plan'
    if not p:
        st.info('Save your profile in Overview first so the plan can be personalized.', icon=':material/person:')
    with st.container(border=True):
        st.subheader('Your personalized plan', icon=':material/auto_awesome:', anchor=False)
        st.caption('The coach considers your profile and current goals.')
        generate = st.button(
            f'Create {plan_name}', key='generate_'+kind, type='primary',
            icon=':material/auto_awesome:', disabled=not p, width='stretch',
        )
    if generate:
        context = dict(p)
        weights = records('weight')
        if weights:
            context['Current weight (kg)'] = weights[-1]['kg']
        targets = records('nutrition_targets')
        if kind == 'nutrition_plan' and targets:
            context['Self-defined nutrition targets'] = {k:v for k,v in targets[-1].items() if k not in ('id','day')}
        try:
            with st.status('Creating your plan …', expanded=True) as status:
                content = st.write_stream(stream_coach(st.session_state['fitness_text_model'], context, [], instruction, plan=True))
                status.update(label='Plan created', state='complete', expanded=False)
            if 'Response limit reached.' in content:
                st.warning('The draft is incomplete and was not saved as your active plan. Ask the coach for a shorter plan.')
            else:
                save(kind, date.today(), {'content':content,'profile':p,'source':'generator'})
                notify('Your new plan is saved and active.')
        except Exception as exc:
            st.error(f'The plan could not be created: {exc}')
    plans = records(kind)
    if plans:
        active = plans[-1]
        with st.container(border=True):
            st.subheader('Active plan', icon=':material/check_circle:', anchor=False)
            st.caption(f"Saved on {active['day']} · {'Added from coach' if active.get('source') == 'coach' else 'Personalized plan'}")
            if active.get('profile') != p:
                st.info('Your profile has changed since this plan was created. Check whether it still fits your goal.', icon=':material/info:')
            st.markdown(active['content'])
            st.download_button('Download plan',active['content'],file_name=kind+'.md',key='download_'+kind,icon=':material/download:')
        if len(plans)>1:
            with st.expander('Previous plans', icon=':material/history:'):
                old = st.selectbox('Version', plans[:-1][::-1], format_func=lambda r:f"{r['day']} · Version #{r['id']}",key='history_'+kind)
                st.markdown(old['content'])
    else:
        st.info('No active plan yet. Create one here or add a suggestion from the coach.', icon=':material/lightbulb:')


def manage_entries(kind, title):
    entries = records(kind)
    if entries:
        with st.expander(title, icon=':material/settings:'):
            st.download_button('Export entries',json.dumps(entries,ensure_ascii=False,indent=2),file_name=kind+'.json',key='export_'+kind,icon=':material/download:')
            selected = st.selectbox('Entry',entries,format_func=lambda r:f"{r['day']} · {r.get('name', str(r.get('kg',''))+' kg')} · #{r['id']}",key='manage_'+kind)
            if st.button('Delete entry',key='delete_'+kind,icon=':material/delete:',type='tertiary'):
                delete(selected['id'])
                notify('Entry deleted.')
