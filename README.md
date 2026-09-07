# Newcomer's Complete Guide

**Welcome to Fuze Real Estate Agentic Service!**

This guide walks you through everything needed to get this system running from scratch, with no prior knowledge assumed.

## What is This System?

A conversational AI service that helps manage real estate contracts. You can:
1. **Change contract execution dates** by describing what you want in natural language
2. **Bulk terminate contracts** by uploading a CSV file

It's built with:
- **FastAPI** (web framework)
- **LangGraph** (agent orchestration)
- **SQLAlchemy** (database ORM)
- **LiteLLM** (AI gateway integration)

## Complete 5-Minute Setup

### Step 1: Initial Setup (2 minutes)

1. **Open terminal/PowerShell** in the project directory
2. **Create a Python virtual environment:**
   ```bash
   python -m venv venv
   ```
3. **Activate it:**
   ```bash
   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Configure (1 minute)

1. **Copy the environment template:**
   ```bash
   # Windows
   copy .env.example .env

   # macOS/Linux
   cp .env.example .env
   ```

2. **Edit `.env` file** (open in any text editor):
   - Replace `<your_jwt_token_here>` with your actual LiteLLM JWT token
   - Keep the other values as-is

### Step 3: Initialize Database (1 minute)

```bash
python -m app.database.init_db
```

You should see:
```
Initializing database...
[OK] Database tables created successfully
[OK] Database already seeded with 8 contracts
[OK] Database initialization complete!
```

### Step 4: Start the Server (1 minute)

```bash
python main.py
```

You should see:
```
Starting Fuze Real Estate Agentic Service...
[OK] Application startup complete!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal open!**

### Step 5: Test It! (Opens automatically)

1. **Open new terminal** (keep server running)
2. **Copy and run this test:**
   ```bash
   curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_user",
       "session_id": "test_1",
       "message": "Please change the execution date to 15-MAR-2026 for contract SAID 100001"
     }'
   ```

You should see a success response!

---

## Documentation Road Map

### For Verification & Troubleshooting
- **[SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)** - Step-by-step checks to ensure everything works
  - Use this if something doesn't work as expected
  - Helps diagnose installation issues

### For Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Detailed quick start guide
  - Complete setup instructions with multiple test examples
  - Troubleshooting for common errors
  - DBeaver database connection guide
  - Example requests and expected responses

### For Understanding the System
- **[README.md](README.md)** - Full project documentation
  - Architecture overview
  - Supported use cases
  - Configuration options
  - API endpoint reference
  - Design decisions

## Key Concepts

### Intents (What Users Can Do)

**1. Execution Date Changes**
- Single contract modification
- Example: "Change execution date to 15-MAR-2026 for SAID 100001"
- System updates the contract's execution date in database

**2. Bulk Terminations**
- Multiple contracts at once
- Upload CSV with contract details
- System terminates all contracts and updates database

### Workflow Flow

```
User Message/CSV Upload
    ↓
Intent Detection (AI understands what you want)
    ↓
Validation (Checks required information)
    ↓
Route to Appropriate Agent
    ↓
Execute Tool (Update database)
    ↓
Response to User
```

### Available Test Contracts

Use any of these SAID values for testing:

```
SAID 365833 - For execution date testing
SAID 100001-100007 - For bulk termination testing
```

## Common Tasks

### Testing Execution Date Change

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo",
    "session_id": "test_exec",
    "message": "Update execution date to 20-JUL-2026 for contract SAID 365833"
  }'
```

### Testing Bulk Termination

1. Create `test.csv`:
   ```csv
   contract_nbr,ammendment_nbr,contract_said,termination_dt,termination_code,description,fas13_doc_id
   223346,0,100001,01-SEP-2026,LANDLORD,Test termination,NOREQ
   225099,0,100002,01-SEP-2026,LANDLORD,Test termination,NOREQ
   ```

2. Upload:
   ```bash
   curl -X POST "http://localhost:8000/api/chat/upload" \
     -F "user_id=demo" \
     -F "session_id=test_bulk" \
     -F "file=@test.csv"
   ```

### Viewing API Documentation

Open browser to: **http://localhost:8000/docs**

You'll see Swagger UI with all endpoints and can test directly!

## Troubleshooting Quick Guide

| Problem | Solution |
|---------|----------|
| "Module not found" | Activate venv: `venv\Scripts\activate` or `source venv/bin/activate` |
| "LiteLLM connection error" | Check `.env` has valid JWT token and network connectivity |
| "Database connection error" | Verify `DB_URL` in `.env`, Oracle host/port reachability, and credentials |
| "Port 8000 in use" | Use different port: `python main.py` (or configure port in settings) |
| "Date validation error" | Use future dates! (Current date: 2026-08-01, use dates after this) |

See [QUICK_START.md](QUICK_START.md) for more detailed troubleshooting.

## File Structure (What's What)

```
fuze-re-agentic-service/
├── main.py                    # Start here: python main.py
├── requirements.txt           # Python packages
├── .env.example              # Configuration template
├── .env                       # Your configuration (create from template)
├── .env                     # Database and gateway configuration
│
├── QUICK_START.md           # Getting started guide
├── SETUP_VERIFICATION.md    # Verification checklist
├── README.md                # Full documentation
└── app/                     # Application code
    ├── api/                 # REST endpoints
    ├── agents/              # AI agents
    ├── tools/               # Tools for agents
    ├── core/                # Core logic (validation, graph, etc.)
    ├── database/            # Database models and initialization
    ├── services/            # LLM, query execution, CSV processing
    └── config/              # Settings
