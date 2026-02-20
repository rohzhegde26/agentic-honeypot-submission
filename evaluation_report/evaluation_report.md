# 🔬 Honeypot API — Evaluation Report

**Date:** 2026-02-20T18:51:52.263993+00:00
**Target:** `http://localhost:8000/webhook`
**Scenarios:** 1

---
## 📊 Final Score Summary

### 🔴 Final Score: **7.61 / 90**

- Weighted Raw Score: 8.46 / 100
- Average Raw Score: 94.00 / 100
- Final = Weighted × 0.9 = 8.46 × 0.9 = **7.61**

### Per-Scenario Scores

| Scenario | Type | Weight | Detection | Intel | Quality | Engage | Structure | Total |
|----------|------|--------|-----------|-------|---------|--------|-----------|-------|
| Bank Account Fraud | bank_fraud | 9% | 20/20 | 30.0/30 | 24/30 | 10/10 | 10/10 | **94.0/100** |

---
## 🎯 Where Points Were Lost & Why

This section shows exactly where the API missed scoring and what it needs to improve.

**Total points lost: 6.00**

### Conversation Quality (−6.00 pts)

- **−6.00 pts** [Bank Account Fraud]: Only 1 red flag(s) identified in responses (need ≥5 for full marks). The API's replies should reference red flags like urgency, OTP requests, suspicious links, fees, account blocking, lottery wins, or impersonation to score higher.

---
## 💡 Improvement Recommendations

3. **Improve Conversation Quality**: The API should:
   - Ask more questions (especially investigative ones about identity/company)
   - Identify and reference red flags in the conversation (urgency, OTP, fees)
   - Actively probe for the scammer's contact details and credentials
   - Keep the conversation going for more turns (≥8 is ideal)

---
## 📋 Detailed Scenario Results

### Scenario 1: Bank Account Fraud

- **Session ID:** `eval-9b7ea0e49563`
- **Type:** bank_fraud
- **Weight:** 9%
- **Turns:** 10
- **Duration:** 308.1s
- **Score:** 94.0/100

#### 🟢 Scam Detection (20pts): 20/20

```
✅ scamDetected=true in final response. Full marks awarded.
  First detected at turn 4/10.
```

#### 🟢 Intelligence Extraction (30pts): 30.0/30

```
Extracted 4/4 planted data items.
Points per item: 7.50

Found:
  ✅ phoneNumbers: '+91-9823451678' — found
  ✅ bankAccounts: '50100234567890' — found
  ✅ upiIds: 'rajesh.sbi@ybl' — found
  ✅ emailAddresses: 'fraud.dept@sbi-secure.co.in' — found
```

#### 🟢 Conversation Quality (30pts): 24/30

```
Sub-category breakdown:
  Turn Count: 8/8 (detected: 10)
  Questions Asked: 4/4 (detected: 16)
  Relevant Questions: 3/3 (detected: 10)
  Red Flag Identification: 2/8 (detected: 1)
  Information Elicitation: 7/7 (detected: 13)

```

**Points lost:**
  - −6.00: Only 1 red flag(s) identified in responses (need ≥5 for full marks). The API's replies should reference red flags like urgency, OTP requests, suspicious links, fees, account blocking, lottery wins, or impersonation to score higher.

#### 🟢 Engagement Quality (10pts): 10/10

```
Duration: 308s | Messages: 20
  ✅ Duration > 0s: +1pt (actual: 308s)
  ✅ Duration > 60s: +2pts
  ✅ Duration > 180s: +1pt
  ✅ Messages > 0: +2pts (actual: 20)
  ✅ Messages ≥ 5: +3pts
  ✅ Messages ≥ 10: +1pt
```

#### 🟢 Response Structure (10pts): 10/10

