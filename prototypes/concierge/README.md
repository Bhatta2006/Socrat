# Concierge prototype

This is a disposable M0 research prototype. It validates comprehension of Socrat’s goal, routing, daily-plan, hint, evidence, and recovery concepts. It is not production application architecture and stores no data.

## Run

From the repository root:

```powershell
python -m http.server 4173 --directory prototypes/concierge
```

Open `http://127.0.0.1:4173`.

## Test

```powershell
node --test prototypes/concierge/model.test.mjs
powershell -ExecutionPolicy Bypass -File scripts/validation/test-m0-contracts.ps1
```

## Research constraints

- The facilitator must disclose that the prototype is rule-based and incomplete.
- Do not enter real email addresses, employer-confidential questions, or personal data.
- Refresh resets the session.
- Log manual facilitator interventions in the session record.
- Prototype behavior is informative; the machine contract remains authoritative.