```

## Next Steps

1. **Complete Setup**: Follow steps 1-5 above (5 minutes)
2. **Verify Installation**: See [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) (optional, 2 minutes)
3. **Run Tests**: Use examples in [QUICK_START.md](QUICK_START.md) (5 minutes)
4. **Explore Further**: Read [README.md](README.md) for architecture and design details
5. **View Live API Docs**: http://localhost:8000/docs (after starting server)

## Testing in Swagger UI (Easiest)

1. Start server: `python main.py`
2. Open browser: http://localhost:8000/docs
3. Click `/api/chat` → "Try it out"
4. Replace example with your message
5. Click "Execute" → See response

**No curl commands needed!**

## Database Verification

After running operations, verify changes:

```bash
python -c "
from app.database.session import SessionLocal
from app.database.models import Contract

db = SessionLocal()

# Check a contract
contract = db.query(Contract).filter(Contract.contract_said == 100001).first()
if contract:
    print(f'SAID: {contract.contract_said}')
    print(f'Execution Date: {contract.execution_dt}')
    print(f'Termination Code: {contract.termination_code}')

db.close()
"
```

Or use **DBeaver** for GUI access (see [QUICK_START.md](QUICK_START.md)).

## Getting Help

1. **Setup Issues?** → See [SETUP_VERIFICATION.md](SETUP_VERIFICATION.md)
2. **How to test?** → See [QUICK_START.md](QUICK_START.md)
3. **How does it work?** → See [README.md](README.md)
4. **Error message?** → Check troubleshooting sections in all guides
5. **Still stuck?** → Check logs in terminal where server is running

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `main.py` | Start the server here |
| `.env` | Your configuration (secret token) |
| `requirements.txt` | Python packages to install |
| `QUICK_START.md` | Quickstart guide |
| `SETUP_VERIFICATION.md` | Verification checklist |
| `README.md` | Complete documentation |

---

**You're ready to go! Follow the 5-step setup above and start testing.** 🚀

Questions? Check the appropriate guide above or examine the error messages in the console.




-------------------------------------------------------------------------------------------------------------







# Setup Verification Checklist

Use this checklist to verify that the Fuze RE Agentic Service is properly installed and ready to run.

## Pre-Installation Checks

- [ ] **Python Version**: Run `python --version` → Should be 3.11 or higher
  ```bash
  python --version
  ```

- [ ] **Project Directory**: Navigate to the project directory
  ```bash
  cd C:\Users\moizmo7\Desktop\FUZE\agentic-repo\fuze-re-agentic-service
  ```

- [ ] **Virtual Environment**: Create and activate
  ```bash
  python -m venv venv
  venv\Scripts\activate  # Windows
  source venv/bin/activate  # macOS/Linux
  ```

## Installation Checks

- [ ] **Dependencies Installed**: Run `pip install -r requirements.txt` → Should complete without errors
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **Import Test**: Verify core modules load
  ```bash
  python -c "from app.database.models import Contract; from app.services.llm import ChatLiteLLM; print('OK')"
  ```

## Configuration Checks

- [ ] **.env File Exists**: Check that `.env` file is in project root
  ```bash
  ls -la .env  # macOS/Linux
  dir .env    # Windows
  ```

- [ ] **.env Contains JWT Token**:
  ```bash
  cat .env | grep LITELLM_JWT_TOKEN  # Should NOT be empty or <your_jwt_token_here>
  ```

- [ ] **.env File is Complete**: Should have these 5 variables:
  ```bash
  LITELLM_JWT_TOKEN
  LITELLM_GATEWAY_URL
  LITELLM_MODEL
  LITELLM_TEMPERATURE
  DB_URL
  LOG_LEVEL
  ```

## Database Checks

- [ ] **Database Initialization**: Run the initialization script
  ```bash
  python -m app.database.init_db
  ```
  Expected output:
  ```
  Initializing database...
  [OK] Database tables created successfully
  [OK] Database already seeded with 8 contracts
  [OK] Database initialization complete!
  ```

- [ ] **Database Connectivity**: Verify Oracle DB URL is configured
  ```bash
  # macOS/Linux
  cat .env | grep DB_URL

  # Windows
  type .env | findstr DB_URL
  ```

- [ ] **Sample Data Available**: Verify contracts are seeded
  ```bash
  python -c "
