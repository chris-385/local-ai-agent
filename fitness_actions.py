"""Conservative action detection and versioned changes to Markdown plans."""
import re


def exercise_lines(content):
    """Offer concrete exercise prescriptions or named exercises in lists."""
    result=[]
    for line in content.splitlines():
        text=line.strip()
        if text and not text.startswith('#') and re.search(r'\d+\s*(?:[x×]|Sätze|Saetze|sets|Wiederholungen|reps)',text,re.I):
            result.append(text)
        elif re.match(r'^(?:[-*•]|\d+[.)])\s+',text) and re.search(r'Kniebeuge|Bankdrück|Bankdrueck|Liegestütz|Liegestuetz|Latzieh|Klimmzug|Rudern|Kreuzheb|Ausfallschritt|Beinpresse|Schulterdrück|Seitheben|Squats?|Bench press|Push-?ups?|Lat pull|Pull-?ups?|Rows?|Deadlifts?|Lunges?|Leg press|Shoulder press|Lateral raises?|Curls?|Plank|Dips',text,re.I):
            result.append(text)
        elif text.startswith('|') and len(re.findall(r'\d+',text))>=2 and not re.search(r'kcal|Kalorien|Protein',text,re.I):
            result.append(text)
    return list(dict.fromkeys(result))


def detect_action(question,answer,mode='Ask a question'):
    if not answer.strip() or re.search(r'Antwortlimit erreicht|Response limit reached',answer,re.I):
        return None
    # A request or a mentioned plan alone is insufficient: require concrete content.
    food = bool(re.search(r'Frühstück|Mittagessen|Abendessen|Snack|breakfast|lunch|dinner',answer,re.I))
    portions = bool(re.search(r'\d+\s*(?:g\b|kcal|Kalorien|ml\b)',answer,re.I))
    training = exercise_lines(answer)
    plan_intent = bool(re.search(r'plan|Trainingswoche|Wochenübersicht|training week|weekly overview',question,re.I))
    food_intent = bool(re.search(r'ernähr|ernaehr|essen|mahlzeit|nutrition|meal|diet',question,re.I))
    food_proposal = bool(re.search(r'(?:hier|dein|vorschlag|here|your|suggestion|#).*?(?:ernährungsplan|ernaehrungsplan|meal plan)',answer,re.I))
    training_proposal = bool(re.search(r'(?:hier|dein|vorschlag|here|your|suggestion|#).*?(?:trainingsplan|training plan|workout plan)',answer,re.I))
    exercise_intent = bool(re.search(r'übung|uebung|exercise|Brust|Rücken|Ruecken|Schulter|Bizeps|Trizeps|Beine|Muskel|Trainingstag|chest|back|shoulder|biceps|triceps|legs|muscle|training day',question,re.I))
    full_plan_request = bool(re.search(r'(?:erstelle|mach|gib|erstell|create|make|give|ganzen|kompletten|vollständigen|complete|full).*?(?:trainingsplan|training plan|workout plan|wochenplan)',question,re.I))
    if training and exercise_intent and not full_plan_request and not training_proposal and not food_proposal:
        return 'exercise'
    if food and portions and ((plan_intent and food_intent) or food_proposal or mode in ('Ernährungsplan erstellen','Create meal plan')):
        return 'nutrition_plan'
    if training and ((plan_intent and not food_intent) or training_proposal or mode in ('Trainingsplan erstellen','Create training plan')):
        return 'training_plan'
    exercise_intent = bool(re.search(r'übung|uebung|exercise|Brust|Rücken|Ruecken|Schulter|Bizeps|Trizeps|Beine|Muskel|Trainingstag|chest|back|shoulder|biceps|triceps|legs|muscle|training day',question,re.I))
    if training and exercise_intent:
        return 'exercise'
    return None


def change_exercise(content,suggestion,day,replace=None):
    if not suggestion.strip() or not day.strip():
        raise ValueError('Please enter an exercise and training day.')
    if replace is not None:
        lines=content.splitlines()
        matches=[i for i,line in enumerate(lines) if line.strip()==replace.strip()]
        if len(matches)!=1:
            raise ValueError('The selected exercise is not unique. Please review the plan.')
        lines[matches[0]]=suggestion.strip()
        return '\n'.join(lines)
    # Insert under an existing matching heading; other Markdown plans get an explicit addendum.
    lines=content.splitlines()
    for i,line in enumerate(lines):
        if line.lstrip().startswith('#') and day.casefold() in line.casefold():
            end=next((j for j in range(i+1,len(lines)) if lines[j].lstrip().startswith('#')),len(lines))
            lines[end:end]=['',suggestion.strip(),'']
            return '\n'.join(lines)
    return content.rstrip()+f'\n\n### Addition: {day.strip()}\n{suggestion.strip()}\n'
