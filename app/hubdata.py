"""Static content for recruiter campaigns and skill tests. No AI, no network."""
import random

# Extra role pools (question, key points a good answer touches). The BPO, hotel, cabin crew, airport and
# data-entry pools come from basic_in_data; general questions are shared by all.
EXTRA_ROLES = {
    "sales": ("Sales / Retail Executive", [
        ("How would you greet a customer who walks into the shop?", "smile greet welcome help ask need friendly"),
        ("A customer says your product is too expensive. What do you say?", "value quality listen benefit offer alternative budget"),
        ("How do you reach a monthly sales target?", "plan target daily follow up customers track"),
        ("Tell me about a time you convinced someone to buy or agree.", "listened example benefit result trust"),
        ("How do you handle a customer who is only browsing?", "polite space help available question"),
        ("What would you do if a customer wants an item that is out of stock?", "check alternative order inform sorry notify"),
        ("Why do you want to work in sales?", "people communication target growth learn"),
    ]),
    "itsupport": ("IT Support / Helpdesk", [
        ("A user says their computer is not starting. What do you check first?", "power cable battery restart check ask error"),
        ("How do you explain a technical problem to a non-technical person?", "simple words patient example steps"),
        ("What is the difference between hardware and software?", "physical parts programs examples"),
        ("A user forgot their password. What is the safe way to help?", "verify identity reset policy secure"),
        ("How do you prioritise when five users report problems at once?", "urgent impact queue ticket communicate"),
        ("Which operating systems and tools have you used?", "windows tools installed learned practice"),
        ("Why do you want a helpdesk job?", "problem solving learn technology help people"),
    ]),
    "accounts": ("Accounts / Finance Assistant", [
        ("What accounting software or tools have you used?", "tally excel software entries practice"),
        ("What is the difference between debit and credit?", "debit credit entry account increase decrease"),
        ("How do you make sure your data entry is accurate?", "check verify double review reconcile careful"),
        ("What would you do if the totals do not match?", "recheck entries find difference reconcile ask"),
        ("What is GST in simple words?", "tax goods services collected government"),
        ("How do you handle confidential financial information?", "confidential access policy share trust"),
        ("Why accounts as a career?", "numbers accuracy interest growth learn"),
    ]),
    "driver": ("Driver / Logistics", [
        ("How many years of driving experience do you have, and on which vehicles?", "years vehicle licence routes experience"),
        ("What do you check before starting a trip?", "tyres fuel brakes lights documents oil"),
        ("What would you do if the vehicle breaks down on the road?", "safe side hazard call inform support"),
        ("How do you handle heavy traffic or a delay?", "calm inform customer alternate route safe"),
        ("What traffic rules matter most to you and why?", "speed seat belt signal safety licence"),
        ("A customer is rude about a late delivery. What do you do?", "polite apologise explain reason inform"),
        ("Have you ever had an accident or fine? What did you learn?", "honest learned careful safety"),
    ]),
    "admin": ("Admin / Office Assistant", [
        ("What office tasks have you done before?", "filing data entry calls emails records"),
        ("How do you organise your day when many tasks come together?", "list priority deadline schedule urgent"),
        ("How comfortable are you with Excel, Word and email?", "excel word email typing practice"),
        ("A senior asks for a document you cannot find. What do you do?", "search ask inform sorry alternative"),
        ("How do you keep records safe and in order?", "label file backup confidential system"),
        ("How would you welcome a visitor at the office?", "greet smile ask purpose inform host seat"),
        ("Why do you want an admin role?", "organised support team learn reliable"),
    ]),
}

POOL_LABELS = {
    "bpo": "BPO / Call Centre", "hotel": "Hotel & Hospitality", "cabin": "Cabin Crew / Air Hostess",
    "airport": "Airport Ground Staff", "dataentry": "Data Entry / Back Office",
    **{k: v[0] for k, v in EXTRA_ROLES.items()},
}

MODULE_LABELS = {"voice": "Voice interview", "typing": "Typing test", "reading": "Reading aloud",
                 "quiz": "English and customer-scenario quiz", "aptitude": "Aptitude (numbers, logic, data checking)"}

