# A3-1 Submission Notes

## Interface choice
I implemented my own web interface and backend (bonus path). The system is a custom Python web application with a SQLite backend. It records worker ID, assignment ID, HIT ID, condition, assigned task trials, participant responses, confidence, time spent, and post-study measures.

## Conditions
- Baseline condition: participants judge each counselor response without AI assistance.
- AI-assisted condition: participants can optionally reveal the AI suggestion generated in Assignment 2 before making a judgment.

## Trial flow
- Each participant receives 10 randomized trials from the Assignment 2 study dataset.
- Not all participants receive the exact same trial set.
- After each trial, participants provide a judgment and confidence rating.
- At the end, participants complete a short post-study questionnaire.
- The system then generates a completion code for MTurk approval.

## Extra measurements
In addition to task performance, the interface records:
- Trial-level time spent
- Trial-level confidence
- Post-study perceived workload
- Post-study overall confidence
- Post-study AI helpfulness in the AI-assisted condition
- Whether and when the participant revealed the AI suggestion

## Screenshots to include
- (Screenshot: baseline instruction page)
- (Screenshot: baseline trial page)
- (Screenshot: AI-assisted trial page before reveal)
- (Screenshot: AI-assisted trial page after reveal)
- (Screenshot: completion code page)
- (Screenshot: exported CSV or database evidence showing recorded submissions)

## Testing notes
- Tested locally with both baseline and AI-assisted conditions.
- Verified that trial assignments are stored in SQLite.
- Verified that responses can be exported to CSV for later analysis.
- Verified that completion codes are generated after study completion.
