# Multi-Service Customer Service System - MVP

## 🚀 Quick Start (Get Running in 10 Minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements_enhanced.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Run Setup Check

```bash
python setup_mvp.py
```

This will verify:
- ✅ Python version (3.11+)
- ✅ Dependencies installed
- ✅ OpenAI API connection
- ✅ Classifier agent working

### 4. Run the MVP Pipeline

```bash
# Demo mode (automated test cases)
python mvp_pipeline.py --mode demo

# Interactive mode (manual testing)
python mvp_pipeline.py --mode interactive
```

---

## 📁 File Structure

```
business_enquiry_system/
├── agents/
│   ├── base_agent_v2.py              # NEW: Enhanced base agent with Pydantic
│   ├── classifier_v2.py              # NEW: LLM-powered classifier
│   └── specialists/
│       └── airtime_sales_agent_v2.py # NEW: Airtime purchase agent
│
├── database/
│   └── schema.sql                    # NEW: PostgreSQL database schema
│
├── .env.example                      # NEW: Environment configuration template
├── requirements_enhanced.txt         # NEW: Complete dependencies
├── setup_mvp.py                      # NEW: Setup verification script
├── mvp_pipeline.py                   # NEW: Simple sequential pipeline
│
├── ENHANCED_SYSTEM_DESIGN.md         # Complete architecture design
├── IMPLEMENTATION_QUICKSTART.md      # Day-by-day implementation guide
└── CODEBASE_ANALYSIS_SUMMARY.md      # Analysis of existing code
```

---

## 🎯 What's Implemented

### ✅ Working Features

1. **Enhanced Base Agent Architecture**
   - Pydantic models for type safety
   - Standardized metrics tracking
   - Built-in logging and error handling
   - Compatible with AutoGen GroupChat

2. **LLM-Powered Classifier**
   - Classifies service domain (AIRTIME, POWER, DATA, MULTI)
   - Extracts intent, priority, sentiment
   - Entity extraction (phones, amounts, networks)
   - Fallback to rule-based classification

3. **Airtime Sales Agent**
   - Supports MTN, Airtel, Glo, 9Mobile
   - Phone number validation
   - Bulk purchase discounts (5% for ₦10,000+)
   - Mock transactions for testing
   - Ready for real API integration

4. **Simple Pipeline**
   - Sequential processing (Classifier → Specialist → Response)
   - Context sharing between agents
   - Performance metrics
   - Demo and interactive modes

### 🚧 Coming Soon (Week 2-4)

- Power/Electricity Sales Agent (EKEDC, IKEDC, etc.)
- Data Package Sales Agent
- RAG-powered Research Agent (ChromaDB)
- Database persistence (PostgreSQL)
- Real API integrations
- AutoGen GroupChat implementation

---

## 🧪 Testing

### Test Individual Agents

```bash
# Test classifier
python agents/classifier_v2.py

# Test airtime agent
python agents/specialists/airtime_sales_agent_v2.py
```

### Test Complete Pipeline

```bash
# Automated demo
python mvp_pipeline.py --mode demo

# Interactive testing
python mvp_pipeline.py --mode interactive
```

### Example Test Messages

Try these in interactive mode:

```
"I need 1000 naira MTN airtime for 08012345678"
"Send me 15000 naira Airtel airtime to 08098765432"
"How much is 2000 naira airtime?"
"Buy me 5000 naira EKEDC token for meter 12345678901"  (not yet implemented)
"I want 10GB data on MTN"  (not yet implemented)
```

---

## 📊 Sample Output

```
================================================================================
  PROCESSING CUSTOMER ENQUIRY
================================================================================

Customer: Chinedu Okafor
Message: I need 1000 naira MTN airtime for 08012345678

STEP 1: Classifying message
--------------------------------------------------------------------------------
   Domain: AIRTIME
   Intent: purchase
   Priority: MEDIUM
   Sentiment: NEUTRAL
   Confidence: 0.95

STEP 2: Routing to specialist agent
--------------------------------------------------------------------------------
   → Routing to AirtimeSalesAgent

STEP 3: Generating final response
--------------------------------------------------------------------------------

================================================================================
  FINAL RESPONSE
================================================================================

✅ Airtime Purchase Successful!

Network: MTN
Recipient: 08012345678
Amount: ₦1,000.00

Transaction ID: TXN-A3F8C9214B7E
Reference: REF-F8D3C921

The airtime has been sent successfully.
Thank you for using our service!

Processing time: 2341ms
Agents involved: ClassifierAgent, AirtimeSalesAgent
Status: COMPLETED
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (for production)
DATABASE_URL=postgresql://user:pass@localhost/csdb
REDIS_URL=redis://localhost:6379/0
MTN_API_KEY=your-mtn-key
PAYSTACK_SECRET_KEY=sk_test_your-key
```

