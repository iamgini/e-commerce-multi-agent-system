# Returns & Refunds Agent

## Overview

Helps customers manage returns, process refunds, and handle complaints. Works as part of the e-commerce multi-agent system.

---

## What It Does

| Task | Description |
|------|-------------|
| **Check eligibility** | Is the order within 30-day return window? |
| **Create return** | Start a return request |
| **Return status** | Track return progress |
| **Refund status** | Check refund amount and timeline |
| **File complaint** | Report damaged or defective items |
| **Return policy** | Show policy details |

---

## Return Policy

- **Window**: 30 days from purchase
- **Unopened**: 100% refund
- **Used**: 80% refund
- **Damaged/Defective**: 100% refund
- **Shipping**: Free return shipping
- **Timeline**: 5-7 business days after inspection

---

## Files

| File | Purpose |
|------|---------|
| `agents/returns_refunds_agent.py` | Agent logic |
| `tools/returns_tools.py` | 6 return tools |
| `agents/coordinator.py` | Routes "return" queries to this agent |
| `graph/workflow.py` | Integrates agent into workflow |

---

## How to Test

```bash
python main.py --user test_user

You: return
You: My item damaged
You: quit
```

---

## Tools (6 total)

1. `check_return_eligibility` - Verify 30-day window
2. `create_return_request` - Start return
3. `get_return_status` - Track return
4. `get_refund_status` - Check refund
5. `file_complaint` - Report damage
6. `get_return_policy` - Show policy

---

## Routing

**Detected keywords** (26 total):
return, refund, damaged, broken, complaint, defective, eligible, return policy, return window, shipping back, refund status, money back, reimbursement, issue, problem, warranty, exchange, return label, return tracking, when will i get, refund when, can i return, how do i return, return process

**Route constant**: `ROUTE_RETURNS = "returns_refunds"`

---

## Integration

- Agent node: `returns_refunds_agent_node(state, config)`
- Tools node: `ToolNode(RETURNS_TOOLS)`
- Coordinator detects return keywords and routes to this agent
- Works with Recommendation Agent and Sales Agent

---

## Python 3.14 Compatibility

✅ Uses `SystemMessage` format  
✅ Tool binding compatible  
✅ No hanging issues  

---