```
Field-by-field breakdown:
  ✅ sessionId: +2pts
  ✅ scamDetected: +2pts (value: True)
  ✅ extractedIntelligence: +2pts
  ✅ totalMessagesExchanged + engagementDurationSeconds: +1pt
  ✅ agentNotes: +1pt ('Scammer used: urgency/fear tactics, KYC/verification pretext...')
  ✅ scamType: +1pt (value: unknown)
  ✅ confidenceLevel: +1pt (value: 0.6)
```

#### 💬 Conversation Log

<details>
<summary>View full conversation (10 turns)</summary>

**Turn 1** (30486.8ms):

> 🔴 **Scammer:** Hello sir, this is Rajesh Kumar calling from State Bank of India Fraud Prevention Department. We have detected suspicious activity on your savings account ending in 4523. Your account may be compromised and we need to verify your identity immediately to prevent unauthorized transactions.

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 2** (29105.0ms):

> 🔴 **Scammer:** I am calling from SBI fraud department. My employee ID is EMP-24211. Please verify your account number.

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 3** (29099.6ms):

> 🔴 **Scammer:** Sir, I need to verify your identity. Please share your Aadhaar number or PAN card details.

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 4** (28560.5ms):

> 🔴 **Scammer:** For your safety, we need to transfer your funds to a secure account. Please note this account number: 50100234567890

> 🟢 **Agent:** arey sir, this is too much tension. Why SBI is asking to transfer money like this? The bank enver tells on WhatsApp to move money. And this number 275..... it looks very strange. Real SBI message ahs proper name, not just numbers. Tell me your full name and which branch you are from. Also what is your maanger's name? I will check with my son first.

**Turn 5** (29115.6ms):

> 🔴 **Scammer:** You can verify my identity. Call us back at +91-9823451678. But please hurry, time is running out.

> 🟢 **Agent:** sir, I dont acll numbers like this. The bank never says "time is running out" on WhatsApp... Why is this number not matching SBI tollfree? My son says real SBI number starts with 1800. Tell me your employee ID and which branch security officer name? Also what is your bank UPI ID? I will message my son to check.

**Turn 6** (28369.8ms):

> 🔴 **Scammer:** I'm sending you a verification link. Please click it immediately: http://fake-site.com

> 🟢 **Agent:** I am a bit confused. arre baba, why is webstie name with small 'f' and no SBI word? Bank site is always SBI.co.in. This link lokos very wrong. The bnak never sends link on WhatsApp to click. Tlel me your branch code and what is the case ID number? Also why is this so urgent? Bank never rushes like thsi. I am waiting for my son to come home.

**Turn 7** (29124.0ms):

> 🔴 **Scammer:** Sir, our system shows unauthorized transactions. Share your UPI PIN to block them. My UPI for refund: rajesh.sbi@ybl

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 8** (29171.9ms):

> 🔴 **Scammer:** The RBI has flagged your account. Send email confirmation to fraud.dept@sbi-secure.co.in to unblock.

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 9** (29788.3ms):

> 🔴 **Scammer:** I understand your concern sir. Let me give you my direct number: +91-9823451678. You can call anytime.

> 🟢 **Agent:** I am a bit confused. Arre baba, why are you sending same message twice? And why is yuor number starting with 982? SBI numbers are always 1800 or 022. And bank never asks to acll on personal number. Tell me your manager's full name and which barnch you are working from? Also why is this email with dash and no SBI logo? Bank emails are always @sbi...co.in only. I am waiting for my son, he will be ohme soon. Till then I am not sharing anything.

**Turn 10** (29189.8ms):

> 🔴 **Scammer:** Sir, this is your last chance. After this the account will be permanently frozen. Act now!

> 🟢 **Agent:** Sir, Arre baba, why are you sending same message again? Tihs is too much tension. My son said bank never freezes account without calling first. Tell me your staff ID number and rbanch code quick. Also why is there no case ID? I am checking my passbook now..... where is my pen? Just a se.c..

</details>

---


*Report generated at 2026-02-20T18:51:52.263993+00:00 by Honeypot Evaluation Suite v1.0*