### LLM Configuration

The system uses GPT-4o-mini by default for cost efficiency:

```python
llm_config = {
    "config_list": [{
        "model": "gpt-4o-mini",
        "api_key": os.getenv("OPENAI_API_KEY")
    }],
    "temperature": 0.3  # Adjust for creativity vs consistency
}
```

**Cost**: ~$0.05 per enquiry (very affordable)

---

## 🐛 Troubleshooting

### Issue: ModuleNotFoundError

```bash
# Reinstall dependencies
pip install -r requirements_enhanced.txt
```

### Issue: OpenAI API Error

```bash
# Check your API key in .env
cat .env | grep OPENAI_API_KEY

# Test connection
python -c "import openai; print(openai.__version__)"
```

### Issue: Import errors

```bash
# Ensure you're in the project root
cd c:\Users\finan\Documents\Agent AI\business_enquiry_system

# Run from project root
python mvp_pipeline.py
```

### Issue: "Classification failed"

- LLM might be rate-limited → wait 1 minute
- System automatically falls back to rule-based classification
- Check logs for detailed error

---

## 📈 Performance Metrics

After running the demo, check agent metrics:

```
ClassifierAgent:
   Total requests: 4
   Success rate: 100%
   Avg processing time: 823ms

AirtimeSalesAgent:
   Total requests: 2
   Success rate: 100%
   Avg processing time: 451ms
```

**Target Performance**:
- Classification: <500ms
- Transaction: <1500ms
- Total response: <3000ms

---

## 🗺️ Next Steps

### This Week

1. ✅ Run `setup_mvp.py` - verify everything works
2. ✅ Test with `mvp_pipeline.py --mode demo`
3. ✅ Try interactive mode with your own messages
4. ✅ Review [ENHANCED_SYSTEM_DESIGN.md](ENHANCED_SYSTEM_DESIGN.md)

### Next Week (Days 8-14)

Follow [IMPLEMENTATION_QUICKSTART.md](IMPLEMENTATION_QUICKSTART.md):

1. Create PowerSalesAgent (copy AirtimeSalesAgent pattern)
2. Create DataSalesAgent
3. Add database persistence
4. Implement RAG with ChromaDB

### Weeks 3-4

1. Integrate real APIs (MTN, EKEDC, Paystack)
2. Build REST API with FastAPI
3. Add monitoring
4. Write tests

---

## 💡 Tips

1. **Start Simple**: Get airtime working perfectly before adding power/data
2. **Test Often**: Run `mvp_pipeline.py` after each change
3. **Check Metrics**: Use agent metrics to identify bottlenecks
4. **Use Mock APIs**: Don't integrate real APIs until MVP is stable
5. **Read Logs**: Detailed logs help debug issues

---

## 📚 Documentation

- **Architecture**: [ENHANCED_SYSTEM_DESIGN.md](ENHANCED_SYSTEM_DESIGN.md)
- **Implementation Guide**: [IMPLEMENTATION_QUICKSTART.md](IMPLEMENTATION_QUICKSTART.md)
- **Codebase Analysis**: [CODEBASE_ANALYSIS_SUMMARY.md](CODEBASE_ANALYSIS_SUMMARY.md)

---

## 🤝 Support

If you encounter issues:

1. Check logs in `logs/` directory
2. Review documentation files
3. Run `setup_mvp.py` to verify setup
4. Check agent metrics for performance issues

---

## 🎉 Success Criteria

You've successfully set up the MVP when:

- ✅ `setup_mvp.py` passes all checks
- ✅ Classification accuracy >90% on test messages
- ✅ Airtime purchases process successfully
- ✅ Average response time <3 seconds
- ✅ No errors in demo mode

**Congratulations! You're ready to build the full system!**

---

**Version**: MVP 1.0
**Last Updated**: November 4, 2025
**Status**: Ready for Testing
