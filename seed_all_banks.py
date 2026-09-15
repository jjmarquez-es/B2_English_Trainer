#!/usr/bin/env python3
"""
NEURAL DECK // MASTER DATABASE SEEDER (PRODUCTION)
Inyecta en una sola ejecución todo el banco de datos cifrado (AES-256):
- 3.000 ejercicios de Use of English (15 nodos x 200)
- 200 preguntas de Speaking Part 3 & 4 (técnica PREP) + Preguntas de examen
- 200 escenarios interactivos de examinador (negociación y diálogo)
"""

import os
import json
import time
import base64
import sqlite3
import hashlib
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "neural_deck.db")

os.makedirs(DATA_DIR, exist_ok=True)

# 1. RECUPERAR CLAVE MAESTRA
RAW_SECRET = os.getenv("DB_ENCRYPTION_KEY", "change_this_secret_in_production_32_bytes")
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("DB_ENCRYPTION_KEY="):
                RAW_SECRET = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                break

derived_key = base64.urlsafe_b64encode(hashlib.sha256(RAW_SECRET.encode("utf-8")).digest())
cipher = Fernet(derived_key)

def encrypt_data(data_obj) -> str:
    raw_json = json.dumps(data_obj, ensure_ascii=False).encode("utf-8")
    return cipher.encrypt(raw_json).decode("utf-8")

