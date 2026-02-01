# Human-in-the-Loop Browser Automation

## Overview
LiteClaw now supports **interactive browser automation** where the browser agent can ask the user for help during task execution.

## How It Works

### 1. Browser Agent Tool
When using `browser_task`, the agent has access to an `ask_human` action:

```python
await ask_human("What's your Instagram password?")
```

### 2. Question Routing
- Question is stored in memory with the session_id
- User receives the question via WhatsApp/Telegram/Console
- User responds normally ("mypassword123")
- Response is automatically routed back to the browser task

### 3. Execution Flow

#### Example: Login to Instagram
```
User: "Login to my Instagram using browser"

LiteClaw: 
>>> [Browser]: Launching browser task...
>>> [Browser]: Human-in-the-loop ENABLED

Browser Agent (internally):
1. Goes to instagram.com
2. Finds login form
3. Checks SOUL.md for username - found: "mr.srisanth"
4. Checks SOUL.md for password - NOT found
5. Calls: await ask_human("What's your Instagram password?")

LiteClaw to User (via WhatsApp):
⏸️ [WAITING FOR USER INPUT]
Question: What's your Instagram password?
Please respond to continue the browser task.

User: "Srisanth1."

LiteClaw:
✅ Got it! Continuing browser task with your answer: "Srisanth1."

Browser Agent (continues):
6. Enters password
7. Clicks login
8. Confirms success
9. Returns result
```

## Implementation Details

### Files Modified

1. **`browser_utils.py`**
   - Added `ask_human_for_input()` async function
   - Added `set_human_answer()` for external response routing
   - Added `get_pending_question()` to check for waiting questions
   - Integrated Tools API with browser agent
   - Added session_id parameter throughout

2. **`agent.py`**
   - Updated `browser_task` execution to pass `session_id`
   - Added pending question check after browser task completes
   - Added "Human-in-the-loop ENABLED" status message

3. **`main.py`**
   - Added question detection in message handler
   - Routes user responses to `set_human_answer()` when pending question exists
   - Sends confirmation when answer is received

4. **`AGENT.md`**
   - Documented human-in-the-loop capability
   - Explained two modes: Fully Autonomous vs Interactive

## Usage Examples

### Fully Autonomous (No User Input Needed)
```
User: "Go to google.com and search for 'python tutorial'"
→ Browser executes completely autonomously
```

### Interactive (User Input Required)
```
User: "Login to my GitHub account"
→ Browser checks SOUL.md, finds username
→ Browser asks: "What's your GitHub password?"
→ User responds
→ Browser continues with login
```

### Benefits
- ✅ **Secure**: Credentials never stored, only asked when needed
- ✅ **Flexible**: Can handle any missing information dynamically
- ✅ **User-Friendly**: Questions routed through existing messaging channel
- ✅ **Timeout Protected**: 5-minute timeout prevents deadlocks
- ✅ **Session-Aware**: Multiple users can have simultaneous browser tasks

## Configuration
No additional configuration needed - feature is automatically enabled when using `browser_task`.

**Timeout**: Default 300 seconds (5 minutes) - can be adjusted in `ask_human_for_input()` function.
