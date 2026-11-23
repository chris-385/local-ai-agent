from datetime import date
import hashlib
import streamlit as st
from fitness_core import stream_coach
from fitness_ui import add, ai_context, data, flash, page_header, profile
from fitness_actions import detect_action, exercise_lines, change_exercise

flash()
p=profile()
SUGGESTIONS={
    'Create my training plan':('Create a training plan for me','Create a complete, compact training plan with exercises, sets, reps, and rest periods tailored to the profile.','Create training plan',':material/fitness_center:'),
    'Create my meal plan':('Create a meal plan for me','Create a complete, compact meal plan with portions and estimated nutrition values tailored to the profile. Strictly follow allergies.','Create meal plan',':material/restaurant:'),
    'How do I get started?':('How do I get started with my goal?',None,'Ask a question',':material/flag:'),
}

with st.container(horizontal=True,vertical_alignment='center'):
    with st.container(width='stretch'):
        page_header('AI Coach','Ask anything about training and nutrition.',':material/auto_awesome:')
    chats=data('coach_chat')
    if chats:
        with st.popover('History',icon=':material/history:',type='tertiary'):
            chat_options={}
            for row in reversed(chats):
                history=row.get('history',[])
                first_question=next((content for role,content in history if role=='user'),'Conversation')
                chat_options[f"{first_question.replace(chr(10),' ')[:45]} · {row['day']} · #{row['id']}"]=row
            selected_chat_label=st.selectbox('Conversation',list(chat_options),key='load_chat')
            if st.button('Open',icon=':material/open_in_new:',width='stretch'):
                chat_data=chat_options[selected_chat_label]
                st.session_state.fitness_chat=chat_data['history']
                st.session_state['coach_actions']={int(k):v for k,v in chat_data.get('actions',{}).items()}
                st.rerun()
    if st.session_state.fitness_chat and st.button('New chat',key='reset_chat',icon=':material/add_comment:',type='tertiary'):
        st.session_state.fitness_chat=[]
        st.session_state['coach_actions']={}
        st.rerun()
if not p:
    st.caption(':material/person: Create a profile on Home so the coach can consider your goals and limitations.')

def adoption_actions(content,index,action):
    if action not in ('training_plan','nutrition_plan','exercise'):
        return
    if action == 'exercise':
        with st.expander('Add exercise to my training plan',icon=':material/add_circle:'):
            plans=data('training_plan')
            if not plans:
                st.info('Save a training plan first. You can then add or replace exercises.',icon=':material/info:')
                return
            active=plans[-1]
            proposal=st.selectbox('Suggested exercise',exercise_lines(content),key=f'proposal_{index}')
            suggestion=st.text_area('Review and edit exercise',proposal,key=f'exercise_text_{index}_'+hashlib.sha256(proposal.encode()).hexdigest()[:8])
            operation=st.radio('Action',['Add','Replace'],key=f'operation_{index}',horizontal=True)
            day=st.text_input('Training day / session',placeholder='e.g. Monday or Upper body A',key=f'day_{index}')
            replacement=None
            if operation=='Replace':
                candidates=exercise_lines(active['content'])
                # Include line positions so duplicate exercises on different days are selectable.
                candidates=[(i,line) for i,line in enumerate(active['content'].splitlines()) if line.strip() in candidates]
                if not candidates:
                    st.info('No clearly selectable exercise was found in the active plan.')
                    return
                replacement=st.selectbox('Replace this exercise',candidates,format_func=lambda item:f'Line {item[0]+1}: {item[1]}',key=f'replace_{index}_{active["id"]}')
                st.caption('The selected line will be replaced in its current position. Check that it belongs to the specified training day.')
            change_token=hashlib.sha256((content+suggestion+day+operation+str(replacement)).encode()).hexdigest()
            already_applied=any(r.get('change_token')==change_token for r in plans)
            if st.button('Already applied' if already_applied else ('Replace exercise' if operation=='Replace' else 'Add exercise'),key=f'apply_exercise_{index}',disabled=already_applied,icon=':material/check:',type='primary'):
                try:
                    if replacement:
                        if not day.strip() or not suggestion.strip():
                            raise ValueError('Please enter an exercise and training day.')
                        lines=active['content'].splitlines()
                        lines[replacement[0]]=suggestion.strip()
                        updated='\n'.join(lines)
                    else:
                        updated=change_exercise(active['content'],suggestion,day)
                    add('training_plan',date.today(),{'content':updated,'profile':active.get('profile'),'source':'coach','previous_plan_id':active['id'],'change_token':change_token,'change':{'operation':operation,'day':day,'exercise':suggestion}})
                    st.session_state['fitness_flash']='Training plan updated. The previous version is still available.'
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        return
    kind=action
    label='Use as training plan' if kind=='training_plan' else 'Use as meal plan'
    with st.expander('Add plan to my profile',icon=':material/save:'):
        st.caption('Use this suggestion as your active plan. Previous versions remain available.')
        if not p:
            st.caption('Create your profile on Home first.')
        token=hashlib.sha256((kind+content).encode()).hexdigest()
        saved=any(r.get('source_token')==token for r in data(kind))
        if st.button('Already added' if saved else label,key=f'adopt_{index}_{kind}',disabled=saved or not p,icon=':material/check:',type='primary'):
            add(kind,date.today(),{'content':content,'profile':p,'source':'coach','source_token':token})
            st.rerun()

suggested=None
if not st.session_state.fitness_chat:
    with st.container(border=True,horizontal_alignment='center'):
        st.subheader('What would you like to achieve today?',anchor=False)
        st.caption('Pick a suggestion or type your own question below.')
        with st.container(horizontal=True,horizontal_alignment='center'):
            for label,(_,_,_,icon) in SUGGESTIONS.items():
                if st.button(label,icon=icon,key='suggest_'+label):
                    suggested=label

for index,(role,content) in enumerate(st.session_state.fitness_chat):
    with st.chat_message(role):
        st.markdown(content)
        if role=='assistant':
            previous=st.session_state.fitness_chat[index-1][1] if index else ''
            # Revalidate visible content, including restored conversations. Cached labels
            # from older sessions must never force an irrelevant adoption action.
            action=detect_action(previous,content)
            adoption_actions(content,index,action)
question=st.chat_input('Message your AI Coach …',max_chars=4000)
mode='Ask a question'
request=question
if suggested:
    question,instruction,mode,_=SUGGESTIONS[suggested]
    request=f'{instruction} Request: {question}' if instruction else question
if question:
    with st.chat_message('user'):
        st.markdown(question)
    try:
        plan=mode!='Ask a question' or 'plan' in question.lower()
        context=ai_context()
        with st.chat_message('assistant'):
            status=st.empty()
            status.caption('AI Coach is starting … the response will appear as it is written.')
            def chunks():
                for chunk in stream_coach(st.session_state['fitness_text_model'],context,st.session_state.fitness_chat,request,plan=plan):
                    status.empty()
                    yield chunk
            answer=st.write_stream(chunks())
        index=len(st.session_state.fitness_chat)+1
        st.session_state.setdefault('coach_actions',{})[index]=detect_action(question,answer,mode)
        st.session_state.fitness_chat.extend([('user',question),('assistant',answer)])
        add('coach_chat', date.today(), {'history': st.session_state.fitness_chat, 'actions': st.session_state.get('coach_actions', {})})
        st.rerun()
    except Exception as exc:
        if 'status' in locals():
            status.empty()
        st.error(f'AI Coach unavailable: {exc}. Please try again.')
