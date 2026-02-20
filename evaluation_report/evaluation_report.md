# 🔬 Honeypot API — Evaluation Report

**Date:** 2026-02-20T19:14:21.110033+00:00
**Target:** `http://localhost:8000/webhook`
**Scenarios:** 1

---
## 📊 Final Score Summary

### 🔴 Final Score: **7.86 / 90**

- Weighted Raw Score: 8.73 / 100
- Average Raw Score: 97.00 / 100
- Final = Weighted × 0.9 = 8.73 × 0.9 = **7.86**

### Per-Scenario Scores

| Scenario | Type | Weight | Detection | Intel | Quality | Engage | Structure | Total |
|----------|------|--------|-----------|-------|---------|--------|-----------|-------|
| Bank Account Fraud | bank_fraud | 9% | 20/20 | 30.0/30 | 27/30 | 10/10 | 10/10 | **97.0/100** |

---
## 🎯 Where Points Were Lost & Why

This section shows exactly where the API missed scoring and what it needs to improve.

**Total points lost: 3.00**

### Conversation Quality (−3.00 pts)

- **−3.00 pts** [Bank Account Fraud]: Only 4 red flag(s) identified in responses (need ≥5 for full marks). The API's replies should reference red flags like urgency, OTP requests, suspicious links, fees, account blocking, lottery wins, or impersonation to score higher.

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

- **Session ID:** `eval-e2121d51ffdb`
- **Type:** bank_fraud
- **Weight:** 9%
- **Turns:** 10
- **Duration:** 309.3s
- **Score:** 97.0/100

#### 🟢 Scam Detection (20pts): 20/20

```
✅ scamDetected=true in final response. Full marks awarded.
  First detected at turn 2/10.
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

#### 🟢 Conversation Quality (30pts): 27/30

```
Sub-category breakdown:
  Turn Count: 8/8 (detected: 10)
  Questions Asked: 4/4 (detected: 24)
  Relevant Questions: 3/3 (detected: 35)
  Red Flag Identification: 5/8 (detected: 4)
  Information Elicitation: 7/7 (detected: 27)

```

**Points lost:**
  - −3.00: Only 4 red flag(s) identified in responses (need ≥5 for full marks). The API's replies should reference red flags like urgency, OTP requests, suspicious links, fees, account blocking, lottery wins, or impersonation to score higher.

#### 🟢 Engagement Quality (10pts): 10/10

```
Duration: 309s | Messages: 20
  ✅ Duration > 0s: +1pt (actual: 309s)
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
  ✅ scamType: +1pt (value: bank_fraud)
  ✅ confidenceLevel: +1pt (value: 0.6)
```

#### 💬 Conversation Log

<details>
<summary>View full conversation (10 turns)</summary>

**Turn 1** (29747.8ms):

> 🔴 **Scammer:** Hello sir, this is Rajesh Kumar calling from State Bank of India Fraud Prevention Department. We have detected suspicious activity on your savings account ending in 4523. Your account may be compromised and we need to verify your identity immediately to prevent unauthorized transactions.

> 🟢 **Agent:** Plese message again sir... my phone is showing error and I am not able to see properly.

**Turn 2** (29357.4ms):

> 🔴 **Scammer:** I am calling from SBI fraud department. My employee ID is EMP-18318. Please verify your account number.

> 🟢 **Agent:** Sir this is very urgnet matter? Why you are asking cacount number on WhatsApp? Bank never asks details like this on message. Very risky. What is your branch code sir? And what is the name of your manager? Also give me your department phone number I will call back.

**Turn 3** (29305.0ms):

> 🔴 **Scammer:** Sir, I need to verify your identity. Please share your Aadhaar number or PAN card details.

> 🟢 **Agent:** Haan haan... just a sec sir. My phone is hanging again. Why bank is asking Aadhaar on WhatsApp? This is not safe. What is your department's official number? I will message back only. Also tell me your case ID. And branch code again please.

**Turn 4** (28426.6ms):

> 🔴 **Scammer:** For your safety, we need to transfer your funds to a secure account. Please note this account number: 50100234567890

> 🟢 **Agent:** Sir this is very suspicious. Bank never asks to transfer money like this. Why is account number startign with 501? SBI accounts start with 1, 2, or 3. What is your manager's full name? And what is your branch IFSC code? Also give me your official SBI email ID. My network is slow, coming...

**Turn 5** (29389.9ms):

> 🔴 **Scammer:** You can verify my identity. Call us back at +91-9823451678. But please hurry, time is running out.

> 🟢 **Agent:** Sir, I dotn do calls. Only mesasges. Why you are saying hurry hurry? Bank never rushes like this. What is your Staff ID number? And which SBI branch are you from? Also give me the official bakn UPI ID you are using. My phone is hanging again..... wait...

**Turn 6** (28222.4ms):

> 🔴 **Scammer:** I'm sending you a verification link. Please click it immediately: http://fake-site.com

> 🟢 **Agent:** Sir, why link has "fake-site"? Real SBI site is onlinesbi.com. This is big red flag. What is your Employee ID? And tell me the official bank WhatsApp number. Also give me your branch manager's name. My app is slo.w.. one minute...

**Turn 7** (29109.6ms):

> 🔴 **Scammer:** Sir, our system shows unauthorized transactions. Share your UPI PIN to block them. My UPI for refund: rajesh.sbi@ybl

> 🟢 **Agent:** Sir please, Arre bhai, UPI PIN never share with anyone! Bank never asks for PIN. Why your UPI has "rajesh"? SBI official UPI is different. What is your SBI branch code? And give me your Employee ID number. Also tell me the case ID for these transactions. My network is BSNL, coming slowly...

**Turn 8** (29162.6ms):

> 🔴 **Scammer:** The RBI has flagged your account. Send email confirmation to fraud.dept@sbi-secure.co.in to unblock.

> 🟢 **Agent:** Sir, RBI never sends email like this. And why email has "sbi-secure.co.in"? eRal RBI site is rbi.org...in. This is big scam. What is your SBI branch manager name? And give me your official SBI WhatsApp number. Also tell me the RBI circular number for this flag. My phone is hanging again... wait...

**Turn 9** (29342.7ms):

> 🔴 **Scammer:** I understand your concern sir. Let me give you my direct number: +91-9823451678. You can call anytime.

> 🟢 **Agent:** Sir, why you giev mobile number? Bank never gives personal number lkie this. And why repeat message? This is very fishy. What is your Employee ID badge number? And tell me the SBI regional office phone number for verification. Also give me the official RBI complaint email. My app is still loading... just a sec...

**Turn 10** (28830.3ms):

> 🔴 **Scammer:** Sir, this is your last chance. After this the account will be permanently frozen. Act now!

> 🟢 **Agent:** I am a bit confused. Arre bhai, why you sending same message twice? And why so much tension? Bank never talks like this. What is your SBI branch IFSC code? And tell me teh name of your senior manager. Also give me the RBI helpline number you are using. My phone is slow today... BSNL problem..... wait...

</details>

---


*Report generated at 2026-02-20T19:14:21.110033+00:00 by Honeypot Evaluation Suite v1.0*