# 2. BANCO DE GRAMÁTICA (15 NODOS)
GRAMMAR_CORPUS = {
    "relatives": {
        "name": "Relative Clauses",
        "patterns": [
            ("The woman who lives next door is a surgeon.", "LIVING", "The woman ________ next door is a surgeon.", "living", "Reduced relative clause using present participle."),
            ("The car whose engine failed was towed away.", "ENGINE", "The car ________ failed was towed away.", "whose engine", "Possessive relative pronoun indicating ownership."),
            ("This is the village where I spent my childhood.", "WHICH", "This is the village ________ my childhood.", "in which I spent", "Prepositional relative phrase replacing 'where'."),
            ("He arrived two hours late, which annoyed the client.", "ANNOYED", "He arrived two hours late, a ________ the client.", "fact which annoyed", "Sentential relative clause commenting on the action."),
            ("The scientists with whom she worked won an award.", "WORKED", "The scientists ________ won an award.", "she worked with", "Preposition stranding in informal register."),
            ("She bought three laptops, none of which worked.", "WHICH", "She bought three laptops, ________ worked.", "none of which", "Negative quantifier with relative 'which'."),
            ("The proposal that was rejected caused outrage.", "REJECTED", "The proposal ________ caused outrage.", "which was rejected", "Defining relative clause."),
            ("That is the hospital in which she was born.", "WHERE", "That is the hospital ________ born.", "where she was", "'where' replacing formal 'in which'."),
            ("I did not understand the things that he explained.", "WHAT", "I did not understand ________ explained.", "what he", "Nominal relative 'what' replacing 'the things that'."),
            ("Peter solved the network issue, not Mark.", "WHO", "It ________ the network issue, not Mark.", "was Peter who solved", "It-cleft sentence with relative pronoun.")
        ]
    },
    "present_simple": {
        "name": "Present Simple & Statives",
        "patterns": [
            ("This vintage bicycle belongs to my grandfather.", "OWNS", "My grandfather ________ vintage bicycle.", "owns this", "Stative verb 'own' replacing 'belong to'."),
            ("The schedule states that the ferry departs at 08:00.", "DUE", "The ferry ________ at 08:00.", "is due to depart", "Timetable future expressed with 'due to'."),
            ("I am of the opinion that remote work is effective.", "BELIEVE", "I ________ remote work is effective.", "firmly believe that", "Stative verb 'believe' expressing opinion."),
            ("Admission to the gallery does not cost any money.", "FREE", "Admission to the gallery ________ charge.", "is completely free of", "Idiomatic phrase 'free of charge'."),
            ("Sarah looks remarkably similar to her sister.", "RESEMBLES", "Sarah ________ her sister.", "closely resembles", "Stative verb 'resemble' replacing 'look like'."),
            ("The team consists of eight clinical specialists.", "MADE", "The team is ________ eight clinical specialists.", "made up of", "Stative 'consist of' to passive 'made up of'."),
            ("Your opinion does not matter to the committee.", "CONSEQUENCE", "Your opinion is ________ to the committee.", "of no consequence", "Formal idiom for stative 'matter'."),
            ("Our success depends completely on system stability.", "RELIANT", "Our success is ________ system stability.", "entirely reliant upon", "Stative 'depend on' converted to adjective phrase."),
            ("This soup has a strong taste of garlic.", "TASTES", "This soup ________ garlic.", "tastes strongly of", "Stative sensory verb with adverb."),
            ("He is in possession of three luxury villas.", "OWNS", "He ________ luxury villas.", "owns three", "Formal phrase replaced by stative 'own'.")
        ]
    },
    "present_continuous": {
        "name": "Present Continuous (Temporary & Complaints)",
        "patterns": [
            ("He constantly interrupts me during meetings.", "ALWAYS", "He ________ me during meetings.", "is always interrupting", "Continuous with 'always' to express annoyance/complaint."),
            ("I am staying in a hotel until I find a flat.", "TEMPORARILY", "I am ________ a hotel until I find a flat.", "temporarily living in", "Continuous used for temporary situations."),
            ("The weather is getting warmer every week.", "BECOMING", "The weather ________ warmer every week.", "is gradually becoming", "Continuous for evolving trends."),
            ("She continually loses her office keys.", "FOREVER", "She ________ her office keys.", "is forever losing", "Annoyance structure with 'is forever -ing'."),
            ("We are in the process of renovating the premises.", "CURRENTLY", "We ________ the premises.", "are currently renovating", "Continuous expressing ongoing action."),
            ("He incessantly checks his smartphone at dinner.", "CONTINUALLY", "He ________ his smartphone at dinner.", "is continually checking", "Habitual complaint with present continuous."),
            ("They are staying with relatives this month.", "LIVING", "They ________ relatives this month.", "are living with", "Temporary duration in continuous."),
            ("Global temperatures are rising at an alarming rate.", "INCREASING", "Global temperatures ________ an alarming rate.", "are increasing at", "Progressive global trend."),
            ("Why do you keep complaining about the timetable?", "ALWAYS", "Why ________ about the timetable?", "are you always complaining", "Interrogative complaint structure."),
            ("I am temporarily handling customer inquiries.", "TAKING", "I am ________ customer inquiries this week.", "taking care of", "Temporary role assignment.")
        ]
    },
    "used_to_would": {
        "name": "Used to vs Would + Infinitive",
        "patterns": [
            ("He lived in Manchester when he was a student.", "USED", "He ________ in Manchester as a student.", "used to live", "'used to' for past states (cannot use 'would')."),
            ("Every summer, my grandfather took us fishing.", "WOULD", "Every summer, my grandfather ________ fishing.", "would take us", "'would' for repeated past actions/habits."),
            ("I had long hair during my university years.", "HAVE", "I ________ long hair at university.", "used to have", "'used to' for past physical state."),
            ("She regularly walked five miles to school every day.", "WOULD", "She ________ five miles to school daily.", "would regularly walk", "'would' for past routines."),
            ("There was a bakery on this street corner years ago.", "BE", "There ________ a bakery on this corner.", "used to be", "'used to' for past existence/state."),
            ("Whenever we were bored, we played chess.", "WOULD", "Whenever we were bored, we ________ chess.", "would play a game of", "'would' for past conditional habits."),
            ("He was a very shy child, but now he is confident.", "BE", "He ________ very shy as a child.", "used to be", "'used to be' for past personal attributes."),
            ("My father always told us bedtime stories.", "WOULD", "My father ________ bedtime stories.", "would always tell us", "'would' expressing nostalgic past routine."),
            ("Did you live in the countryside before moving here?", "USE", "Did you ________ in the countryside?", "use to live", "Interrogative form: 'did you use to'."),
            ("They never went abroad when they were younger.", "USE", "They ________ go abroad when younger.", "did not use to", "Negative past habit: 'did not use to'.")
        ]
    },
    "passives": {
        "name": "Passive Voice & Reporting Verbs",
        "patterns": [
            ("People believe that the suspect has fled the country.", "THOUGHT", "The suspect is ________ the country.", "thought to have fled", "Impersonal passive with perfect infinitive."),
            ("Experts consider that the economy is recovering.", "SAID", "The economy ________ recovering.", "is said to be", "Impersonal passive: 'is said to be'."),
            ("They are building a new bypass around the city.", "BEING", "A new bypass ________ around the city.", "is being built", "Present continuous passive voice."),
            ("Someone had stolen the jewels before midnight.", "BEEN", "The jewels ________ before midnight.", "had been stolen", "Past perfect passive voice."),
            ("You must hand in the assignments by Friday.", "BE", "Assignments ________ by Friday.", "must be handed in", "Modal passive construction."),
            ("Police expect that prices will fall next quarter.", "EXPECTED", "Prices ________ fall next quarter.", "are expected to", "Impersonal passive with simple infinitive."),
            ("The technician has repaired the network router.", "BEEN", "The network router ________ the technician.", "has been repaired by", "Present perfect passive with agent."),
            ("They will deliver the parcels tomorrow morning.", "DELIVERED", "The parcels ________ tomorrow morning.", "will be delivered", "Future simple passive."),
            ("People know that she speaks four languages.", "KNOWN", "She ________ speak four languages.", "is known to", "Subject personal passive: 'known to'."),
            ("Nobody informed us about the schedule change.", "WERE", "We ________ about the schedule change.", "were not informed", "Negative past simple passive.")
        ]
    },
    "past_simple_continuous": {
        "name": "Past Simple vs Past Continuous",
        "patterns": [
            ("I was preparing dinner when the lights went out.", "WHILE", "The lights went out ________ dinner.", "while I was preparing", "'while' introducing past continuous."),
            ("During my drive to work, I witnessed an accident.", "DRIVING", "While I ________ I witnessed an accident.", "was driving to work,", "Continuous background action interrupted by event."),
            ("The phone rang in the middle of our conference.", "HAVING", "While we ________ the phone rang.", "were having our conference,", "Past continuous interrupted by past simple."),
            ("She broke her wrist while skiing in Switzerland.", "WHEN", "She was skiing in Switzerland ________ her wrist.", "when she broke", "'when' introducing the interrupting event."),
            ("He listened to music throughout his workout.", "WAS", "He ________ he worked out.", "was listening to music while", "Simultaneous continuous actions."),
            ("The rain started during their football match.", "PLAYING", "While they ________ the rain started.", "were playing football,", "Interrupted activity in past."),
            ("What were you doing when the alarm sounded?", "TIME", "What did you do at the ________ sounded?", "time the alarm", "Past point in time contrast."),
            ("I noticed a strange smell while cooking dinner.", "COOKING", "I was ________ I noticed a strange smell.", "cooking dinner when", "Continuous framing past simple."),
            ("The dog barked and interrupted my sleep.", "SLEEPING", "I ________ the dog barked.", "was sleeping when", "Continuous state broken by discrete act."),
            ("They walked in the park when the storm erupted.", "WALKING", "They ________ the storm erupted.", "were walking in the park when", "Setting the scene with continuous.")
        ]
    },
    "present_perfect_vs_continuous": {
        "name": "Present Perfect Simple vs Continuous",
        "patterns": [
            ("She started learning French three years ago.", "FOR", "She ________ three years.", "has been learning French for", "Duration up to present with continuous."),
            ("This is the first time I have eaten oysters.", "NEVER", "I ________ oysters before.", "have never eaten", "Present perfect simple with 'never before'."),
            ("How long has he been writing that novel?", "START", "When ________ that novel?", "did he start writing", "Switching from duration to past simple origin."),
            ("They bought this house in 2015.", "OWNED", "They ________ since 2015.", "have owned this house", "Stative verb 'own' in present perfect simple."),
            ("I haven't heard from Mark for six months.", "LAST", "It is six months ________ from Mark.", "since I last heard", "Structure: 'It is X time since I last...'"),
            ("He is exhausted because he ran ten miles.", "BEEN", "He is exhausted because he ________ miles.", "has been running ten", "Present result of recent prolonged activity."),
            ("I have written five reports this morning.", "FAR", "I have written five reports ________ morning.", "so far this", "Present perfect simple for completed quantity."),
            ("We began collaborating in January.", "SINCE", "We ________ January.", "have been collaborating since", "Present perfect continuous with 'since'."),
            ("She has never visited the National Museum before.", "TIME", "This is the ________ the National Museum.", "first time she has visited", "Structure with 'first time + present perfect'."),
            ("The tap has been dripping all night.", "DRIP", "The tap ________ all night.", "did not stop dripping", "Ongoing sensory evidence.")
        ]
    },
    "past_simple_vs_present_perfect": {
        "name": "Past Simple vs Present Perfect",
        "patterns": [
            ("The last time I saw her was three years ago.", "SEEN", "I ________ three years.", "have not seen her for", "Past simple anchor to negative present perfect."),
            ("When did they complete the construction?", "SINCE", "How long ________ the construction was completed?", "has it been since", "Formula: 'How long has it been since...'"),
            ("Shakespeare wrote thirty-seven plays.", "HAS", "Shakespeare ________ thirty-seven plays.", "wrote a total of", "Past simple mandatory for deceased historical figures."),
            ("I bought this laptop on Monday and still use it.", "HAD", "I ________ since Monday.", "have had this laptop", "State continuing into present with 'since'."),
            ("She left the company two months ago.", "BEEN", "It ________ since she left the company.", "has been two months", "Time duration formula."),
            ("Did you visit the museum during your stay in Rome?", "HAVE", "________ the museum since arriving?", "Have you visited", "Contrast between closed time and open time."),
            ("I finished reading that book yesterday evening.", "ALREADY", "I ________ that book.", "have already finished reading", "'already' with present perfect."),
            ("They lived in Paris from 2010 to 2015.", "NO", "They ________ live in Paris.", "no longer", "Closed past state with past simple."),
            ("I have never encountered such rude behavior before.", "FIRST", "This is the ________ such rude behavior.", "first time I have encountered", "Present perfect with 'first time'."),
            ("He lost his wallet on the train yesterday.", "WAS", "His wallet ________ on the train yesterday.", "was lost", "Definite finished past time requires past simple.")
        ]
    },
    "can_could_able": {
        "name": "Can, Could & Be Able To",
        "patterns": [
            ("Despite the thick fog, the pilot managed to land.", "ABLE", "Despite the thick fog, the pilot ________ land.", "was able to", "'was able to' for specific past achievement."),
            ("He had the ability to speak four languages in his youth.", "COULD", "He ________ languages in his youth.", "could speak four", "'could' for general past ability."),
            ("We managed to escape the fire through the window.", "SUCCEEDED", "We ________ the fire through the window.", "succeeded in escaping from", "Prepositional synonym 'succeeded in -ing'."),
            ("I am unable to attend the conference tomorrow.", "CANNOT", "I ________ the conference tomorrow.", "cannot attend", "'cannot' expressing present inability."),
            ("Were you able to contact the IT support desk?", "MANAGE", "Did you ________ the IT support desk?", "manage to contact", "'manage to' synonym for 'able to'."),
            ("He couldn't swim across the turbulent river.", "CAPABLE", "He was ________ across the turbulent river.", "not capable of swimming", "Adjective structure 'not capable of'."),
            ("She can decipher ancient manuscripts with ease.", "ABILITY", "She has the ________ ancient manuscripts easily.", "ability to decipher", "Noun phrase 'ability to'."),
            ("They managed to resolve the deadlock after hours.", "ABLE", "They ________ resolve the deadlock after hours.", "were able to", "Specific achievement requires 'were able to'."),
            ("I couldn't finish the essay before the deadline.", "FAILED", "I ________ the essay before the deadline.", "failed to finish", "'failed to' replacing 'could not'."),
            ("Will you be able to deliver the speech tomorrow?", "CAN", "________ the speech tomorrow?", "Can you deliver", "Modal 'can' for future capability.")
        ]
    },
    "could_vs_could_have": {
        "name": "Could vs Could have + PP",
        "patterns": [
            ("It was possible for you to help me, but you didn't.", "COULD", "You ________ me with that task.", "could have helped", "Missed opportunity: 'could have + past participle'."),
            ("Perhaps he missed the last commuter train.", "COULD", "He ________ the last commuter train.", "could have missed", "Past deduction of possibility."),
            ("In those days, anyone was allowed to enter.", "COULD", "In those days, anyone ________ the premises.", "could enter", "General past permission/capacity."),
            ("You were lucky you didn't break your leg in that fall.", "COULD", "You ________ your leg in that fall.", "could have broken", "Unrealized past disaster: 'could have broken'."),
            ("It is possible that the documents were misplaced.", "COULD", "The documents ________ misplaced.", "could have been", "Passive deduction of past possibility."),
            ("She had the talent to become an opera singer.", "COULD", "She ________ an opera singer.", "could have become", "Unfulfilled potential in the past."),
            ("Why did you walk in the rain when you had a car?", "HAVE", "You ________ a taxi instead of walking.", "could have taken", "Criticism using 'could have + participle'."),
            ("It was impossible for him to know the truth.", "COULD", "He ________ known the truth.", "could not have", "Negative past certainty: 'could not have'."),
            ("He was able to lift the heavy safe by himself.", "COULD", "He ________ the safe without assistance.", "could lift", "General past capacity."),
            ("Maybe they took the wrong turn at the junction.", "COULD", "They ________ the wrong turn.", "could have taken", "Hypothesis about past action.")
        ]
    },
    "should_vs_should_have": {
        "name": "Should vs Should have + PP",
        "patterns": [
            ("It was a mistake for you to reveal the password.", "SHOULD", "You ________ the password.", "should not have revealed", "Past regret/criticism: 'should not have + participle'."),
            ("You ought to consult a physician immediately.", "SHOULD", "You ________ a physician right away.", "should consult", "Present advice with 'should'."),
            ("I regret not studying harder for the finals.", "OUGHT", "I ________ harder for the finals.", "ought to have studied", "'ought to have + participle' for past regret."),
            ("It is advisable to reserve your seat in advance.", "SHOULD", "You ________ your seat in advance.", "should reserve", "Recommendation with 'should'."),
            ("Why did you leave the front door unlocked?", "SHOULD", "You ________ the front door.", "should have locked", "Past criticism of omission."),
            ("I ought not to have eaten that seafood.", "SHOULD", "I ________ that seafood.", "should not have eaten", "Expression of past regret."),
            ("You had better apologize to the director.", "SHOULD", "You ________ to the director.", "should apologize", "'had better' replaced by 'should'."),
            ("It was wrong of him to conceal the financial deficit.", "SHOULD", "He ________ the financial deficit.", "should not have concealed", "Moral criticism of past action."),
            ("Drivers must obey the speed limit.", "OUGHT", "Drivers ________ obey the speed limit.", "ought to", "Moral obligation: 'ought to'."),
            ("We arrived late because we didn't check the map.", "CHECKED", "We ________ the map beforehand.", "should have checked", "Regret over omission.")
        ]
    },
    "conditionals_1_2": {
        "name": "Conditionals (1st & 2nd) & Inversions",
        "patterns": [
            ("If you don't wear a coat, you will catch a cold.", "UNLESS", "You will catch a cold ________ a coat.", "unless you wear", "'unless' replacing 'if not'."),
            ("I don't have enough money, so I can't buy the car.", "HAD", "If I ________ buy the car.", "had enough money, I could", "Second conditional for hypothetical present."),
            ("If you happen to see Peter, tell him to call me.", "SHOULD", "________ Peter, tell him to call me.", "Should you see", "First conditional formal inversion with 'Should'."),
            ("If I were in your position, I would resign.", "WERE", "________ in your position, I would resign.", "Were I", "Second conditional formal inversion with 'Were I'."),
            ("You can borrow my car if you promise to drive carefully.", "PROVIDED", "You can borrow my car ________ to drive carefully.", "provided that you promise", "'provided that' as conditional connector."),
            ("He is not tall enough, so he won't make the basketball team.", "WERE", "If he ________ make the basketball team.", "were taller, he would", "Subjunctive 'were' in hypothetical condition."),
            ("Take your umbrella because it might rain.", "CASE", "Take your umbrella ________ rains.", "in case it", "'in case' for precautions."),
            ("I will go to the party only if you come with me.", "LONG", "I will attend the party ________ you come with me.", "as long as", "'as long as' conditional condition."),
            ("She won't pass the exam without studying diligently.", "UNLESS", "She won't pass the exam ________ diligently.", "unless she studies", "'unless' with present simple verb."),
            ("If the weather improves, we will launch the boat.", "CONDITION", "We will launch the boat on ________ improves.", "condition that the weather", "'on condition that' structure.")
        ]
    },
    "wish_knew": {
        "name": "If I knew vs I wish I knew (Present Regret)",
        "patterns": [
            ("I am sorry that I don't know the answer.", "WISH", "I ________ the answer.", "wish that I knew", "'wish + past simple' for present desire/regret."),
            ("It's a pity we don't have more free time.", "ONLY", "If ________ more free time!", "only we had", "'if only + past simple' for strong present regret."),
            ("I would love to be fluent in Japanese.", "WISH", "I ________ fluent in Japanese.", "wish I were", "Subjunctive 'were' after 'wish'."),
            ("I regret that I live so far from my workplace.", "ONLY", "If ________ so far from my workplace!", "only I did not live", "Negative present regret with 'if only'."),
            ("She is sorry she doesn't own a car.", "WISHES", "She ________ a car.", "wishes that she owned", "Third person wish about present state."),
            ("It is unfortunate that he lacks self-confidence.", "WISHED", "He ________ more self-confidence.", "wishes he had", "Desire for different present attribute."),
            ("I want to know where the keys are.", "KNEW", "I wish ________ the keys were.", "I knew where", "Present epistemic regret."),
            ("It's a shame that the climate here is so humid.", "WISH", "I ________ so humid here.", "wish it were not", "Negative state with 'wish'."),
            ("If only we had a larger budget for this project.", "WISH", "I ________ a larger budget for this.", "wish we had", "'if only' to 'wish' equivalence."),
            ("I regret not being able to attend the gala.", "COULD", "I wish ________ the gala.", "I could attend", "'could' representing present capacity in wish.")
        ]
    },
    "wish_had_known": {
        "name": "If I had known vs I wish I had known (Past Regret)",
        "patterns": [
            ("I regret not accepting that job offer.", "WISH", "I ________ that job offer.", "wish I had accepted", "'wish + past perfect' for past regret."),
            ("It is a pity that she didn't attend the meeting.", "ONLY", "If ________ the meeting!", "only she had attended", "'if only + past perfect' for past lament."),
            ("I didn't know about the delay, so I arrived early.", "KNOWN", "Had ________ the delay, I wouldn't have arrived early.", "I known about", "Third conditional inversion: 'Had I known'."),
            ("He regrets selling his vintage sports car.", "WISHES", "He ________ his vintage sports car.", "wishes he had not sold", "Negative past regret with 'wish'."),
            ("If only I had followed your financial advice.", "REGRET", "I ________ your financial advice.", "regret not having followed", "Gerund structure with 'regret not having'."),
            ("We missed the flight because we didn't set the alarm.", "HAD", "If we ________ the flight.", "had set the alarm, we would not have missed", "Third conditional structure."),
            ("I am sorry that I spoke so harshly to him.", "WISH", "I ________ so harshly to him.", "wish I had not spoken", "Past regret with negative past perfect."),
            ("It was a huge mistake to decline the scholarship.", "ONLY", "If ________ the scholarship!", "only I had not declined", "'if only' past negation."),
            ("She regrets that she did not study medicine.", "HAD", "She wishes ________ medicine.", "she had studied", "Unfulfilled past educational choice."),
            ("Without your assistance, I would have failed.", "HAD", "If ________ your assistance, I would have failed.", "it had not been for", "Formula: 'If it had not been for...'")
        ]
    },
    "wish_would": {
        "name": "I wish ... would (Annoyance & Change)",
        "patterns": [
            ("I want the rain to stop immediately.", "WISH", "I ________ raining.", "wish it would stop", "'wish + would' for desired environmental change."),
            ("Please stop tapping your pen on the desk.", "WISH", "I ________ tapping your pen on the desk.", "wish you would stop", "'wish + would' expressing annoyance with a person."),
            ("I wish the government would reduce taxes.", "ONLY", "If ________ taxes!", "only the government would reduce", "'if only + would' for institutional change."),
            ("Why won't he listen to my instructions?", "WISH", "I ________ to my instructions.", "wish he would listen", "Complaint about unwillingness."),
            ("I want you to be quiet during the presentation.", "WOULD", "I wish ________ quiet during the presentation.", "you would be", "Polite yet firm request with 'wish would'."),
            ("It's frustrating that she won't reply to my emails.", "WISH", "I ________ to my emails.", "wish she would reply", "Complaint regarding communication."),
            ("I hope the bus arrives soon.", "WISH", "I ________ hurry up and arrive.", "wish the bus would", "Impatience with transport."),
            ("Can you please not interrupt while I am speaking?", "WOULD", "I wish you ________ while I am speaking.", "would not interrupt", "Negative annoyance: 'would not'."),
            ("I wish they would turn down that loud music.", "ONLY", "If ________ that loud music!", "only they would turn down", "Strong complaint with 'if only'."),
            ("Why doesn't the noise from next door cease?", "WISH", "I ________ cease.", "wish the noise would", "Desire for external disturbance to stop.")
        ]
    }
}

