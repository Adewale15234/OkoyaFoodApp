from datetime import datetime

def ai_offence_review(worker, reason):
    if not reason:
        reason = "No reason provided"

    reason_lower = reason.lower()

    high_severity_words = ["theft", "steal", "fight", "violence", "assault", "fraud", "dismissed"]
    medium_severity_words = ["absent", "lateness", "late", "insult", "disrespect", "warning"]

    score = 0

    for word in high_severity_words:
        if word in reason_lower:
            score += 3

    for word in medium_severity_words:
        if word in reason_lower:
            score += 1

    if score >= 3:
        severity = "HIGH"
        recommendation = "Immediate Suspension / Investigation"
    elif score == 2:
        severity = "MEDIUM"
        recommendation = "Formal Warning Required"
    else:
        severity = "LOW"
        recommendation = "Verbal Warning / Monitoring"

    escalation = "HR Director Review Required" if severity == "HIGH" else "Supervisor Review"

    return f"""

AI OFFENCE REVIEW REPORT

Worker Name: {worker.name}
Worker Code: {worker.worker_code}
Position: {worker.position}

Reported Issue:
{reason}

AI ANALYSIS

Severity Level: {severity}
Risk Score: {score}

Recommendation: {recommendation}
Escalation Level: {escalation}

SUMMARY

This case has been automatically analyzed based on HR behavioural patterns.
Further human verification is recommended before final disciplinary action.
"""

def generate_hr_letter(worker, reason, status_type):
    name = worker.name or "Unknown"
    code = worker.worker_code or "N/A"
    position = worker.position or "N/A"
    date = datetime.utcnow().strftime('%Y-%m-%d')
    reason_text = reason if reason else "No reason provided"

    offence_review = ai_offence_review(worker, reason)

    if status_type in ["deactivated", "suspended"]:
        letter_body = f"""

OKOYA FOOD COMPANY LIMITED
HUMAN RESOURCES DEPARTMENT
OFFICIAL DISCIPLINARY NOTICE

Employee Name: {name}
Employee Code: {code}
Position: {position}

STATUS: {status_type.upper()}

REASON FOR ACTION:
{reason_text}

HR DECISION

Following internal review and company policy guidelines,
you have been placed under disciplinary action and
temporarily removed from active duty pending further review.

You are advised to report to the HR department for clarification.

Effective Date: {date}

NOTE:
Failure to comply may lead to permanent termination.

OKOYA FOOD HR MANAGEMENT SYSTEM
"""
        return letter_body + "\n" + offence_review

    elif status_type in ["reactivated", "reinstated"]:
        letter_body = f"""

OKOYA FOOD COMPANY LIMITED
HUMAN RESOURCES DEPARTMENT
REINSTATEMENT NOTICE

Employee Name: {name}
Employee Code: {code}
Position: {position}

STATUS: REINSTATED

HR DECISION

After careful review of your case,
management has approved your return to active duty.

You are expected to resume duties immediately and
maintain proper conduct going forward.

Effective Date: {date}

HR DEPARTMENT
OKOYA FOOD COMPANY LIMITED
"""
        return letter_body + "\n" + offence_review

    else:
        letter_body = f"""
OKOYA FOOD HR SYSTEM

Employee: {name}
Code: {code}

Status Update: {status_type}

No formal HR letter template matched this status.
Please verify the worker status configuration.

Date: {date}
"""
        return letter_body + "\n" + offence_review