from app.database.session import SessionLocal
from app.database.models import Contract
db = SessionLocal()
count = db.query(Contract).count()
print(f'[OK] Database has {count} contracts')
db.close()
  "
  ```
  Expected output: `[OK] Database has 8 contracts`

## Application Checks

- [ ] **Application Imports**: Verify the app loads
  ```bash
  python -c "from main import app; print(f'[OK] App loaded with {len(app.routes)} routes')"
  ```
  Expected output: `[OK] App loaded with 8 routes`

- [ ] **LiteLLM Service**: Verify LLM integration loads
  ```bash
  python -c "from app.services.llm import ChatLiteLLM; print('[OK] LLM service loads')"
  ```
  Expected output: `[OK] LLM service loads`

- [ ] **Graph Builder**: Verify agent graph can be built
  ```bash
  python -c "from app.core.graph_builder import build_agent_graph; graph = build_agent_graph(); print('[OK] Agent graph built')"
  ```
  Expected output: `[OK] Agent graph built`

## Server Check (Optional)

- [ ] **Server Startup**: Start the server in a separate terminal
  ```bash
  python main.py
  ```
  Expected output:
  ```
  Starting Fuze Real Estate Agentic Service...
  [OK] Application startup complete!
  INFO:     Uvicorn running on http://0.0.0.0:8000
  ```

- [ ] **Health Check**: In a new terminal, test the health endpoint
  ```bash
  curl http://localhost:8000/api/health
  ```
  Expected response:
  ```json
  {"status": "healthy", "timestamp": "...", "version": "1.0.0"}
  ```

- [ ] **API Docs**: Open browser to http://localhost:8000/docs
  - Should show Swagger UI
  - Should list `/api/chat`, `/api/chat/upload`, `/api/health` endpoints

## Quick Functional Test

If server is running, test one endpoint:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test_1",
    "message": "Change execution date to 15-MAR-2026 for SAID 100001"
  }'
```

Expected response should have:
- `"status": "success"` or `"status": "needs_input"`
- A message field with response text
- No error status

## Troubleshooting

### If Module Not Found
```bash
# Ensure venv is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall requirements
pip install -r requirements.txt
```

### If .env Error
```bash
# Copy template
cp .env.example .env  # macOS/Linux
copy .env.example .env  # Windows

# Edit .env and add your JWT token
# Then run verification again
```

### If Database Error
```bash
# Verify DB URL and retry initialization
# Expected Oracle URL format:
# oracle+oracledb://<user>:<url_encoded_password>@<host>:1521/?service_name=<service_name>

# Reinitialize
python -m app.database.init_db
```

### If LiteLLM Connection Error
- Verify JWT token is correct and not expired
- Check network connectivity to VZ gateway
- Verify gateway URL: https://vz-ai-gateway-gke-test-east.ebiz.verizon.com

## All Checks Passing?

✅ If all checkmarks above are complete, the system is **ready for testing!**

Next step: Follow the [QUICK_START.md](QUICK_START.md) guide to run tests.

## Test Coverage

This verification ensures:
- ✅ Python and dependencies installed correctly
- ✅ Configuration files exist and are valid
- ✅ Database is initialized with sample data
- ✅ All core modules import without errors
- ✅ Agent graph builds successfully
- ✅ Server can start and respond to requests
- ✅ API endpoints are accessible

---

**Need Help?** See [QUICK_START.md](QUICK_START.md) Troubleshooting section for common issues.








---------------------------------------------------------



# Contract Lookup Feature - Quick Test Guide

## Quick Setup

1. **Start the backend server:**
   ```bash
   cd fuze-re-agentic-service
   python main.py
   # Server runs on http://localhost:8000
   ```

2. **In another terminal, test via API:**
   ```bash
   # Test 1: Lookup by SAID
   curl "http://localhost:8000/api/contract/lookup?said=365833"

   # Test 2: Lookup by Contract Number
   curl "http://localhost:8000/api/contract/lookup?nbr=219533"
   ```

3. **Or test via Chat API:**
   ```bash
   curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_user",
       "session_id": "test_session_1",
       "message": "Look up contract SAID 365833"
     }'
   ```

## Expected Log Output (Backend)