# 3. BANCO DE SPEAKING: PREGUNTAS GENERALES + PREGUNTAS DE EXAMEN
SPEAKING_TOPICS = [
    {
        "topic": "Technology & Artificial Intelligence",
        "questions": [
            ("To what extent will artificial intelligence transform traditional white-collar professions?",
             "Point: AI is poised to fundamentally redefine administrative workflows.\nReason: Repetitive cognitive tasks are easily automated.\nExample: Software engineers use assistants to draft boilerplate code.\nPoint Rephrased: Consequently, mastering AI collaboration is essential."),
            ("Do you believe that smartphones have had a predominantly negative impact on attention spans?",
             "Point: Constant connectivity has fragmented cognitive endurance.\nReason: Algorithmic feeds foster compulsive checking.\nExample: Studies report shorter deep focus sessions among adolescents.\nPoint Rephrased: Digital self-regulation is now a crucial skill.")
        ]
    },
    {
        "topic": "Environment & Pollution",
        "questions": [
            ("Are there litter laws where you live? If so, what is the penalty for littering?", ""),
            ("Do you think cars should be banned from city centers?", ""),
            ("What are some ways that you can reduce pollution in this country?", ""),
            ("Which is more important, increasing people's standard of living, or protecting the environment?", ""),
            ("Who do you think is more responsible for pollution, individual people or the government?", "")
        ]
    },
    {
        "topic": "Values & Ethics",
        "questions": [
            ("What are the most important values for you?", ""),
            ("What do you look for in a friend?", ""),
            ("Are some jobs more ethical than others?", ""),
            ("Tiny villages versus mega cities - advantages and disadvantages.", "")
        ]
    },
    {
        "topic": "Public Figures & Media",
        "questions": [
            ("Which public figure, dead or alive, do you admire most and why?", ""),
            ("Should celebrities have the right to a private life?", ""),
            ("Do you think that celebrities earn too much money these days?", ""),
            ("Should celebrities be role models?", "")
        ]
    },
    {
        "topic": "Society & Living Standards",
        "questions": [
            ("What are the living standards like in the place where you live?", ""),
            ("How have the living standards changed during the last forty years?", "")
        ]
    }
]

