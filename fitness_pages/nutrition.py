from datetime import date
import hashlib
import pandas as pd
import streamlit as st
from fitness_core import records, save, ask, validate_meal
from fitness_ui import flash, notify, plan_panel, NUTRITION_PROMPT, manage_entries, page_header

flash()
page_header('Nutrition', 'Log meals, track nutrition, and create practical plans.', ':material/restaurant:')
view=st.segmented_control('Section',['Daily overview','Log a meal','Meal plan'],default='Daily overview',key='nutrition_view',width='stretch')
meals=records('meal')
if view=='Meal plan':
    plan_panel('nutrition_plan',NUTRITION_PROMPT)
elif view=='Daily overview':
    with st.container(horizontal=True,vertical_alignment='bottom'):
        day=st.date_input('View date',date.today(),key='nutrition_day')
        st.caption('All values are based on the meals you logged.')
    selected=[m for m in meals if m['day']==day.isoformat()]
    total={k:sum(m[k] for m in selected) for k in ['kcal','protein','carbs','fat']}
    targets=records('nutrition_targets')
    target=targets[-1] if targets else {}
    metrics=st.columns(4)
    for column,(key,label,unit) in zip(metrics,[('kcal','Calories','kcal'),('protein','Protein','g'),('carbs','Carbohydrates','g'),('fat','Fat','g')]):
        column.metric(label,f"{total[key]:.0f} {unit}",border=True)
    if target.get('kcal'):
        st.progress(min(total['kcal']/target['kcal'],1.),text=f"{total['kcal']:.0f} of {target['kcal']:.0f} kcal logged")
        st.caption(f"Difference from your self-defined target: {target['kcal']-total['kcal']:+.0f} kcal. Only logged meals are included.")
    if selected:
        st.dataframe(pd.DataFrame(selected)[['name','kcal','protein','carbs','fat']].rename(columns={'name':'Meal','protein':'Protein (g)','carbs':'Carbohydrates (g)','fat':'Fat (g)','kcal':'kcal'}),hide_index=True,width='stretch')
    else:
        st.info('No meals have been logged for this date. Open “Log a meal” to get started.',icon=':material/add_circle:')
    with st.expander('Daily targets',icon=':material/flag:'):
        st.caption('Optional. You define these values yourself; they are not calculated recommendations. Set a target to 0 to disable it.')
        with st.form('targets',border=False):
            values={}
            target_columns=st.columns(4)
            for column,(key,label,maximum) in zip(target_columns,[('kcal','Calorie target',10000),('protein','Protein target (g)',1000),('carbs','Carbohydrate target (g)',1000),('fat','Fat target (g)',1000)]):
                values[key]=column.number_input(label,0.,float(maximum),float(target.get(key,0.)))
            if st.form_submit_button('Save daily targets',icon=':material/save:',width='stretch'):
                save('nutrition_targets',date.today(),values)
                notify('Daily targets saved.')
    if target:
        for key,label in [('protein','Protein'),('carbs','Carbohydrates'),('fat','Fat')]:
            if target.get(key):
                st.progress(min(total[key]/target[key],1.),text=f"{label}: {total[key]:.0f} / {target[key]:.0f} g")
    if meals:
        st.subheader('Nutrition history',icon=':material/bar_chart:',anchor=False)
        df=pd.DataFrame(meals).groupby('day',as_index=False)[['kcal','protein','carbs','fat']].sum()
        st.bar_chart(df,x='day',y='kcal',x_label='Date',y_label='Logged kcal',height=280)
        manage_entries('meal','Manage meals')
else:
    with st.container(border=True):
        st.subheader('New meal',icon=':material/add_circle:',anchor=False)
        mode=st.segmented_control('Input method',['Manual','Upload photo','Camera'],default='Manual',key='meal_mode',width='stretch')
    photo=None
    detail=''
    if mode!='Manual':
        st.caption('Calories and nutrition values from photos are estimates. Add the portion size, oils, and hidden ingredients, then review the result.')
        photo=st.camera_input('Take a meal photo') if mode=='Camera' else st.file_uploader('Upload a meal photo',type=['jpg','jpeg','png','webp'])
        detail=st.text_input('Portion size and additional ingredients',placeholder='e.g. 200 g rice, 1 tbsp oil')
        if photo:
            st.image(photo,width=360)
            fingerprint=hashlib.sha256(photo.getvalue()+detail.encode()).hexdigest()
            if st.button('Estimate calories and nutrition',type='primary',icon=':material/auto_awesome:',width='stretch'):
                st.session_state.pop('meal_draft',None)
                try:
                    with st.spinner('Analyzing your meal …'):
                        result=ask(st.session_state['fitness_vision_model'],'Analyze the food photo. Return JSON with is_food (bool), name (string), kcal, protein, carbs, fat (numbers for the full portion; macros in grams), and assumptions (English description of portion assumptions and uncertainty). If no food is visible, set is_food=false. User details: '+detail,photo.getvalue(),True)
                        st.session_state['meal_draft']={'fingerprint':fingerprint,'data':validate_meal(result)}
                except Exception as exc:
                    st.error(f'Photo analysis is unavailable: {exc}. Check your vision model or log the meal manually.')
    stored=st.session_state.get('meal_draft',{})
    draft=stored.get('data',{}) if photo and stored.get('fingerprint')==hashlib.sha256(photo.getvalue()+detail.encode()).hexdigest() else {}
    if draft:
        st.info('Estimate: '+draft['assumptions'],icon=':material/info:')
    revision=hashlib.sha256(str(draft).encode()).hexdigest()[:12]
    with st.form('meal'):
        name=st.text_input('Meal',draft.get('name',''),key='meal_name_'+revision)
        day=st.date_input('Meal date',date.today(),max_value=date.today())
        values={}
        value_columns=st.columns(4)
        for column,(key,label) in zip(value_columns,[('kcal','Calories (kcal)'),('protein','Protein (g)'),('carbs','Carbohydrates (g)'),('fat','Fat (g)')]):
            values[key]=column.number_input(label,0.,10000.,float(draft.get(key,0.)),key='meal_'+key+revision)
        if st.form_submit_button('Save meal',type='primary',icon=':material/save:',width='stretch'):
            if not name.strip():
                st.error('Please enter a name.')
            else:
                save('meal',day,dict(name=name.strip(),**values,source='photo' if draft else 'manual'))
                st.session_state.pop('meal_draft',None)
                notify('Meal saved. You can find it in your daily overview.')
