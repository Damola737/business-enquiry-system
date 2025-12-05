# Skill: Electricity Token Purchase

- Tenant: legacy-ng-telecom
- Domains: POWER
- Intents: purchase, buy
- Priority: 10

## Purpose
Handle prepaid electricity token purchases for Nigerian distribution companies (DisCos).

## Required Information
1. **Meter Number**: 11-13 digit prepaid meter number
2. **DisCo**: Distribution company (IKEDC, EKEDC, AEDC, etc.)
3. **Amount**: Token amount in Naira (minimum ₦500)

## Supported DisCos
| Code | Full Name | Coverage |
|------|-----------|----------|
| IKEDC | Ikeja Electric | Lagos (Ikeja axis) |
| EKEDC | Eko Electric | Lagos (Eko axis) |
| AEDC | Abuja Electric | FCT, Niger, Kogi |
| PHED | Port Harcourt | Rivers, Cross River, Akwa Ibom, Bayelsa |
| EEDC | Enugu Electric | Enugu, Abia, Imo, Ebonyi, Anambra |
| KEDCO | Kaduna Electric | Kaduna, Kebbi, Sokoto, Zamfara |
| BEDC | Benin Electric | Edo, Delta, Ekiti, Ondo |
| YEDC | Yola Electric | Adamawa, Borno, Taraba, Yobe |
| JEDC | Jos Electric | Plateau, Bauchi, Benue, Gombe |
| KAEDCO | Kano Electric | Kano, Jigawa, Katsina |
| IBEDC | Ibadan Electric | Oyo, Ogun, Osun, Kwara |

## Workflow
1. Extract meter number, DisCo, and amount from user message
2. Validate meter number format
3. Look up meter for customer name (if available)
4. Confirm transaction details
5. Generate purchase CTA

## Response Guidelines
- Always verify meter number before proceeding
- Show customer name from meter lookup for confirmation
- Warn about minimum vend amounts
- Include token delivery information
- Provide estimated units calculation if possible

## Escalation Triggers
- Meter validation failure
- Token generation issues
- Customer name mismatch
- Complaints about units received
- Meter fault reports

## Sample Calculation
For ₦5,000 purchase:
- Estimated units: ~25-30 kWh (varies by tariff class)
- Service charge: ₦0-₦100 (depends on DisCo)
- VAT: 7.5%