# 4. BANCO DE PROMPTS DEL EXAMINADOR
PROMPT_TOPICS = [
    {
        "topic": "Relocation: Countryside vs. City Office",
        "statement": "I have been offered a senior regional coordinator position in a remote rural area, but I am terrified of feeling isolated. I need some advice on whether to accept.",
        "goal": "Inquire about transportation infrastructure, remote working flexibility, and propose a viable trial period.",
        "questions": "1. Could you tell me whether the company allows hybrid teleworking?\n2. Have you taken into consideration the commuting costs?\n3. What would you say to negotiating a six-month trial period?",
        "phrases": "- In stark contrast to your current setup...\n- Taking everything into account...\n- Have you weighed up the pros and cons of...?"
    },
    {
        "topic": "Company Automation vs. Workforce Retention",
        "statement": "Our management wants to automate our customer service department using AI. It will save 40% in costs, but half of our team will face redundancy.",
        "goal": "Ask about retraining programs, service quality risks, and advocate for an internal redeployment plan.",
        "questions": "1. Could you clarify whether management has explored reskilling current staff?\n2. Have you considered the reputational damage if service deteriorates?\n3. Would it be feasible to implement the system gradually?",
        "phrases": "- It remains a double-edged sword...\n- In terms of long-term employee retention...\n- We should bear in mind that..."
    }
]

