# Skill: Data Bundle Purchase

- Tenant: legacy-ng-telecom
- Domains: DATA
- Intents: purchase, buy
- Priority: 10

## Purpose
Handle data bundle purchases for Nigerian mobile networks (MTN, Glo, Airtel, 9Mobile).

## Required Information
1. **Network**: MTN, Glo, Airtel, or 9Mobile
2. **Phone Number**: Valid Nigerian phone number
3. **Bundle**: Data bundle size (e.g., 1GB, 2GB, 5GB)
4. **Duration**: Bundle validity (optional, defaults to 30 days)

## Available Bundles

### MTN
| Bundle | Price | Validity |
|--------|-------|----------|
| 1GB | ₦300 | 1 day |
| 1.5GB | ₦1,000 | 30 days |
| 2GB | ₦1,200 | 30 days |
| 3GB | ₦1,500 | 30 days |
| 5GB | ₦2,500 | 30 days |
| 10GB | ₦3,500 | 30 days |

### Glo
| Bundle | Price | Validity |
|--------|-------|----------|
| 1.25GB | ₦500 | 1 day |
| 2GB | ₦1,000 | 30 days |
| 4.5GB | ₦2,000 | 30 days |
| 7.7GB | ₦2,500 | 30 days |

### Airtel
| Bundle | Price | Validity |
|--------|-------|----------|
| 1GB | ₦300 | 1 day |
| 2GB | ₦1,000 | 30 days |
| 3GB | ₦1,500 | 30 days |
| 6GB | ₦2,500 | 30 days |

### 9Mobile
| Bundle | Price | Validity |
|--------|-------|----------|
| 1GB | ₦500 | 30 days |
| 2.5GB | ₦1,200 | 30 days |
| 5GB | ₦2,000 | 30 days |

## Workflow
1. Extract network, phone, and bundle from user message
2. If user asks about available bundles, show pricing table
3. Validate phone number
4. Confirm transaction
5. Generate purchase CTA

## Response Guidelines
- Show available bundles when user is unsure
- Highlight best value options
- Include validity period in confirmation
- Provide clear pricing breakdown

## Escalation Triggers
- Bundle activation issues
- Data not credited after purchase
- Dispute about bundle validity
