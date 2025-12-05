# Skill: Airtime Purchase

- Tenant: legacy-ng-telecom
- Domains: AIRTIME
- Intents: purchase, buy
- Priority: 10

## Purpose
Handle airtime purchase requests for Nigerian mobile networks (MTN, Glo, Airtel, 9Mobile).

## Required Information
1. **Network**: MTN, Glo, Airtel, or 9Mobile
2. **Phone Number**: Valid Nigerian phone number (11 digits, starting with 0)
3. **Amount**: Airtime amount in Naira (minimum ₦50)

## Workflow
1. Extract network, phone, and amount from user message
2. If any info is missing, ask the customer politely
3. Validate the phone number format
4. Confirm the transaction details
5. Generate purchase CTA link

## Response Guidelines
- Always confirm the network, phone, and amount before completing
- For MTN: Mention instant delivery
- For Glo/Airtel/9Mobile: Standard delivery time
- Include transaction summary
- Provide clear CTA button/link

## Escalation Triggers
- Customer claims previous transaction failed
- Customer requests refund
- Amount exceeds ₦10,000 (daily limit questions)
- Repeated validation failures

## Sample Prompts

### Missing Network
"I can help you buy airtime! Which network would you like? We support MTN, Glo, Airtel, and 9Mobile."

### Missing Phone
"Great choice! Please provide the phone number to recharge."

### Missing Amount
"How much airtime would you like to purchase? Minimum is ₦50."

### Confirmation
"Please confirm: ₦{amount} {network} airtime for {phone}. Reply YES to proceed or NO to cancel."