TYPING = [
    "Thank you for calling. My name is Riya and I will be happy to help you today. Please share your order number so that I can check the status for you.",
    "We are sorry for the delay in delivery. Your parcel has reached the local hub and will be delivered by tomorrow evening. You will get a message before the delivery.",
    "Good morning and welcome to our hotel. Your room is ready on the third floor. Breakfast is served from seven to ten in the main restaurant. Please call us if you need anything.",
    "Please keep your seat belt fastened while the sign is on. Our crew will serve snacks and drinks soon. If you need help, press the call button above your seat.",
]
READING = [
    "Good afternoon. Thank you for waiting. I understand that your internet has not been working since yesterday. I have raised a request and an engineer will visit you tomorrow between ten and twelve.",
    "Welcome aboard. We will be flying for about two hours. Please keep your bags under the seat in front of you. We wish you a pleasant journey.",
    "Hello, this is a reminder that your appointment is on Friday at four in the afternoon. Please bring your identity card. If you cannot come, call us to choose a new time.",
]
QUIZ = [
    {"q": "She ___ to the office every day.", "o": ["go", "goes", "going", "gone"], "a": 1},
    {"q": "I have worked here ___ 2021.", "o": ["for", "since", "from", "during"], "a": 1},
    {"q": "Please ___ me your email address.", "o": ["tell", "say", "speak", "talk"], "a": 0},
    {"q": "Which sentence is correct?", "o": ["He don't know the answer.", "He doesn't know the answer.", "He not know the answer.", "He didn't knows the answer."], "a": 1},
    {"q": "We ___ your order yesterday.", "o": ["ship", "shipped", "shipping", "ships"], "a": 1},
    {"q": "I would like ___ information about the plan.", "o": ["a", "an", "some", "many"], "a": 2},
    {"q": "Can you speak ___, please? I cannot hear you.", "o": ["loud", "loudly", "louder", "more loud"], "a": 2},
    {"q": "\"Please hold the line\" means:", "o": ["wait on the call", "hang up", "call again later", "speak louder"], "a": 0},
    {"q": "A customer shouts that the parcel is late. Best first reply?", "o": ["Calm down, it is not my fault.", "I am sorry for the delay. Let me check your order now.", "Please call tomorrow.", "That is the courier's problem."], "a": 1},
    {"q": "You do not know the answer to a customer's question. Best reply?", "o": ["Guess an answer.", "Say I do not know and end the call.", "Let me check and confirm. May I put you on a short hold?", "Transfer the call without telling the customer."], "a": 2},
    {"q": "A customer asks for a refund outside the policy. Best reply?", "o": ["Promise the refund anyway.", "Explain the policy politely and offer what you can do, like a replacement or escalation.", "Say no and hang up.", "Argue until they agree."], "a": 1},
    {"q": "Before ending a call you should:", "o": ["Confirm the issue is solved and thank the customer.", "Hang up quickly.", "Ask them to call back.", "Change the topic."], "a": 0},
    {"q": "A customer reads out their bank OTP on the call by mistake. You:", "o": ["Write it down.", "Tell them not to share it and follow the company security process.", "Ask them to repeat it.", "Use it to fix the problem."], "a": 1},
    {"q": "You make a mistake on a customer's order. You:", "o": ["Hide it.", "Tell the customer and your team lead, and fix it.", "Blame the system.", "Ignore it."], "a": 1},
]
LOGIC = [
    {"q": "Series: 2, 4, 8, 16, ?", "o": ["24", "30", "32", "36"], "a": 2},
    {"q": "All roses are flowers. Some flowers fade quickly. Which is certainly true?", "o": ["All roses fade quickly", "All roses are flowers", "No flower fades quickly", "Only roses are flowers"], "a": 1},
    {"q": "Odd one out: Tuesday, Friday, June, Monday", "o": ["Tuesday", "Friday", "June", "Monday"], "a": 2},
    {"q": "A is taller than B, and B is taller than C. Who is the shortest?", "o": ["A", "B", "C", "Cannot say"], "a": 2},
    {"q": "A shop opens at 9 am and closes at 6 pm. How many hours is it open?", "o": ["8", "9", "10", "7"], "a": 1},
    {"q": "Series: 5, 10, 15, 20, ?", "o": ["25", "30", "24", "35"], "a": 0},
]


def _opts(rng, correct, spread):
    s = {correct}
    while len(s) < 4:
        s.add(max(0, correct + rng.choice([-1, 1]) * rng.randint(1, spread)))
    o = sorted(s)
    rng.shuffle(o)
    return [str(x) for x in o], o.index(correct)


def aptitude(seed: int) -> list[dict]:
    """Numerical and data-check items are generated from a seed, so every candidate gets different numbers."""
    rng = random.Random(seed)
    items = []
    p = rng.choice([10, 15, 20, 25]); base = rng.choice([120, 160, 240, 320, 400])
    o, a = _opts(rng, base * p // 100, 12); items.append({"q": f"What is {p}% of {base}?", "o": o, "a": a})
    x, y = rng.randint(120, 480), rng.randint(120, 480)
    o, a = _opts(rng, x + y, 20); items.append({"q": f"{x} + {y} = ?", "o": o, "a": a})
    bill = rng.choice([450, 780, 920, 1260]); paid = bill + rng.choice([40, 120, 240, 540])
    o, a = _opts(rng, paid - bill, 30); items.append({"q": f"A bill is Rs {bill}. The customer pays Rs {paid}. How much change do you return?", "o": o, "a": a})
    m, n = rng.randint(12, 48), rng.randint(3, 9)
    o, a = _opts(rng, m * n, 15); items.append({"q": f"{m} x {n} = ?", "o": o, "a": a})
    tot = rng.choice([60, 80, 120]); part = rng.choice([2, 3, 4, 5])
    o, a = _opts(rng, tot // part, 8); items.append({"q": f"{tot} sweets are shared equally among {part} people. How many does each get?", "o": o, "a": a})
    for q in rng.sample(LOGIC, 4):
        items.append(dict(q))
    for _ in range(3):
        d = "".join(rng.choice("0123456789") for _ in range(7))
        pre = rng.choice(["AC", "ID", "PO", "TX"])
        left = f"{pre}-{d[:4]}-{d[4:]}"
        same = rng.random() < 0.5
        right = left
        if not same:
            i = rng.choice([i for i, c in enumerate(left) if c.isdigit()])
            right = left[:i] + str((int(left[i]) + rng.randint(1, 8)) % 10) + left[i + 1:]
        items.append({"q": f"Are these two numbers exactly the same?  {left}   and   {right}", "o": ["Same", "Different"], "a": 0 if same else 1})
    return items
