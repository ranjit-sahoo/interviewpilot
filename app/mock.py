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
            "followup": "What was the hardest part of that, and what would you do differently now?",
        }
    if task == "report":
        return {
            "overall_score": 3.4,
            "summary": "Good technical base. Answers need more concrete examples, numbers and STAR structure.",
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
    raise KeyError(task)
