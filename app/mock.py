"""Canned replies used only when NEBIUS_API_KEY is missing (offline demo / tests)."""


def reply(task: str, user: str):
    if task == "resume_review":
        return {
            "overall": "Solid base, but the resume reads like a task list. Recruiters need numbers and a clear US-market story.",
            "score": 6,
            "weaknesses": [
                {
                    "issue": "Bullets describe duties, not results",
                    "why_it_hurts": "US recruiters scan for impact. Duty lists look the same as every other candidate.",
                    "fix": "Rewrite each bullet as action + tool + measurable result, e.g. 'Cut report time 40% by automating X in Python'.",
                },
                {
                    "issue": "No clear target role or summary",
                    "why_it_hurts": "ATS and recruiters cannot tell in 6 seconds what you want.",
                    "fix": "Add a 3-line summary naming the target role, years of experience and top 4 skills.",
                },
                {
                    "issue": "Skills section is a long unsorted list",
                    "why_it_hurts": "Keyword stuffing lowers trust and hides your strongest skills.",
                    "fix": "Group skills (Languages, Cloud, Tools) and put the ones the job asks for first.",
                },
            ],
            "strengths": ["Relevant technical keywords present", "Clear work history order"],
            "rewrite_examples": [
                {"before": "Worked on testing of applications", "after": "Executed 120+ regression test cases per release in Selenium, reducing escaped defects by 25%"}
            ],
        }
    if task == "company_bank":
        return {
            "note": "Offline sample: generic questions for this role.",
            "questions": [
                {"type": "technical", "level": "medium", "question": "Walk me through the most complex system you worked on and your exact part in it.", "hint": "Scope, your decisions, result with a number."},
                {"type": "behavioral", "level": "easy", "question": "Why do you want to work here?", "hint": "Two specific reasons about the product or mission."},
                {"type": "scenario", "level": "hard", "question": "A key deliverable is at risk the day before launch. What do you do?", "hint": "Assess, communicate early, give options."},
            ],
        }
    if task == "code_eval":
        return {
            "verdict": "partially_correct", "score": 6,
            "summary": "Offline sample review. The idea is reasonable but edge cases are not handled.",
            "bugs": ["Empty input is not handled."],
            "complexity": {"time": "O(n)", "space": "O(n)", "optimal": True, "note": "Sample only."},
            "style": ["Use clearer variable names."],
            "next_step": "Trace your code on an empty input and a single element.",
            "better_approach": "",
        }
    if task == "code_hint":
        return {"hint": "Think about what you can store while scanning once so you avoid a second loop."}
    if task == "builder_parse":
        return {"name": "Jane Doe", "title": "QA Engineer", "email": "jane@example.com", "phone": "", "location": "",
                "links": [], "summary": "QA engineer with 5 years of experience.",
                "experience": [{"role": "QA Engineer", "company": "Acme Corp", "dates": "2019 - Present",
                                "bullets": ["Automated regression tests in Selenium and Java."]}],
                "education": [], "skills": ["Selenium", "Java", "API testing"], "projects": []}
    if task == "builder_polish":
        lines = [l[2:] for l in user.splitlines() if l.startswith("- ")]
        return {"bullets": ["Delivered: " + l for l in lines]}
    if task == "builder_summary":
        return {"summary": "Results-driven professional with hands-on experience in the listed tools, ready to contribute from day one."}
    if task == "prep_core":
        return {"coding": True, "focus": ["Selenium", "API testing", "CI/CD"],
                "questions": [
                    {"type": "technical", "question": "Walk me through the automation framework you built at your last job.", "model_answer": "At my last role I built a Selenium and Java framework with a Page Object structure, ran it in CI, and cut regression time by [X]%. I owned the design and onboarded two teammates.", "why_asked": "Checks real depth in your main tool."},
                    {"type": "behavioral", "question": "Tell me about a time you disagreed with a developer about a bug.", "model_answer": "Situation: a release bug was marked not-a-bug. I reproduced it, shared logs, and paired with the developer. We fixed it before release and agreed on a clearer bug template.", "why_asked": "Tests collaboration."},
                    {"type": "scenario", "question": "A client wants a release tonight but regression is failing. What do you do?", "model_answer": "I would triage failures by risk, separate flaky from real, share a clear go or no-go with data, and offer a safe partial release.", "why_asked": "Tests judgment under pressure."},
                ]}
    if task == "prep_code":
        return {"coding_questions": [
            {"title": "Two Sum", "level": "easy", "problem": "Return indices of two numbers adding to a target. Example: [2,7,11], 9 -> [0,1].", "approach": "Scan once, keep a map of seen numbers.", "solution": "def solve(nums, t):\n    seen = {}\n    for i, n in enumerate(nums):\n        if t - n in seen:\n            return [seen[t - n], i]\n        seen[n] = i", "language": "Python", "complexity": "O(n) time, O(n) space"}]}
    if task == "questions":
        return {
            "questions": [
                {"type": "technical", "question": "Walk me through a project where you used the main tool listed on your resume. What was your exact role?"},
                {"type": "technical", "question": "How do you debug a failing job in production when logs are incomplete?"},
                {"type": "behavioral", "question": "Tell me about a time you disagreed with a teammate. What did you do and what was the result?"},
                {"type": "scenario", "question": "A US client asks for a change at 5pm their time that affects tomorrow's release. How do you respond?"},
                {"type": "behavioral", "question": "Describe a deadline you almost missed. How did you recover?"},
            ]
        }
    if task == "turn":
        return {
            "scores": {"clarity": 3, "depth": 3, "correctness": 4, "star": 2},
            "feedback": "You gave a correct answer but stayed general. Add one concrete example with numbers.",
            "stronger_answer": "In my last project I owned the regression suite for a payments app. I automated 80 critical flows in Selenium, which cut release testing from 3 days to 1 and caught 12 defects before production.",
            "tips": ["Lead with the result, then explain how.", "Use 'I' not 'we' so the interviewer hears your contribution."],
            "communication": {
                "fluency": 4,
                "tone": "calm and professional",
                "language_notes": ["Say 'I automated' instead of 'I have done automation'."],
                "tip": "Pause for a second before the result so the client hears the key number.",
            },
            "followup": "What was the hardest part of that, and what would you do differently now?",
        }
    if task == "report":
        return {
            "overall_score": 3.4,
            "summary": "Good technical base. Answers need more concrete examples, numbers and STAR structure.",
            "communication_summary": "Clear and calm. Reduce filler words and lead with the result.",
            "strengths": ["Correct technical understanding", "Calm, professional tone"],
            "gaps": ["Few measurable results", "Behavioral answers lack a clear Situation/Result"],
            "plan_7_days": [
                {"day": 1, "task": "Write 3 STAR stories from your best projects with numbers."},
                {"day": 2, "task": "Rewrite resume bullets as action + tool + result."},
                {"day": 3, "task": "Practice 5 technical questions out loud, 2 minutes each."},
                {"day": 4, "task": "Mock a US-client scenario: communication, time zones, escalation."},
                {"day": 5, "task": "Record yourself answering 'Tell me about yourself' in 90 seconds."},
                {"day": 6, "task": "Redo the weakest 3 answers from this session."},
                {"day": 7, "task": "Full mock interview again and compare scores."},
            ],
        }
    return reply_extra(task, user)