### Before Fix (would show GENERAL_QUERY routing):
```
[Orchestrator] Using LLM for intent classification
[Orchestrator] LLM classified intent: general_query (confidence: 0.8)
[Orchestrator] GENERAL_QUERY intent detected
[GRAPH] === General Query Agent Node START ===
```

### After Fix (shows CONTRACT_LOOKUP routing):
```
[Orchestrator] Using LLM for intent classification
[Orchestrator] LLM classified intent: contract_lookup (confidence: 0.95)
[Orchestrator] CONTRACT_LOOKUP intent detected
[Orchestrator] ✓ Routing to ContractLookupAgent
[GRAPH] === Contract Lookup Agent Node START ===
[ContractLookupAgent] Tool result: True
[ContractLookupAgent] ✓ Contract lookup successful
```

## Test Cases

### Test 1: "Look up contract SAID 365833"
**Expected:**
- Intent: contract_lookup
- Route: contract_lookup_agent_node
- Response: Comprehensive contract info with status, dates, financial details, etc.

**How to verify:**
- Check logs for "CONTRACT_LOOKUP intent detected"
- See formatted contract response with ✅ symbol

### Test 2: "Find contract 219533"
**Expected:**
- Intent: contract_lookup
- Route: contract_lookup_agent_node
- Response: Same comprehensive contract information

**How to verify:**
- Logs show "contract_lookup" intent
- Response contains contract 219533 details

### Test 3: "Show me SAID 365833"
**Expected:**
- Intent: contract_lookup (system prompt includes "show me" keyword)
- Route: contract_lookup_agent_node
- Response: Contract details

**How to verify:**
- LLM recognizes "show me" keyword
- Proper CONTRACT_LOOKUP classification

### Test 4: "Contract SAID 999999" (non-existent)
**Expected:**
- Intent: contract_lookup
- Route: contract_lookup_agent_node
- Response: "I couldn't find the contract. No contract found with SAID 999999"

**How to verify:**
- Still routes to contract_lookup_agent
- Graceful error message

### Test 5: "I want to look up a contract" (no ID)
**Expected:**
- Intent: contract_lookup
- Route: contract_lookup_agent_node
- Response: "I need a contract identifier to look up. Please provide either a Contract SAID (6-digit number) or Contract Number."

**How to verify:**
- Routes to contract_lookup_agent
- Asks for clarification

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Test 1: "Look up contract SAID 365833" routes to CONTRACT_LOOKUP
- [ ] Test 2: "Find contract 219533" returns contract info
- [ ] Test 3: "Show me contract" recognizes the intent
- [ ] Test 4: Invalid contract returns proper error
- [ ] Test 5: Missing contract ID asks for clarification
- [ ] Logs show CONTRACT_LOOKUP routing (not GENERAL_QUERY)
- [ ] Response contains comprehensive contract information
- [ ] Frontend "Find Contract" button works correctly
- [ ] No existing functionality broken

## Key Indicators

### ✅ Fix is Working:
- Logs show: `[Orchestrator] CONTRACT_LOOKUP intent detected`
- Logs show: `[GRAPH] === Contract Lookup Agent Node START ===`
- Response shows contract data (dates, financial info, tenant info, etc.)

### ❌ Fix Not Working:
- Logs show: `[Orchestrator] GENERAL_QUERY intent detected`
- Logs show: `[GRAPH] === General Query Agent Node START ===`
- Response is conversational instead of showing structured contract data

## Troubleshooting

**Issue: Still seeing GENERAL_QUERY routing**
- Solution: Clear any Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
- Restart the backend server

**Issue: "Contract not found" error**
- Check if contract SAID 365833 or 219533 exists in database
- Try with known contract from sample data

**Issue: API endpoint 404**
- Verify backend is running on http://localhost:8000
- Check that the endpoint is `/api/contract/lookup?said=XXX`

## Sample Contracts in Database

The system is pre-seeded with sample contracts:
- SAID: 365833 (Contract Nbr: 219533)
- SAID: 128868
- And others (see seeded data in main.py)

Use these for testing.

## Frontend Testing

1. Open the UI and navigate to the chatbot
2. Click the "Find Contract" quick action button
3. Observe the text "I want to look up a contract" is inserted
4. Press send
5. Verify CONTRACT_LOOKUP intent is detected (check backend logs)
6. Confirm comprehensive contract information is displayed

## Measurement

**Success Metric:** When you ask for a contract lookup, the backend routes to `contract_lookup_agent_node` (not `general_query_agent_node`) and displays comprehensive contract information.

**Before Fix:** Routes to general_query_agent (shows conversational response)
**After Fix:** Routes to contract_lookup_agent (shows comprehensive contract data)

---

The critical fix has been applied to `app/api/templates.py`. The Contract Lookup feature is ready for end-to-end testing.

