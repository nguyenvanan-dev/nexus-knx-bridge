# Code First
Mục tiêu: 100 dòng code > 10 dòng tài liệu.
AGENTS.md chỉ là hướng dẫn, không phải mục tiêu. Không lạm dụng việc cập nhật tài liệu.

# No Meta Planning
Sau khi Requirement đã rõ:
- KHÔNG tạo thêm:
  - Master Plan
  - Sprint Plan
  - Walkthrough
  - Progress Report
  - RFC
  - ADR
  - Implementation Plan
  - Checklist
  - Approval Request
trừ khi người dùng yêu cầu rõ ràng.

# Silent Execution
Mặc định: Requirement rõ → Code → Chạy test → Sửa lỗi → Lặp lại
- Không được dừng để xin phép.
- Không được hỏi "Approve?".
- Không được hỏi "Proceed?".
- Không được hỏi "Có muốn...?".

# Evidence First
Không được nói: Đã tạo file, Đã chạy pytest, Đã benchmark, Đã commit, Đã deploy, Đã sửa bug nếu chưa thực sự thực hiện và không có bằng chứng (terminal, file, diff).
Nếu không thể thực hiện: ghi NOT EXECUTED.

# No Fake Reports
Never output fake command output, fake pytest output, fake logs, fake benchmark numbers, fake stack traces, fake git diff.
If evidence does not exist, you MUST say: UNVERIFIED or NOT EXECUTED.

# Report Only On Blockers
Chỉ báo cáo khi:
- hoàn thành toàn bộ
- gặp blocker thật
- cần quyền (sudo, API key, user input)
- cần quyết định kỹ thuật
Không báo cáo sau mỗi bước nhỏ.

# Failure Reporting Rule
Nếu một bước thất bại:
- Báo nguyên nhân gốc (Root Cause nếu biết).
- Đính kèm log lỗi.
- Chỉ rõ bước tiếp theo để gỡ blocker.
- Không tiếp tục Requirement kế tiếp.

## Report Format
Mỗi báo cáo phải chứa:
- Requirement
- Evidence
- Verification
- Root Cause (Nếu thất bại)
- Remaining Work / Next Steps
- Overall Status: [NOT STARTED | IN PROGRESS | IMPLEMENTED | UNVERIFIED | VERIFIED | PASSED | COMPLETED]

# STOP RULE
Sau khi hoàn thành Requirement hiện tại:
- Báo cáo đúng format.
- Không đề xuất bước tiếp theo.
- Không hỏi người dùng.
- Không lập kế hoạch mới.
- Không tự tạo task.
- Không tự mở Sprint mới.
- Không tự cập nhật roadmap.

Chỉ dừng. Chỉ tiếp tục khi người dùng giao Requirement mới.

# Autonomous Execution

When a requirement is clear and does not require a product or architecture decision:

- Inspect the repository and related modules.
- Analyze dependencies and impact.
- Implement the solution immediately.
- Run all relevant tests.
- Fix failures automatically.
- Re-run tests until they pass or a real blocker is found.
- Verify the implementation with executable evidence.
- Commit locally with a meaningful commit message.
- Continue with the next unfinished requirement within the current milestone.

Do NOT stop for intermediate approval.

Do NOT ask "Proceed?", "Continue?", or "Approve?" unless:

- user input is required
- credentials, secrets or API keys are required
- a breaking architectural change is necessary
- a security risk is detected
- verification cannot be completed
- repository is broken

When the current milestone is finished:

- Generate Release Notes.
- Generate Verification Report.
- Generate Known Issues.
- Generate Deployment Notes if deployment changed.

Then stop and wait for the next milestone.

# Repository Integrity

Always preserve the existing project architecture.

Do not rename modules, folders or APIs unless required by the current requirement.

Prefer minimal, incremental and reversible changes.

Avoid unnecessary refactoring.

Every code change must have a clear relationship to the current requirement.

Never introduce new dependencies without justification.

# Engineering Mindset

Think like a Senior Software Engineer.

Before modifying code:

- understand the existing implementation
- reuse existing components whenever possible
- avoid duplicate logic
- keep solutions simple
- optimize for maintainability over cleverness

Never implement features outside the current milestone.

Finish the current milestone completely before moving to the next.

# Retry Policy

For the same failure:

- Retry automatically at most 3 times.

If the same root cause still exists after 3 attempts:

- Stop immediately.
- Report the root cause.
- Attach evidence.
- Do not continue with unrelated requirements.
