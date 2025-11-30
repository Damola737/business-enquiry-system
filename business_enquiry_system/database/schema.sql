-- Multi-Service Customer Service Database Schema
-- PostgreSQL 16+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop tables if exists (for clean setup)
DROP TABLE IF EXISTS agent_metrics CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS enquiries CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;

-- ============================================================
-- TENANTS TABLE (multi-tenant support)
-- ============================================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_key VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'legacy-ng-telecom', 'acme-ecommerce'
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    region VARCHAR(50),
    default_language VARCHAR(10) DEFAULT 'en',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_tenants_active ON tenants(is_active);

-- ============================================================
-- CUSTOMERS TABLE
-- ============================================================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255),
    full_name VARCHAR(255),
    customer_tier VARCHAR(20) DEFAULT 'BRONZE' CHECK (customer_tier IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM')),
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    total_transactions INTEGER DEFAULT 0,
    total_spent DECIMAL(12, 2) DEFAULT 0.00,
    last_transaction_date TIMESTAMP
);

-- Indexes
CREATE INDEX idx_customers_phone ON customers(phone_number);
CREATE INDEX idx_customers_tier ON customers(customer_tier);
CREATE INDEX idx_customers_active ON customers(is_active);

-- ============================================================
-- ENQUIRIES TABLE
-- ============================================================
CREATE TABLE enquiries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    enquiry_id VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,

    -- Classification
    service_domain VARCHAR(20) CHECK (service_domain IN ('AIRTIME', 'POWER', 'DATA', 'MULTI', 'OTHER')),
    intent VARCHAR(50),
    priority VARCHAR(20) CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    sentiment VARCHAR(20) CHECK (sentiment IN ('VERY_NEGATIVE', 'NEGATIVE', 'NEUTRAL', 'POSITIVE')),

    -- Content
    original_message TEXT NOT NULL,
    final_response TEXT,
    channel VARCHAR(20) DEFAULT 'SMS' CHECK (channel IN ('SMS', 'WHATSAPP', 'WEB', 'VOICE', 'EMAIL', 'USSD')),

    -- Processing
    agents_involved TEXT[],
    processing_duration_ms INTEGER,
    resolution_status VARCHAR(20) DEFAULT 'PENDING' CHECK (resolution_status IN ('PENDING', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED', 'FAILED')),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    sla_deadline TIMESTAMP,

    -- Feedback
    customer_rating INTEGER CHECK (customer_rating BETWEEN 1 AND 5),
    feedback_text TEXT,

    -- Metadata
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_enquiries_tenant ON enquiries(tenant_id);
CREATE INDEX idx_enquiries_customer ON enquiries(customer_id);
CREATE INDEX idx_enquiries_status ON enquiries(resolution_status);
CREATE INDEX idx_enquiries_domain ON enquiries(service_domain);
CREATE INDEX idx_enquiries_created ON enquiries(created_at DESC);
CREATE INDEX idx_enquiries_priority ON enquiries(priority);
CREATE INDEX idx_enquiries_sla ON enquiries(sla_deadline) WHERE resolution_status IN ('PENDING', 'IN_PROGRESS');

-- ============================================================
-- TRANSACTIONS TABLE
-- ============================================================
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    enquiry_id UUID REFERENCES enquiries(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,

    -- Transaction details
    service_type VARCHAR(20) NOT NULL CHECK (service_type IN ('AIRTIME', 'POWER', 'DATA')),
    network_or_disco VARCHAR(50) NOT NULL, -- MTN, EKEDC, etc.

    -- Financial
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    service_charge DECIMAL(10, 2) DEFAULT 0 CHECK (service_charge >= 0),
    total_amount DECIMAL(10, 2) NOT NULL CHECK (total_amount > 0),
    currency VARCHAR(3) DEFAULT 'NGN',

    -- Status
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED', 'REFUNDED', 'CANCELLED')),
    external_reference VARCHAR(100), -- From provider API
    failure_reason TEXT,

    -- Service-specific data
    recipient_phone VARCHAR(20), -- For airtime/data
    meter_number VARCHAR(20), -- For power
    token VARCHAR(50), -- For power (20-digit token)
    units DECIMAL(10, 2), -- For power (kWh)
    bundle_code VARCHAR(20), -- For data

    -- Timestamps
    initiated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Metadata (flexible JSONB for service-specific data)
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_transactions_tenant ON transactions(tenant_id);
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_type ON transactions(service_type);
CREATE INDEX idx_transactions_created ON transactions(initiated_at DESC);
CREATE INDEX idx_transactions_external_ref ON transactions(external_reference);

-- ============================================================
-- AGENT METRICS TABLE
-- ============================================================
CREATE TABLE agent_metrics (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    enquiry_id UUID REFERENCES enquiries(id) ON DELETE CASCADE,

    -- Performance
    processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
    success BOOLEAN NOT NULL,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),

    -- Context
    input_message TEXT,
    output_message TEXT,

    -- Metadata
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_agent_metrics_tenant ON agent_metrics(tenant_id);
CREATE INDEX idx_agent_metrics_name ON agent_metrics(agent_name);
CREATE INDEX idx_agent_metrics_timestamp ON agent_metrics(timestamp DESC);
CREATE INDEX idx_agent_metrics_success ON agent_metrics(success);
CREATE INDEX idx_agent_metrics_enquiry ON agent_metrics(enquiry_id);

-- ============================================================
-- VIEWS FOR ANALYTICS
-- ============================================================

-- Customer analytics view
CREATE OR REPLACE VIEW customer_analytics AS
SELECT
    c.id,
    c.phone_number,
    c.full_name,
    c.customer_tier,
    c.total_transactions,
    c.total_spent,
    COUNT(DISTINCT e.id) as total_enquiries,
    COUNT(DISTINCT CASE WHEN t.status = 'SUCCESS' THEN t.id END) as successful_transactions,
    AVG(e.customer_rating) as average_rating,
    MAX(e.created_at) as last_enquiry_date
FROM customers c
LEFT JOIN enquiries e ON c.id = e.customer_id
LEFT JOIN transactions t ON c.id = t.customer_id
GROUP BY c.id, c.phone_number, c.full_name, c.customer_tier, c.total_transactions, c.total_spent;

-- Agent performance view
CREATE OR REPLACE VIEW agent_performance AS
SELECT
    agent_name,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN success THEN 1 END) as successful_requests,
    COUNT(CASE WHEN NOT success THEN 1 END) as failed_requests,
    ROUND(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END)::numeric, 4) as success_rate,
    ROUND(AVG(processing_time_ms)::numeric, 2) as avg_processing_time_ms,
    ROUND(AVG(confidence_score)::numeric, 4) as avg_confidence,
    MIN(timestamp) as first_request,
    MAX(timestamp) as last_request
FROM agent_metrics
GROUP BY agent_name;

-- Daily transaction summary view
CREATE OR REPLACE VIEW daily_transaction_summary AS
SELECT
    DATE(initiated_at) as transaction_date,
    service_type,
    status,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as average_transaction_value
FROM transactions
GROUP BY DATE(initiated_at), service_type, status
ORDER BY transaction_date DESC, service_type;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Update customer's updated_at timestamp
CREATE OR REPLACE FUNCTION update_customer_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_timestamp
BEFORE UPDATE ON customers
FOR EACH ROW
EXECUTE FUNCTION update_customer_timestamp();

-- Update customer transaction stats when transaction succeeds
CREATE OR REPLACE FUNCTION update_customer_transaction_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'SUCCESS' AND (OLD.status IS NULL OR OLD.status != 'SUCCESS') THEN
        UPDATE customers
        SET
            total_transactions = total_transactions + 1,
            total_spent = total_spent + NEW.total_amount,
            last_transaction_date = NEW.completed_at
        WHERE id = NEW.customer_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_customer_stats
AFTER INSERT OR UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_customer_transaction_stats();

-- ============================================================
-- SEED DATA (for testing)
-- ============================================================

-- Sample tenant
INSERT INTO tenants (tenant_key, name, industry, region)
VALUES ('legacy-ng-telecom', 'Legacy Nigerian Telecom Demo', 'TELECOM', 'NG');

-- Sample customer
INSERT INTO customers (tenant_id, phone_number, email, full_name, customer_tier) VALUES
((SELECT id FROM tenants WHERE tenant_key = 'legacy-ng-telecom'), '+2348012345678', 'chinedu.okafor@example.com', 'Chinedu Okafor', 'GOLD'),
((SELECT id FROM tenants WHERE tenant_key = 'legacy-ng-telecom'), '+2348098765432', 'amina.bello@example.com', 'Amina Bello', 'SILVER'),
((SELECT id FROM tenants WHERE tenant_key = 'legacy-ng-telecom'), '+2347012345678', NULL, 'Emeka Nwosu', 'BRONZE');

-- Sample enquiry
INSERT INTO enquiries (
    tenant_id,
    enquiry_id,
    customer_id,
    service_domain,
    intent,
    priority,
    sentiment,
    original_message,
    channel,
    resolution_status
) VALUES (
    (SELECT id FROM tenants WHERE tenant_key = 'legacy-ng-telecom'),
    'ENQ-TEST-001',
    (SELECT id FROM customers WHERE phone_number = '+2348012345678'),
    'AIRTIME',
    'purchase',
    'MEDIUM',
    'NEUTRAL',
    'I need 1000 naira MTN airtime',
    'WHATSAPP',
    'PENDING'
);

-- ============================================================
-- UTILITY FUNCTIONS
-- ============================================================

-- Function to get customer tier based on spending
CREATE OR REPLACE FUNCTION calculate_customer_tier(customer_uuid UUID)
RETURNS VARCHAR AS $$
DECLARE
    total_spent_amount DECIMAL;
    new_tier VARCHAR;
BEGIN
    SELECT total_spent INTO total_spent_amount
    FROM customers
    WHERE id = customer_uuid;

    IF total_spent_amount >= 1000000 THEN
        new_tier := 'PLATINUM';
    ELSIF total_spent_amount >= 500000 THEN
        new_tier := 'GOLD';
    ELSIF total_spent_amount >= 100000 THEN
        new_tier := 'SILVER';
    ELSE
        new_tier := 'BRONZE';
    END IF;

    UPDATE customers
    SET customer_tier = new_tier
    WHERE id = customer_uuid;

    RETURN new_tier;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE customers IS 'Customer master table with tier management';
COMMENT ON TABLE enquiries IS 'All customer enquiries with classification and resolution tracking';
COMMENT ON TABLE transactions IS 'Financial transactions for airtime, power, and data services';
COMMENT ON TABLE agent_metrics IS 'Performance metrics for each agent interaction';

COMMENT ON COLUMN customers.customer_tier IS 'Tier based on spending: BRONZE < 100K, SILVER < 500K, GOLD < 1M, PLATINUM >= 1M';
COMMENT ON COLUMN transactions.metadata IS 'Flexible JSONB field for service-specific data like bundle details, tariff info, etc.';
COMMENT ON COLUMN enquiries.agents_involved IS 'Array of agent names that processed this enquiry';

-- ============================================================
-- GRANT PERMISSIONS (adjust based on your setup)
-- ============================================================

-- Grant permissions to application user (create this user first)
-- CREATE USER csapp WITH PASSWORD 'your-secure-password';
-- GRANT CONNECT ON DATABASE customer_service_db TO csapp;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO csapp;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO csapp;
