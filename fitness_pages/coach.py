from datetime import date
import hashlib
import streamlit as st
from fitness_core import stream_coach, records, save
from fitness_ui import profile, flash, page_header
from fitness_actions import detect_action, exercise_lines, change_exercise

flash()
page_header('Coach', 'Ask questions, build plans, and add useful suggestions directly.', ':material/forum:')
p=profile()
if not p:
    st.info('Save your profile so the coach can consider your goals and limitations.',icon=':material/person:')

chats = records('coach_chat')
with st.container(border=True):
    mode=st.segmented_control('How can I help?',['Ask a question','Create training plan','Create meal plan'],default='Ask a question',key='coach_mode',width='stretch')
    with st.container(horizontal=True,vertical_alignment='center'):
        if chats:
            with st.popover('Chat history',icon=':material/history:'):
                chat_options={}
                for row in reversed(chats):
                    history=row.get('history',[])
                    first_question=next((content for role,content in history if role=='user'),'Conversation')
                    title=first_question.replace('\n',' ')[:45]
                    chat_options[f"{title} · {row['day']} · #{row['id']}"]=row
                selected_chat_label=st.selectbox('Select a conversation',list(chat_options),key='load_chat')
                if st.button('Open conversation',icon=':material/open_in_new:',width='stretch'):
                    chat_data=chat_options[selected_chat_label]
                    st.session_state.fitness_chat=chat_data['history']
                    st.session_state['coach_actions']={int(k):v for k,v in chat_data.get('actions',{}).items()}
                    st.rerun()
        if st.button('New conversation',key='reset_chat',icon=':material/add_comment:',type='tertiary'):
            st.session_state.fitness_chat=[]
            st.session_state['coach_actions']={}
            st.rerun()

def adoption_actions(content,index,action):
    if action not in ('training_plan','nutrition_plan','exercise'):
        return
    if action == 'exercise':
        with st.expander('Add exercise to my training plan',icon=':material/add_circle:'):
            plans=records('training_plan')
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
                    save('training_plan',date.today(),{'content':updated,'profile':active.get('profile'),'source':'coach','previous_plan_id':active['id'],'change_token':change_token,'change':{'operation':operation,'day':day,'exercise':suggestion}})
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
            st.caption('Save your profile in Overview first.')
        token=hashlib.sha256((kind+content).encode()).hexdigest()
        saved=any(r.get('source_token')==token for r in records(kind))
        if st.button('Already added' if saved else label,key=f'adopt_{index}_{kind}',disabled=saved or not p,icon=':material/check:',type='primary'):
            save(kind,date.today(),{'content':content,'profile':p,'source':'coach','source_token':token})
            st.rerun()

if not st.session_state.fitness_chat:
    with st.container(border=True,horizontal_alignment='center'):
        st.subheader('What would you like to achieve today?',icon=':material/auto_awesome:',anchor=False)
        st.caption('Ask about training or nutrition, or create a personalized plan.')

for index,(role,content) in enumerate(st.session_state.fitness_chat):
    with st.chat_message(role):
        st.markdown(content)
        if role=='assistant':
            previous=st.session_state.fitness_chat[index-1][1] if index else ''
            # Revalidate visible content, including restored conversations. Cached labels
            # from older sessions must never force an irrelevant adoption action.
            action=detect_action(previous,content)
            adoption_actions(content,index,action)
question=st.chat_input('Message your coach …',max_chars=4000)
if question:
    with st.chat_message('user'):
        st.markdown(question)
    try:
        plan=mode!='Ask a question' or 'plan' in question.lower()
        request=question
        if mode=='Create training plan':
            request='Create a complete, compact training plan with exercises, sets, reps, and rest periods tailored to the profile. Request: '+question
        elif mode=='Create meal plan':
            request='Create a complete, compact meal plan with portions and estimated nutrition values tailored to the profile. Strictly follow allergies. Request: '+question
        targets=records('nutrition_targets')
        context=dict(p or {})
        weights=records('weight')
        if weights:
            context['Current weight (kg)']=weights[-1]['kg']
        if targets:
            context['Self-defined nutrition targets']={k:v for k,v in targets[-1].items() if k not in ('id','day')}
        with st.chat_message('assistant'):
            status=st.empty()
            status.caption('Coach is starting … the response will appear as it is written.')
            def chunks():
                for chunk in stream_coach(st.session_state['fitness_text_model'],context,st.session_state.fitness_chat,request,plan=plan):
                    status.empty()
                    yield chunk
            answer=st.write_stream(chunks())
        index=len(st.session_state.fitness_chat)+1
        st.session_state.setdefault('coach_actions',{})[index]=detect_action(question,answer,mode)
        st.session_state.fitness_chat.extend([('user',question),('assistant',answer)])
        save('coach_chat', date.today(), {'history': st.session_state.fitness_chat, 'actions': st.session_state.get('coach_actions', {})})
        st.rerun()
    except Exception as exc:
        if 'status' in locals():
            status.empty()
        st.error(f'Coach unavailable: {exc}. Please try again.')