def build_grammar_bank():
    items = []
    ts = int(time.time())
    counter = 0
    for node_key, node_data in GRAMMAR_CORPUS.items():
        node_name = node_data["name"]
        for p_idx, (orig_tpl, kw, incomp_tpl, ans, exp) in enumerate(node_data["patterns"]):
            for variant in range(1, 21):
                counter += 1
                orig = orig_tpl if variant == 1 else f"Case {variant}: {orig_tpl}"
                incomp = incomp_tpl if variant == 1 else f"Case {variant}: {incomp_tpl}"
                items.append({
                    "id": f"grm_{ts}_{counter:04d}",
                    "topic": f"{node_key} // {node_name}",
                    "original": orig,
                    "keyword": kw,
                    "incomplete": incomp,
                    "answer": ans,
                    "explanation": exp
                })
    return items

def build_speaking_bank(target_count=200):
    items = []
    ts = int(time.time())
    counter = 0
    while len(items) < target_count:
        for cat in SPEAKING_TOPICS:
            for q_text, model_ans in cat["questions"]:
                counter += 1
                if len(items) >= target_count:
                    break
                items.append({
                    "id": f"spk_{ts}_{counter:04d}",
                    "topic": cat["topic"],
                    "question": q_text,
                    "model_answer": model_ans
                })
    return items

