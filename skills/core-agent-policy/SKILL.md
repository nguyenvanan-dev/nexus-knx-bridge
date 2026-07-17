# Approval & Deployment Policy

From now on, whenever a user requests creating, modifying, or deploying a skill, you MUST follow this workflow.

Phase 1 - Planning
- Analyze the user's request.
- Produce an implementation plan.
- Explain: Goal, Files to create, Files to modify, Commands to execute, Possible risks.
- Wait for explicit approval.
- Do NOT generate or install any skill before approval.

Phase 2 - Draft Generation
After the user replies with 'Approve', 'Duyệt', or 'Đồng ý':
- Use draft-skill to generate the complete skill code. This tool will auto-generate metadata.yaml and save everything to skills/drafts/draft_ID/.
- Present a deployment summary containing the draft_ID.
- Do NOT deploy yet.

Phase 3 - Staging & Deployment Approval
Only after receiving a second explicit confirmation may you proceed:
- If the user wants to test it, you can use stage-skill to move the draft to Staging.
- If the user says 'Deploy', 'Cài đặt', use commit-skill and pass the draft_ID. This tool reads metadata, archives the old version, moves the code to Official, registers it, and restarts the gateway.

Never automatically overwrite existing skills, execute shell commands, or restart services without using these specific lifecycle tools and getting explicit approval.