def reply_extra(task: str, user: str):
    if task == "detect":
        return None
    if task == "match":
        return {
            "match_score": 62,
            "verdict": "Decent overlap, but several required tools are missing from the resume text.",
            "matched_keywords": ["Java", "Selenium", "API testing"],
            "missing_keywords": ["CI/CD", "Docker", "Postman"],
            "gaps": [{"gap": "No CI/CD keywords", "fix": "If you have used Jenkins or GitHub Actions, add it to a project bullet."}],
            "tailored_bullets": [{"before": "Worked on testing", "after": "Built Selenium regression suites for API and UI testing"}],
        }
    if task == "nego_start":
        return {
            "market_range": "$95,000-$115,000 per year (estimate)",
            "offer": "$98,000 per year",
            "opening_message": "We would like to offer you the role at $98,000 a year. How does that sound to you?",
            "goal": "Reach the upper half of the range with a clear, polite justification.",
        }
    if task == "nego_turn":
        return {
            "recruiter_reply": "I hear you. I can move to $103,000, but that is near the top of what I can approve.",
            "current_offer": "$103,000 per year",
            "coach": {
                "what_worked": "You stayed polite and named a number.",
                "what_to_improve": "Tie your ask to specific impact from past work.",
                "better_line": "Based on the results I delivered and the market range, I was hoping for $108,000.",
            },
            "deal_closed": False,
        }
    if task == "nego_report":
        return {
            "outcome": "Offer improved during the session.",
            "score": 3.5,
            "strengths": ["Polite tone", "Asked for a higher number"],
            "mistakes": ["Did not cite market data", "Accepted the first counter quickly"],
            "script": ["I am excited about the role. Based on my experience and market data, I was targeting a higher figure."],
            "next_steps": ["Research three salary sources", "Write down your walk-away number"],
        }
    if task == "recruiter":
        n = len(user)
        score = 45 + n % 45
        return {
            "score": score,
            "recommendation": "advance" if score >= 70 else "maybe" if score >= 55 else "reject",
            "summary": "Relevant background with some gaps against the job description.",
            "strengths": ["Relevant technical stack"],
            "risks": ["Few measurable results", "Unclear recent tenure"],
            "screening_questions": ["Walk me through your most recent project.", "What is your notice period or availability?", "What are your compensation expectations?"],
        }
    raise KeyError(task)
