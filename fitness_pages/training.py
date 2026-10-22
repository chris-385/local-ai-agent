from datetime import date, timedelta
import pandas as pd
import streamlit as st
from fitness_core import records, save
from fitness_ui import flash, notify, plan_panel, TRAINING_PROMPT, manage_entries, page_header

flash()
page_header('Training', 'Plan your week, log sessions, and track your progress.', ':material/fitness_center:')
view=st.segmented_control('Section',['Training plan','Sessions','Exercises & progress'],default='Training plan',key='training_view',width='stretch')
workouts=records('workout')
exercises=records('exercise')
if view=='Training plan':
    plan_panel('training_plan',TRAINING_PROMPT)
elif view=='Sessions':
    week_start=date.today()-timedelta(days=date.today().weekday())
    this_week=[w for w in workouts if week_start.isoformat()<=w['day']<=date.today().isoformat()]
    metrics=st.columns(3)
    metrics[0].metric('This week',len(this_week),border=True)
    metrics[1].metric('Training time',f"{sum(w['minutes'] for w in this_week)} min",border=True)
    metrics[2].metric('Total sessions',len(workouts),border=True)
    with st.container(border=True):
        st.subheader('Log a session',icon=':material/add_circle:',anchor=False)
        with st.form('workout',border=False):
            basics=st.columns([1,1,0.7])
            day=basics[0].date_input('Training date',date.today(),max_value=date.today())
            title=basics[1].text_input('Session name',placeholder='e.g. Full body A')
            minutes=basics[2].number_input('Duration (min)',1,600,45)
            notes=st.text_area('Notes',placeholder='Optional: energy, highlights, or a personal best')
            if st.form_submit_button('Save session',type='primary',icon=':material/save:',width='stretch'):
                if title.strip():
                    save('workout',day,{'name':title.strip(),'minutes':minutes,'notes':notes})
                    notify('Session saved. Add its exercises under “Exercises & progress.”')
                else:
                    st.error('Please name your session.')
    if workouts:
        st.subheader('Your sessions',icon=':material/history:',anchor=False)
        st.dataframe(pd.DataFrame(workouts)[['day','name','minutes','notes']].rename(columns={'day':'Date','name':'Session','minutes':'Minutes','notes':'Notes'}),hide_index=True,width='stretch')
        week_df=pd.DataFrame(workouts)
        week_df['Week']=pd.to_datetime(week_df['day']).dt.to_period('W').astype(str)
        st.bar_chart(week_df.groupby('Week',as_index=False)['minutes'].sum(),x='Week',y='minutes',y_label='Minutes',height=280)
        manage_entries('workout','Manage sessions')
    else:
        st.info('Log your first session to start tracking your training progress.',icon=':material/fitness_center:')
else:
    with st.container(border=True):
        st.subheader('Log an exercise',icon=':material/add_circle:',anchor=False)
        st.caption('Log identical sets together. Create another entry when the weight or reps change.')
        with st.form('exercise',border=False):
            context=st.columns(2)
            day=context[0].date_input('Exercise date',date.today(),max_value=date.today())
            linked=context[1].selectbox('Add to a session',[None]+workouts[::-1],format_func=lambda w:'No session' if w is None else f"{w['day']} · {w['name']} · #{w['id']}")
            name=st.text_input('Exercise',placeholder='e.g. Squat')
            performance=st.columns(3)
            sets=performance[0].number_input('Sets',1,30,3)
            reps=performance[1].number_input('Reps',1,200,10)
            load=performance[2].number_input('Additional weight (kg)',0.,1000.,0.,step=0.5)
            notes=st.text_input('Technique / notes',placeholder='Optional')
            if st.form_submit_button('Save exercise',type='primary',icon=':material/save:',width='stretch'):
                if name.strip():
                    save('exercise',linked['day'] if linked else day,dict(name=name.strip(),sets=sets,reps=reps,load=load,notes=notes,workout_id=linked['id'] if linked else None))
                    notify('Exercise saved.')
                else:
                    st.error('Please enter an exercise.')
    if exercises:
        st.subheader('Performance progress',icon=':material/trending_up:',anchor=False)
        names=sorted(set(e['name'] for e in exercises))
        filters=st.columns(2)
        selected=filters[0].selectbox('Compare exercise',names)
        df=pd.DataFrame([e for e in exercises if e['name']==selected])
        df['Volume (kg)']=df['sets']*df['reps']*df['load']
        trend=df.groupby('day',as_index=False).agg({'load':'max','Volume (kg)':'sum'})
        metric=filters[1].selectbox('Metric',['Maximum additional weight','Training volume'])
        st.line_chart(trend,x='day',y='load' if metric=='Maximum additional weight' else 'Volume (kg)',x_label='Date',y_label='kg',height=300)
        st.caption('Volume = sets × reps × additional weight. Body weight is not included.')
        st.dataframe(df[['day','name','sets','reps','load','workout_id','notes']].rename(columns={'day':'Date','name':'Exercise','sets':'Sets','reps':'Reps','load':'Additional weight (kg)','workout_id':'Session ID','notes':'Notes'}),hide_index=True,width='stretch')
        manage_entries('exercise','Manage exercises')
    else:
        st.info('Your performance chart starts with your first exercise entry.',icon=':material/trending_up:')