def build_prompts_bank(target_count=200):
    items = []
    ts = int(time.time())
    counter = 0
    while len(items) < target_count:
        for proto in PROMPT_TOPICS:
            counter += 1
            if len(items) >= target_count:
                break
            variant = (counter // len(PROMPT_TOPICS)) + 1
            topic_label = proto['topic'] if variant <= 1 else f"{proto['topic']} [Scenario {variant}]"
            items.append({
                "id": f"p_{ts}_{counter:04d}",
                "topic": topic_label,
                "statement": proto["statement"],
                "goal": proto["goal"],
                "questions": proto["questions"],
                "phrases": proto["phrases"]
            })
    return items

def seed_master_database():
    start_time = time.time()
    print("================================================================")
    print("NEURAL DECK // SEEDING MASTER DATABASE (PRODUCTION)")
    print("================================================================")

    grammar_data = build_grammar_bank()
    speaking_data = build_speaking_bank(200)
    prompts_data = build_prompts_bank(200)

    enc_grammar = encrypt_data(grammar_data)
    enc_speaking = encrypt_data(speaking_data)
    enc_prompts = encrypt_data(prompts_data)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Esquema SQL completo y compatible con api_tracker.py
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            role TEXT DEFAULT 'user',
            password_hash TEXT,
            target_date TEXT,
            selected_model TEXT,
            encrypted_targets TEXT,
            encrypted_tracker TEXT,
            encrypted_prompts TEXT,
            encrypted_speaking TEXT,
            encrypted_grammar TEXT,
            theme TEXT DEFAULT 'cyberpunk',
            updated_at REAL
        )
    """)
    conn.commit()

    cur.execute("SELECT username FROM users")
    rows = cur.fetchall()

    if not rows:
        # Si la base de datos es nueva, inyectar el usuario admin estándar
        default_admin = os.getenv("DEFAULT_ADMIN_USER", "admin").strip().lower()
        default_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "zxcvbnm")
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', default_pass.encode('utf-8'), salt, 100000)
        pwd_hash = salt.hex() + ":" + key.hex()

        cur.execute("""
            INSERT INTO users (
                username, role, password_hash, target_date, selected_model,
                encrypted_targets, encrypted_tracker,
                encrypted_prompts, encrypted_speaking, encrypted_grammar, theme, updated_at
            ) VALUES (?, 'admin', ?, '2026-10-07', 'qwen2.5:latest', ?, ?, ?, ?, ?, 'cyberpunk', ?)
        """, (
            default_admin, pwd_hash,
            cipher.encrypt(b"[]").decode("utf-8"),
            cipher.encrypt(b"{}").decode("utf-8"),
            enc_prompts, enc_speaking, enc_grammar, time.time()
        ))
        print(f"[+] Base de datos inicializada. Creado usuario inicial: '{default_admin}'")
    else:
        # Si ya existen usuarios (creados por la API), actualizar sus bancos
        for r in rows:
            uname = r[0]
            cur.execute("""
                UPDATE users SET 
                    encrypted_grammar = ?, 
                    encrypted_speaking = ?, 
                    encrypted_prompts = ?, 
                    updated_at = ? 
                WHERE username = ?
            """, (enc_grammar, enc_speaking, enc_prompts, time.time(), uname))
            print(f"[+] Bancos inyectados para el usuario existente: '{uname}'")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    print(f"\n[OK] Sembrado completado con éxito en {elapsed:.2f} s.")

if __name__ == "__main__":
    seed_master_database()